import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scanner.publish import publish_report


@unittest.skipUnless(shutil.which('git'), 'Git required for report-branch integration checks')
class PublicReportPublishing(unittest.TestCase):
    def test_report_branch_preserves_main_and_publishes_failure_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / 'remote.git'
            work = root / 'work'
            work.mkdir()
            def git(*args, cwd=work):
                return subprocess.run(['git', *args], cwd=cwd, check=True, text=True,
                                      capture_output=True).stdout.strip()
            git('init', '--bare', str(remote), cwd=root)
            git('init', '--initial-branch=main')
            git('config', 'user.name', 'test')
            git('config', 'user.email', 'test@example.invalid')
            (work / 'README.md').write_text('source only', encoding='utf-8')
            git('add', 'README.md')
            git('commit', '-m', 'Initial source')
            git('remote', 'add', 'origin', str(remote))
            git('push', '-u', 'origin', 'main')
            head = git('rev-parse', 'HEAD')
            output = work / 'output'
            output.mkdir()
            (output / 'report.json').write_text(json.dumps({'status': 'watch_only'}), encoding='utf-8')
            (output / 'index.html').write_text('<p>Research</p>', encoding='utf-8')
            publish_report(work, output)
            git('fetch', 'origin', 'scanner-report')
            self.assertEqual(git('ls-tree', '--name-only', 'FETCH_HEAD').splitlines(), ['index.html', 'report.json'])
            self.assertEqual(git('rev-parse', 'HEAD'), head)
            self.assertEqual(publish_report(work, output), 'Report unchanged')
            (output / 'report.json').write_text(json.dumps({'status': 'unavailable'}), encoding='utf-8')
            (output / 'index.html').write_text('<p>Unavailable</p>', encoding='utf-8')
            publish_report(work, output)
            git('fetch', 'origin', 'scanner-report')
            self.assertEqual(json.loads(git('show', 'FETCH_HEAD:report.json'))['status'], 'unavailable')
            self.assertEqual(git('rev-parse', 'HEAD'), head)

    def test_partial_report_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'report.json').write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                publish_report(output, output)
