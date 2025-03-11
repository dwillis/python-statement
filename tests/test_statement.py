#!/usr/bin/env python3
"""
Unit tests for the Statement module.
"""

import unittest
from unittest.mock import patch, MagicMock
import datetime
from statement_python import Feed, Scraper, Utils

class TestStatement(unittest.TestCase):
    """Test cases for the Statement module."""

    @patch('statement_python.requests.get')
    def test_parse_rss(self, mock_get):
        """Test parsing an RSS feed."""
        # Read the test XML file
        with open('tests/ruiz_rss.xml', 'r', encoding='utf-8') as file:
            mock_response = MagicMock()
            mock_response.content = file.read()
            mock_get.return_value = mock_response

        results = Feed.from_rss('https://ruiz.house.gov/rss.xml')
        self.assertIsNotNone(results)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['domain'], 'ruiz.house.gov')
        self.assertEqual(results[0]['title'], 'Dr. Ruiz Highlights First 100 Days in Congress')

    @patch('statement_python.Scraper.open_html')
    def test_crapo_scraper(self, mock_open_html):
        """Test the Crapo scraper."""
        # Set up mock response
        with open('tests/crapo_press.html', 'r', encoding='utf-8') as file:
            mock_soup = MagicMock()
            # Setup the mock to simulate BeautifulSoup behavior
            article_blocks = []
            for i in range(5):  # Mock 5 press releases
                block = MagicMock()
                link = MagicMock()
                link.get.return_value = f"/press-release/{i}"
                link.text = f"Press Release Title {i}"
                block.find.return_value = link
                p = MagicMock()
                p.text = "04.15.23"
                block.find_all.return_value = [p]
                article_blocks.append(block)
            
            mock_soup.find_all.return_value = article_blocks
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

if __name__ == '__main__':
    unittest.main()