"""
Standalone tests for generic scraper methods.

These tests work with the generic_scrapers.py file before integration
into the main Scraper class.
"""

import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import datetime
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the generic scraper methods
from generic_scrapers import GenericScrapers


class TestTableRecordlistDate(unittest.TestCase):
    """Test the table_recordlist_date() generic method."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_html = """
        <html>
            <body>
                <table>
                    <tbody>
                        <tr>
                            <td class="recordListDate">01/15/24</td>
                            <td><a href="/press/release1">First Press Release</a></td>
                        </tr>
                        <tr>
                            <td class="recordListDate">01/14/24</td>
                            <td><a href="/press/release2">Second Press Release</a></td>
                        </tr>
                        <tr>
                            <td class="recordListDate">12/20/23</td>
                            <td><a href="/press/release3">Third Press Release</a></td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """

    @patch.object(GenericScrapers, 'open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with recordListDate pattern."""
        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = GenericScrapers.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
        self.assertTrue(results[0]['url'].startswith('https://'))

    @patch.object(GenericScrapers, 'open_html')
    def test_multiple_date_formats(self, mock_open_html):
        """Test parsing of multiple date formats."""
        html_with_different_dates = """
        <html>
            <body>
                <table>
                    <tbody>
                        <tr>
                            <td class="recordListDate">01/15/24</td>
                            <td><a href="/press/release1">Short year format</a></td>
                        </tr>
                        <tr>
                            <td class="recordListDate">01/15/2024</td>
                            <td><a href="/press/release2">Full year format</a></td>
                        </tr>
                        <tr>
                            <td class="recordListDate">01.15.24</td>
                            <td><a href="/press/release3">Dot format</a></td>
                        </tr>
                        <tr>
                            <td class="recordListDate">January 15, 2024</td>
                            <td><a href="/press/release4">Long format</a></td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_with_different_dates, 'html.parser')

        results = GenericScrapers.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        self.assertEqual(len(results), 4)
        # All should parse to the same date
        for result in results:
            self.assertEqual(result['date'], datetime.date(2024, 1, 15))

    @patch.object(GenericScrapers, 'open_html')
    def test_missing_elements(self, mock_open_html):
        """Test handling of missing elements."""
        html_with_missing = """
        <html>
            <body>
                <table>
                    <tbody>
                        <tr>
                            <td class="recordListDate">01/15/24</td>
                            <td><a href="/press/release1">Valid Release</a></td>
                        </tr>
                        <tr>
                            <td class="recordListDate">01/14/24</td>
                            <td>No link here</td>
                        </tr>
                        <tr>
                            <td>No date class</td>
                            <td><a href="/press/release3">Has link but no date</a></td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_with_missing, 'html.parser')

        results = GenericScrapers.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        # Should only return the valid row
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Valid Release')

    @patch.object(GenericScrapers, 'open_html')
    def test_network_error(self, mock_open_html):
        """Test handling of network errors."""
        mock_open_html.return_value = None

        results = GenericScrapers.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        self.assertEqual(len(results), 0)


class TestJetListingElementor(unittest.TestCase):
    """Test the jet_listing_elementor() generic method."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_html = """
        <html>
            <body>
                <div class="jet-listing-grid">
                    <div class="jet-listing-grid__item">
                        <h3><a href="https://example.com/press/release1">First Press Release</a></h3>
                        <li><span class="elementor-icon-list-text">January 15, 2024</span></li>
                    </div>
                    <div class="jet-listing-grid__item">
                        <h3><a href="https://example.com/press/release2">Second Press Release</a></h3>
                        <li><span class="elementor-icon-list-text">January 14, 2024</span></li>
                    </div>
                </div>
            </body>
        </html>
        """

    @patch.object(GenericScrapers, 'open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with jet listing pattern."""
        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = GenericScrapers.jet_listing_elementor(
            urls=["https://www.scott.senate.gov/media-center/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
        self.assertEqual(results[0]['url'], 'https://example.com/press/release1')


class TestArticleBlockH2PDate(unittest.TestCase):
    """Test the article_block_h2_p_date() generic method."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_html = """
        <html>
            <body>
                <div class="ArticleBlock">
                    <h2><a href="https://example.com/press/release1">First Press Release</a></h2>
                    <p>01/15/24</p>
                </div>
                <div class="ArticleBlock">
                    <h2><a href="https://example.com/press/release2">Second Press Release</a></h2>
                    <p>01.14.24</p>
                </div>
            </body>
        </html>
        """

    @patch.object(GenericScrapers, 'open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with ArticleBlock pattern."""
        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = GenericScrapers.article_block_h2_p_date(
            urls=["https://www.durbin.senate.gov/newsroom/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
        self.assertEqual(results[1]['date'], datetime.date(2024, 1, 14))

    @patch.object(GenericScrapers, 'open_html')
    def test_date_format_normalization(self, mock_open_html):
        """Test that dots in dates are normalized to slashes."""
        html_with_dots = """
        <html>
            <body>
                <div class="ArticleBlock">
                    <h2><a href="https://example.com/press/release1">Dot format</a></h2>
                    <p>01.15.2024</p>
                </div>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_with_dots, 'html.parser')

        results = GenericScrapers.article_block_h2_p_date(
            urls=["https://www.durbin.senate.gov/newsroom/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))


class TestTableTime(unittest.TestCase):
    """Test the table_time() generic method."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_html = """
        <html>
            <body>
                <table>
                    <tr>
                        <th>Title</th>
                        <th>Date</th>
                    </tr>
                    <tr>
                        <td><a href="/press/release1">First Press Release</a></td>
                        <td><time datetime="2024-01-15">01/15/24</time></td>
                    </tr>
                    <tr>
                        <td><a href="/press/release2">Second Press Release</a></td>
                        <td><time>01/14/24</time></td>
                    </tr>
                </table>
            </body>
        </html>
        """

    @patch.object(GenericScrapers, 'open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with table time pattern."""
        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = GenericScrapers.table_time(
            urls=["https://barr.house.gov/media-center/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))


class TestElementPostMedia(unittest.TestCase):
    """Test the element_post_media() generic method."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_html = """
        <html>
            <body>
                <div class="element">
                    <a href="https://example.com/press/release1">Link</a>
                    <div class="post-media-list-title">First Press Release</div>
                    <div class="post-media-list-date">January 15, 2024</div>
                </div>
                <div class="element">
                    <a href="https://example.com/press/release2">Link</a>
                    <div class="post-media-list-title">Second Press Release</div>
                    <div class="post-media-list-date">01/14/2024</div>
                </div>
            </body>
        </html>
        """

    @patch.object(GenericScrapers, 'open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with element post-media pattern."""
        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = GenericScrapers.element_post_media(
            urls=["https://www.wicker.senate.gov/media/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
        self.assertEqual(results[1]['date'], datetime.date(2024, 1, 14))


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
