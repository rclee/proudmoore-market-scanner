import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scanner.__main__ import demo_feeds, load_config, main
from scanner.data import FeedError, parse_feed, record_history
from scanner.engine import build_watchlist, max_buy_price
from scanner.report import dashboard


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
HEADER = 'itemId,name,marketValue,minBuyout,recent,historical,updatedAt\n'
ROW = '123,Test item,10000000,5000000,10000000,10000000,2026-10-31T11:00:00Z\n'


class FinancialRules(unittest.TestCase):
    def test_worked_1000_gold_example_and_rounding(self):
        # 1000g resale, 5% AH cut, 20% return on cost, zero lost deposits.
        self.assertEqual(max_buy_price(10_000_000, 500, 2000, 0), 7_916_666)
        self.assertEqual(max_buy_price(10_000_000, 500, 2000, 10_000), 7_908_333)
        self.assertEqual(max_buy_price(1_000, 500, 2000, 10_000), 0)

    def setUp(self):
        self.config = load_config(ROOT / 'config.json')
        self.feeds = demo_feeds(NOW)

    def scan(self, feeds=None):
        feeds = feeds or self.feeds
        summaries = [feed.summary(NOW, 48 if feed.scope == 'region' else 6) for feed in feeds]
        return build_watchlist(feeds, self.config, summaries)[0]

    def test_candidates_are_research_only_and_market_scopes_stay_separate(self):
        rows = self.scan()
        self.assertEqual({row['scope'] for row in rows}, {'realm', 'commodities'})
        self.assertTrue(all(row['recommended_quantity'] == 0 and row['status'] == 'watch_only' for row in rows))
        self.assertTrue(all(row['return_bps'] >= 2000 for row in rows))

    def test_zero_or_missing_liquidity_is_not_a_buy_signal(self):
        for feed in self.feeds:
            if feed.scope == 'region':
                feed.rows[0]['soldPerDay'] = 0
                feed.rows[1]['saleRate'] = 0
        self.assertEqual(self.scan(), [])

    def test_missing_prices_and_over_cap_are_rejected(self):
        self.feeds[0].rows[0]['minBuyout'] = 40_000_001
        self.feeds[1].rows[0]['historical'] = 0
        self.assertEqual(self.scan(), [])

    def test_stale_sources_are_visible(self):
        summaries = [feed.summary(NOW + timedelta(days=3), 6) for feed in self.feeds]
        rows, _ = build_watchlist(self.feeds, self.config, summaries)
        self.assertTrue(all('Source data is stale' in row['blockers'] for row in rows))


class FeedValidation(unittest.TestCase):
    def test_valid_schema_preserves_integer_copper_and_utc(self):
        feed = parse_feed('realm', 'https://example.com', HEADER + ROW, NOW)
        self.assertEqual(feed.rows[0]['minBuyout'], 5_000_000)
        self.assertEqual(feed.source_time, '2026-10-31T11:00:00+00:00')

    def test_rejects_bad_identity_prices_timestamps_and_schema(self):
        variants = [HEADER + ROW + ROW, HEADER + ROW.replace('5000000', '-1'),
                    HEADER + ROW.replace('5000000', '0.5'), HEADER + ROW.replace('5000000', 'NaN'),
                    HEADER + ROW.replace('2026-10-31T11:00:00Z', '2026-11-01T11:00:00Z'),
                    HEADER + ROW.replace('2026-10-31T11:00:00Z', '2026-10-31T11:00:00'),
                    HEADER + ROW.replace('123,', 'i:123,'), HEADER + ROW.rstrip() + ',extra\n',
                    HEADER.replace('minBuyout', 'unknown') + ROW, HEADER]
        for content in variants:
            with self.subTest(content=content), self.assertRaises(FeedError):
                parse_feed('realm', 'https://example.com', content, NOW)

    def test_deduplicates_scans_and_expires_old_history(self):
        feed = parse_feed('realm', 'https://example.com', HEADER + ROW, NOW)
        candidate = {'scope': 'realm', 'item_id': 123, 'source_time': feed.source_time,
                     'observed_buy_copper': 5_000_000}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.sqlite3'
            first = record_history(path, [feed], [candidate], NOW, 35)
            again = record_history(path, [feed], [candidate], NOW, 35)
            self.assertEqual(first['new_scans'], 1)
            self.assertEqual(again['new_scans'], 0)
            self.assertEqual(again['retained_observations'], 1)
            expired = record_history(path, [], [], NOW + timedelta(days=36), 35)
            self.assertEqual(expired['retained_scans'], 0)
            self.assertEqual(expired['retained_observations'], 0)

    def test_changed_scan_payload_does_not_replace_existing_history(self):
        feed = parse_feed('realm', 'https://example.com', HEADER + ROW, NOW)
        changed = parse_feed('realm', 'https://example.com', HEADER + ROW.replace('Test item', 'Changed'), NOW)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.sqlite3'
            record_history(path, [feed], [], NOW, 35)
            with self.assertRaises(FeedError):
                record_history(path, [changed], [], NOW, 35)


class CommandAndReports(unittest.TestCase):
    def test_invalid_configuration_replaces_prior_results(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'report.json').write_text('{"old":"results"}', encoding='utf-8')
            code = main(['--config', str(output / 'missing.json'), '--output', str(output)])
            report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
            self.assertEqual(code, 2)
            self.assertEqual(report['status'], 'unavailable')
            self.assertEqual(report['watchlist'], [])

    def test_demo_is_labelled_and_never_touches_live_history(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'reports'
            state = Path(directory) / 'live.sqlite3'
            code = main(['--demo', '--config', str(ROOT / 'config.json'), '--state', str(state), '--output', str(output)])
            report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
            self.assertEqual(code, 0)
            self.assertEqual(report['mode'], 'demo')
            self.assertFalse(state.exists())
            self.assertIn('SYNTHETIC DEMO', (output / 'index.html').read_text(encoding='utf-8'))

    def test_failed_live_run_replaces_prior_results_with_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'report.json').write_text('{"old":"results"}', encoding='utf-8')
            with patch('scanner.__main__.fetch_feed', side_effect=FeedError('Source unavailable')):
                code = main(['--config', str(ROOT / 'config.json'), '--output', str(output)])
            report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
            self.assertEqual(code, 1)
            self.assertEqual(report['status'], 'unavailable')
            self.assertEqual(report['watchlist'], [])

    def test_two_live_runs_restore_durable_history(self):
        # Exercise the CLI with deterministic feed responses, not private SQLite internals.
        current_feeds = demo_feeds(datetime.now(timezone.utc))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'reports'
            args = ['--config', str(ROOT / 'config.json'), '--state', str(Path(directory) / 'history.sqlite3'),
                    '--output', str(output)]
            for run in range(2):
                with patch('scanner.__main__.fetch_feed', side_effect=current_feeds):
                    self.assertEqual(main(args), 0)
                report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
                self.assertEqual(report['history']['new_scans'], 3 if run == 0 else 0)
                self.assertEqual(report['history']['retained_observations'], 2)

    def test_feed_text_is_escaped_in_dashboard(self):
        feeds = demo_feeds(NOW)
        config = load_config(ROOT / 'config.json')
        summaries = [feed.summary(NOW, 48) for feed in feeds]
        rows, _ = build_watchlist(feeds, config, summaries)
        rows[0]['name'] = '<script>alert(1)</script>'
        report = {'mode': 'demo', 'status': 'demo', 'config': config, 'feeds': summaries,
                  'generated_at': NOW.isoformat(), 'watchlist': rows}
        rendered = dashboard(report)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', rendered)
        self.assertNotIn('<script>alert(1)</script>', rendered)


if __name__ == '__main__':
    unittest.main()
