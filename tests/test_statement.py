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
        """Test the Crapo scraper via generic method with ArticleBlock + reversed a>h2."""
        html = """
        <html><body>
        <div class="ArticleBlock">
            <p class="Heading Heading--time">March 26, 2026</p>
            <a href="https://www.crapo.senate.gov/media/newsreleases/press-release-0">
                <h2 class="Heading__title ArticleTitle">Press Release Title 0</h2>
            </a>
        </div>
        <div class="ArticleBlock">
            <p class="Heading Heading--time">March 25, 2026</p>
            <a href="https://www.crapo.senate.gov/media/newsreleases/press-release-1">
                <h2 class="Heading__title ArticleTitle">Press Release Title 1</h2>
            </a>
        </div>
        </body></html>
        """
        from bs4 import BeautifulSoup
        mock_open_html.return_value = BeautifulSoup(html, 'lxml')

        results = Scraper.crapo()
        self.assertEqual(len(results), 2)
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

class TestDetailPageDate(unittest.TestCase):
    """Test generic_scraper fetching dates from detail pages."""

    LISTING_HTML = """
    <html><body>
      <div class="views-row">
        <div class="h3"><a href="/press/release-0"><span>Release Zero</span></a></div>
      </div>
      <div class="views-row">
        <div class="h3"><a href="/press/release-1"><span>Release One</span></a></div>
      </div>
    </body></html>
    """

    DETAIL_HTML = {
        'https://example.house.gov/press/release-0':
            '<html><body><div class="col-auto">August 5, 2026</div>'
            '<div class="col-auto">Press Release</div></body></html>',
        'https://example.house.gov/press/release-1':
            '<html><body><div class="col-auto">July 22, 2026</div></body></html>',
    }

    def _fake_open_html(self, url):
        from bs4 import BeautifulSoup
        if url in self.DETAIL_HTML:
            return BeautifulSoup(self.DETAIL_HTML[url], 'lxml')
        return BeautifulSoup(self.LISTING_HTML, 'lxml')

    @patch('python_statement.scraper.Scraper.open_html')
    def test_date_pulled_from_detail_page(self, mock_open_html):
        from python_statement import config
        mock_open_html.side_effect = self._fake_open_html
        config.SCRAPER_CONFIG['detailtest'] = {
            'method': 'generic',
            'url_base': 'https://example.house.gov/press',
            'container': '.views-row',
            'title_sel': '.h3 a',
            'detail_date_sel': '.col-auto',
            'date_fmt': ['%B %d, %Y'],
        }
        try:
            results = Scraper.run_scraper('detailtest', 1)
        finally:
            config.SCRAPER_CONFIG.pop('detailtest', None)

        self.assertEqual(len(results), 2)
        self.assertEqual(str(results[0]['date']), '2026-08-05')
        self.assertEqual(str(results[1]['date']), '2026-07-22')
        self.assertEqual(results[0]['title'], 'Release Zero')
        # One listing fetch + one detail fetch per dateless row.
        self.assertEqual(mock_open_html.call_count, 3)

    DATED_LISTING_HTML = """
    <html><body>
      <div class="views-row">
        <div class="h3"><a href="/press/release-0"><span>Release Zero</span></a></div>
        <div class="col-auto">March 3, 2026</div>
      </div>
    </body></html>
    """

    @patch('python_statement.scraper.Scraper.open_html')
    def test_detail_page_not_fetched_when_listing_has_date(self, mock_open_html):
        """detail_date_sel must not trigger a fetch when the row already has a date."""
        from bs4 import BeautifulSoup
        from python_statement import config
        mock_open_html.return_value = BeautifulSoup(self.DATED_LISTING_HTML, 'lxml')
        config.SCRAPER_CONFIG['detailtest'] = {
            'method': 'generic',
            'url_base': 'https://example.house.gov/press',
            'container': '.views-row',
            'title_sel': '.h3 a',
            'date_sel': '.col-auto',
            'detail_date_sel': '.col-auto',
            'date_fmt': ['%B %d, %Y'],
        }
        try:
            results = Scraper.run_scraper('detailtest', 1)
        finally:
            config.SCRAPER_CONFIG.pop('detailtest', None)

        self.assertEqual(len(results), 1)
        self.assertEqual(str(results[0]['date']), '2026-03-03')
        # Only the listing page should have been fetched — no detail fetch.
        self.assertEqual(mock_open_html.call_count, 1)


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