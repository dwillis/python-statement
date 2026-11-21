#!/usr/bin/env python3
"""Tests for member vs committee health-check collections."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from python_statement.health import HealthChecker


def _ok(name, timeout=30):
    return {'name': name, 'status': 'ok', 'count': 3, 'has_dates': True,
            'latest_date': '2026-11-20', 'duration_ms': 1, 'error': None}


@patch.object(HealthChecker, 'check_scraper', side_effect=_ok)
class TestRunCollections(unittest.TestCase):

    @patch('python_statement.health.Scraper.committee_methods',
           return_value=['hsag_majority', 'hsag_minority'])
    def test_committees_runs_every_committee_scraper(self, _cm, _check):
        report = HealthChecker.run(collection='committees', verbose=False)
        self.assertEqual([r['name'] for r in report['results']],
                         ['hsag_majority', 'hsag_minority'])
        self.assertEqual(report['collection'], 'committees')
        self.assertEqual(report['mode'], 'full')

    @patch('python_statement.health.Scraper.committee_methods', return_value=['hsag_majority'])
    def test_committees_ignores_quick_mode(self, _cm, _check):
        report = HealthChecker.run(mode='quick', collection='committees', verbose=False)
        self.assertEqual(report['summary']['total'], 1)
        self.assertEqual(report['mode'], 'full')

    @patch('python_statement.health.Scraper.member_methods', return_value=['fuller', 'mejia'])
    def test_members_full_uses_member_methods(self, _mm, _check):
        report = HealthChecker.run(mode='full', verbose=False)
        self.assertEqual(report['summary']['total'], 2)
        self.assertEqual(report['collection'], 'members')

    def test_explicit_scraper_list(self, _check):
        report = HealthChecker.run(scrapers=['a', 'b', 'c'], verbose=False)
        self.assertEqual(report['summary']['total'], 3)

    def test_unknown_collection_rejected(self, _check):
        with self.assertRaises(ValueError):
            HealthChecker.run(collection='caucuses', verbose=False)


class TestCollectionPaths(unittest.TestCase):

    def test_paths(self):
        self.assertEqual(HealthChecker.paths_for('members'),
                         ('health_results.json', 'health_history.jsonl'))
        self.assertEqual(HealthChecker.paths_for('committees'),
                         ('committee_health_results.json', 'committee_health_history.jsonl'))
        with self.assertRaises(ValueError):
            HealthChecker.paths_for('nope')


class TestFailuresAndHistory(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    @patch.object(HealthChecker, 'check_scraper', side_effect=_ok)
    def test_failures_only_reruns_named_committees(self, check):
        path = os.path.join(self.tmp.name, 'committee_health_results.json')
        with open(path, 'w') as f:
            json.dump({'results': [
                {'name': 'hsag_majority', 'status': 'ok'},
                {'name': 'ssfi_minority', 'status': 'empty'},
            ]}, f)
        report = HealthChecker.run_failures_only(path=path, collection='committees',
                                                 verbose=False)
        self.assertEqual([r['name'] for r in report['results']], ['ssfi_minority'])
        self.assertEqual(report['collection'], 'committees')
        self.assertEqual(report['mode'], 'failures-only')

    def test_history_line_records_collection(self):
        path = os.path.join(self.tmp.name, 'h.jsonl')
        report = {'timestamp': 't', 'mode': 'full', 'collection': 'committees',
                  'summary': {'total': 1, 'ok': 0, 'empty': 1, 'no_dates': 0, 'errors': 0},
                  'results': [{'name': 'ssfi_minority', 'status': 'empty'}]}
        HealthChecker.append_history(report, path)
        with open(path) as f:
            entry = json.loads(f.readline())
        self.assertEqual(entry['collection'], 'committees')
        self.assertEqual(entry['failures'], ['ssfi_minority'])


if __name__ == '__main__':
    unittest.main()
