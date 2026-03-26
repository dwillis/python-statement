#!/usr/bin/env python3
"""
Unit tests for the Statement module.
"""

import unittest
from unittest.mock import patch, MagicMock
import datetime
from python_statement import Feed, Scraper, Utils

class TestStatement(unittest.TestCase):
    """Test cases for the Statement module."""

    @patch('python_statement.feed.requests.get')
    def test_parse_rss(self, mock_get):
        """Test parsing an RSS feed."""
        # Read the test XML file
        with open('tests/fixtures/ruiz_rss.xml', 'r', encoding='utf-8') as file:
            mock_response = MagicMock()
            mock_response.content = file.read()
            mock_get.return_value = mock_response

        results = Feed.from_rss('https://ruiz.house.gov/rss.xml')
        self.assertIsNotNone(results)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['domain'], 'ruiz.house.gov')
        self.assertEqual(results[0]['title'], 'Dr. Ruiz Highlights First 100 Days in Congress')

    @patch('python_statement.scraper.Scraper.open_html')
    def test_crapo_scraper(self, mock_open_html):
        """Test the Crapo scraper via article_block_h2_p_date generic method."""
        mock_soup = MagicMock()
        article_blocks = []

        def make_block(i):
            block = MagicMock()
            link = MagicMock()
            link.get.return_value = f"/press-release/{i}"
            link.text = f"  Press Release Title {i}  "
            link.name = 'a'
            p_elem = MagicMock(text="04.15.23", name='p')
            p_elem.get.return_value = None
            def select_one(sel, _link=link, _p=p_elem):
                return {'h2 a': _link, 'h3 a': None, 'p': _p, 'time': None}.get(sel)
            block.select_one = select_one
            return block

        for i in range(5):
            article_blocks.append(make_block(i))

        mock_soup.select.return_value = article_blocks
        mock_open_html.return_value = mock_soup

        results = Scraper.crapo()
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]['title'], "Press Release Title 0")
        self.assertEqual(results[0]['domain'], 'www.crapo.senate.gov')
        
    def test_absolute_link(self):
        """Test the absolute_link utility function."""
        self.assertEqual(
            Utils.absolute_link('http://example.com/path/', 'subpage.html'),
            'http://example.com/path/subpage.html'
        )
        self.assertEqual(
            Utils.absolute_link('http://example.com/path/', 'http://other.com/page'),
            'http://other.com/page'
        )

    def test_remove_generic_urls(self):
        """Test the remove_generic_urls utility function."""
        input_data = [
            {'url': 'http://example.com/news/'},
            {'url': 'http://example.com/press-release/1'},
            {'url': 'http://example.com/news'},
            None,
            {'title': 'Missing URL'}
        ]
        expected = [
            {'url': 'http://example.com/press-release/1'}
        ]
        self.assertEqual(Utils.remove_generic_urls(input_data), expected)

class TestParseDate(unittest.TestCase):
    """Test cases for Utils.parse_date()."""

    def test_explicit_format_match(self):
        d = Utils.parse_date('01/15/24', ['%m/%d/%y'])
        self.assertEqual(str(d), '2024-01-15')

    def test_dot_normalization(self):
        d = Utils.parse_date('01.15.24', ['%m/%d/%y'])
        self.assertEqual(str(d), '2024-01-15')

    def test_unnormalized_pass_handles_abbreviated_months(self):
        d = Utils.parse_date('Jan. 15, 2024', ['%b. %d, %Y'])
        self.assertEqual(str(d), '2024-01-15')

    def test_dateutil_fallback_no_formats(self):
        d = Utils.parse_date('January 15, 2024')
        self.assertEqual(str(d), '2024-01-15')

    def test_dateutil_fallback_when_formats_fail(self):
        d = Utils.parse_date('Mar 5, 2026', ['%m/%d/%y'])
        self.assertEqual(str(d), '2026-03-05')

    def test_none_input(self):
        self.assertIsNone(Utils.parse_date(None))

    def test_empty_string(self):
        self.assertIsNone(Utils.parse_date(''))

    def test_whitespace_only(self):
        self.assertIsNone(Utils.parse_date('   '))

    def test_garbage_string(self):
        self.assertIsNone(Utils.parse_date('not a date'))

    def test_multiple_formats_tries_all(self):
        d = Utils.parse_date('January 15, 2024', ['%m/%d/%y', '%B %d, %Y'])
        self.assertEqual(str(d), '2024-01-15')


if __name__ == '__main__':
    unittest.main()