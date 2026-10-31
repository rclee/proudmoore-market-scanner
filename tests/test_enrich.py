import html
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, Mock

from scanner.__main__ import demo_feeds
from scanner.data import FeedError, record_history
from scanner.enrich import (MARKET, Cache, community_feed, daily_brief, enrich_report,
                            live_build, parse_catalog, parse_commodity, parse_token)

NOW = datetime(2026, 10, 31, 17, 0, tzinfo=timezone.utc)


class SupplementalData(unittest.TestCase):
    def test_provider_timeout_stops_remaining_item_requests(self):
        report={'mode':'live','status':'watch_only','watchlist':[{'item_id':i,'scope':'commodities'} for i in (1,2,3)]}
        cache=Mock(spec=Cache)
        cache.get.return_value=None
        item_calls=[]
        def responses(url, **kwargs):
            if 'wowtoken.app' in url:
                return b'{"us":["2026-10-31T16:33:30Z",285978]}'
            if 'api.ahledger.com' in url:
                item_calls.append(url)
                raise TimeoutError('Provider timeout')
            return b'<rss><channel></channel></rss>'
        with patch('scanner.enrich.vendor_catalog',side_effect=OSError('Catalog unavailable')), patch('scanner.enrich.download',side_effect=responses):
            extra=enrich_report(report,cache,NOW)
        self.assertEqual(len(item_calls),1)
        self.assertEqual(extra['status'],'partial')
        self.assertEqual(extra['daily_brief']['tasks'],[])

    def test_selects_product_wow_not_newer_ptr(self):
        props={'products':{'wow':{'name':'Retail','flavor':'_retail_'}},
               'versions':[{'product':'wowt','version':'12.1.7.70668'}, {'product':'wow','version':'12.1.5.70688'}]}
        content='<div data-page="'+html.escape(json.dumps({'props':props}),quote=True)+'"></div>'
        self.assertEqual(live_build(content),'12.1.5.70688')
        with self.assertRaises(FeedError):
            live_build(content.replace('Retail','PTR'))

    def test_catalog_excludes_equipment_and_scaling(self):
        header='ID,SellPrice,InventoryType,Stackable,PlayerLevelToItemLevelCurveID,ItemLevelOffsetCurveID\n'
        csv=header+'2589,13,0,1000,0,0\n25,3,21,1,0,0\n123,100,0,200,7,0\n'
        values,count=parse_catalog(csv)
        self.assertEqual(values,{'2589':13})
        self.assertEqual(count,3)
        with self.assertRaises(FeedError):
            parse_catalog(csv+'2589,13,0,1000,0,0\n')

    def test_token_gold_is_converted_to_copper_and_timestamp_preserved(self):
        token=parse_token({'us':['2026-10-31T16:33:30Z',285978]},NOW)
        self.assertEqual(token['price_copper'],2859780000)
        self.assertEqual(token['status'],'fresh')
        self.assertEqual(parse_token({'us':['2026-10-30T16:33:30Z',285978]},NOW)['status'],'stale')
        with self.assertRaises(FeedError):
            parse_token({'us':['2026-11-01T16:33:30Z',285978]},NOW)
        with self.assertRaises(FeedError):
            parse_token({'us':[None,285978]},NOW)

    def test_commodity_scope_is_validated_and_total_supply_is_not_cheapest_depth(self):
        payload={'market':MARKET,'item':{'id':2589,'name':'Linen Cloth'},
            'latest':{'observedAt':'2026-10-31T16:33:44Z','minBuyout':500,'median':900,'quantity':760702,'auctions':247},
            'series':[{'t':'2026-10-30T16:00:00Z','min':100,'median':900,'quantity':12000}],
            'attribution':{'url':'https://ahledger.com/items/2589?utm_source=ahledger_api'}}
        detail=parse_commodity(payload,2589,NOW)
        self.assertEqual(detail['total_quantity'],760702)
        self.assertIsNone(detail['quantity_at_minimum'])
        self.assertFalse(detail['executable_quote'])
        self.assertEqual(len(detail['history']),1)
        with self.assertRaises(FeedError):
            parse_commodity({**payload,'market':'retail.normal.neutral.us'},2589,NOW)
        with self.assertRaises(FeedError):
            parse_commodity(payload,34054,NOW)

    def test_conditional_lot_uses_budget_and_never_claims_live_verification(self):
        candidate={'item_id':2589,'name':'Test','screen_result':'reference_discount_persists',
            'corroborated_vendor_copper':1000000,
            'snapshot_cross_check':{'status':'fresh','unit_price_copper':800000,'total_quantity':100,
                                    'observed_at':NOW.isoformat()}}
        brief=daily_brief([candidate],NOW)
        task=brief['tasks'][0]
        self.assertEqual(task['quantity_to_quote'],1)
        self.assertEqual(task['maximum_total_copper'],800000)
        self.assertEqual(task['minimum_conditional_profit_copper'],200000)
        self.assertFalse(task['buy_without_live_verification'])
        self.assertEqual(daily_brief([{**candidate,'screen_result':'newer_price_rejects_discount'}],NOW)['tasks'],[])
        self.assertEqual(daily_brief([],NOW)['status'],'skip')

    def test_community_titles_are_not_executable_instructions(self):
        feed=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Buy everything</title><link href="https://www.reddit.com/r/woweconomy/comments/abc"/><published>2026-10-31T16:00:00Z</published></entry><entry><title>Wrong host</title><link href="https://evil.example"/><published>2026-10-31T16:00:00Z</published></entry></feed>'''
        result=community_feed(feed,'r/woweconomy','https://www.reddit.com/r/woweconomy/new/.rss',NOW)
        self.assertEqual(len(result['entries']),1)
        self.assertEqual(result['entries'][0]['use'],'research_lead_only')

    def test_cache_expires_and_provider_failure_leaves_original_report_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'market.sqlite3'
            record_history(path,demo_feeds(NOW),[],NOW,35)
            cache=Cache(path)
            cache.put('example',{'fetched_at':NOW.isoformat(),'value':13})
            cached=cache.get('example',NOW,1)
            assert cached is not None
            self.assertEqual(cached['value'],13)
            self.assertIsNone(cache.get('example',NOW+timedelta(hours=2),1))
            report={'mode':'live','status':'watch_only','watchlist':[]}
            with patch('scanner.enrich.download',side_effect=OSError('Unavailable')):
                enriched=enrich_report(report,cache,NOW)
            self.assertEqual(enriched['status'],'partial')
            self.assertEqual(enriched['daily_brief']['tasks'],[])
            self.assertEqual(report['status'],'watch_only')


if __name__=='__main__':
    unittest.main()
