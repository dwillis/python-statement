#!/usr/bin/env python3
"""Unit tests for HealthChecker."""

import datetime
import unittest
from unittest.mock import patch

from python_statement.health import HealthChecker


class TestCheckScraperLatestDate(unittest.TestCase):
    """Tests for the latest_date field added to check_scraper()."""

    @patch('python_statement.health.Scraper.run_scraper')
    def test_latest_date_is_max_date_as_iso_string(self, mock_run):
        mock_run.return_value = [
            {'title': 'Older', 'date': datetime.date(2026, 6, 1)},
            {'title': 'Newest', 'date': datetime.date(2026, 7, 15)},
            {'title': 'Middle', 'date': datetime.date(2026, 6, 20)},
        ]
        result = HealthChecker.check_scraper('somemember')
        self.assertEqual(result['latest_date'], '2026-07-15')

    @patch('python_statement.health.Scraper.run_scraper')
    def test_latest_date_is_none_when_no_dates(self, mock_run):
        mock_run.return_value = [
            {'title': 'No date', 'date': None},
        ]
        result = HealthChecker.check_scraper('somemember')
        self.assertIsNone(result['latest_date'])

    @patch('python_statement.health.Scraper.run_scraper')
    def test_latest_date_is_none_when_empty(self, mock_run):
        mock_run.return_value = []
        result = HealthChecker.check_scraper('somemember')
        self.assertIsNone(result['latest_date'])


if __name__ == '__main__':
    unittest.main()
