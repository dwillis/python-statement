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


if __name__ == '__main__':
    unittest.main()
