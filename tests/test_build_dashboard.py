#!/usr/bin/env python3
"""Unit tests for the dashboard's stale-scraper enrichment."""

import datetime
import unittest
from unittest.mock import patch

from scripts.build_dashboard import enrich_results


class TestEnrichResultsStaleness(unittest.TestCase):
    """Tests for days_since / is_stale added to enrich_results()."""

    @patch('scripts.build_dashboard.datetime')
    def test_marks_ok_scraper_stale_at_30_days(self, mock_datetime):
        mock_datetime.date.today.return_value = datetime.date(2026, 8, 9)
        mock_datetime.date.fromisoformat = datetime.date.fromisoformat
        results = [
            {'name': 'stale_member', 'status': 'ok', 'latest_date': '2026-07-10'},
        ]
        enrich_results(results)
        self.assertEqual(results[0]['days_since'], 30)
        self.assertTrue(results[0]['is_stale'])

    @patch('scripts.build_dashboard.datetime')
    def test_does_not_mark_recent_ok_scraper_stale(self, mock_datetime):
        mock_datetime.date.today.return_value = datetime.date(2026, 8, 9)
        mock_datetime.date.fromisoformat = datetime.date.fromisoformat
        results = [
            {'name': 'fresh_member', 'status': 'ok', 'latest_date': '2026-08-01'},
        ]
        enrich_results(results)
        self.assertEqual(results[0]['days_since'], 8)
        self.assertFalse(results[0]['is_stale'])

    def test_error_status_is_never_stale(self):
        results = [
            {'name': 'broken_member', 'status': 'error', 'latest_date': None},
        ]
        enrich_results(results)
        self.assertIsNone(results[0]['days_since'])
        self.assertFalse(results[0]['is_stale'])


class TestCommitteePanel(unittest.TestCase):
    """Tests for the Committees tab."""

    COMMITTEES = [
        {'thomas_id': 'HSAG', 'name': 'House Committee on Agriculture', 'type': 'house'},
    ]

    def test_enrich_reads_committee_config(self):
        from python_statement.committee_config import COMMITTEE_CONFIG
        results = [{'name': 'hsag_minority', 'status': 'ok', 'latest_date': None}]
        enrich_results(results)
        self.assertEqual(results[0]['url_base'], COMMITTEE_CONFIG['hsag_minority']['url_base'])
        self.assertEqual(results[0]['config_method'], 'generic')

    @patch('scripts.build_dashboard.datetime')
    def test_panel_rows_show_committee_side_and_staleness(self, mock_datetime):
        from scripts.build_dashboard import build_committee_panel
        mock_datetime.date.today.return_value = datetime.date(2026, 11, 21)
        mock_datetime.date.fromisoformat = datetime.date.fromisoformat
        report = {
            'timestamp': '2026-11-21T09:00:00',
            'summary': {'total': 2, 'ok': 1, 'empty': 1, 'no_dates': 0, 'errors': 0,
                        'success_rate': 50.0},
            'results': [
                {'name': 'hsag_majority', 'status': 'ok', 'count': 10, 'duration_ms': 5,
                 'latest_date': '2026-09-01', 'error': None},
                {'name': 'hsag_minority', 'status': 'empty', 'count': 0, 'duration_ms': 5,
                 'latest_date': None, 'error': None},
            ],
        }
        panel = build_committee_panel(report, self.COMMITTEES)
        self.assertIn('House Committee on Agriculture', panel)
        self.assertIn('majority', panel)
        self.assertIn('minority', panel)
        self.assertIn('badge-stale', panel)   # 81 days old
        self.assertIn('badge-empty', panel)
        self.assertIn('Report Issue', panel)  # failing row gets an issue link

    def test_panel_without_report_explains_how_to_run(self):
        from scripts.build_dashboard import build_committee_panel
        panel = build_committee_panel(None, self.COMMITTEES)
        self.assertIn('--collection committees', panel)


if __name__ == '__main__':
    unittest.main()
