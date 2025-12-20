"""
Comprehensive tests for generic scraper methods.

This test suite validates that the generic scraper methods can correctly parse
HTML from congressional member websites and extract press release information.

Author: Generated for python-statement consolidation
Date: 2025-12-20
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urlparse

# Import the Scraper class (assuming it's in statement.py)
# from python_statement.statement import Scraper


class MockScraper:
    """Mock Scraper class with generic methods for testing."""

    @staticmethod
    def open_html(url):
        """Mock open_html method - will be patched in tests."""
        pass

    # Include the generic methods here for testing
    # In production, these would be added to the actual Scraper class


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

    @patch('python_statement.statement.Scraper.open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with recordListDate pattern."""
        from python_statement.statement import Scraper

        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = Scraper.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
        self.assertTrue(results[0]['url'].startswith('https://'))

    @patch('python_statement.statement.Scraper.open_html')
    def test_multiple_date_formats(self, mock_open_html):
        """Test parsing of multiple date formats."""
        from python_statement.statement import Scraper

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

        results = Scraper.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        self.assertEqual(len(results), 4)
        # All should parse to the same date
        for result in results:
            self.assertEqual(result['date'], datetime.date(2024, 1, 15))

    @patch('python_statement.statement.Scraper.open_html')
    def test_missing_elements(self, mock_open_html):
        """Test handling of missing elements."""
        from python_statement.statement import Scraper

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

        results = Scraper.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        # Should only return the valid row
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Valid Release')

    @patch('python_statement.statement.Scraper.open_html')
    def test_absolute_and_relative_urls(self, mock_open_html):
        """Test handling of both absolute and relative URLs."""
        from python_statement.statement import Scraper

        html_with_mixed_urls = """
        <html>
            <body>
                <table>
                    <tbody>
                        <tr>
                            <td class="recordListDate">01/15/24</td>
                            <td><a href="/press/release1">Relative URL</a></td>
                        </tr>
                        <tr>
                            <td class="recordListDate">01/14/24</td>
                            <td><a href="https://example.com/press/release2">Absolute URL</a></td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_with_mixed_urls, 'html.parser')

        results = Scraper.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        # Relative URL should be converted to absolute
        self.assertTrue(results[0]['url'].startswith('https://www.moran.senate.gov'))
        # Absolute URL should remain unchanged
        self.assertEqual(results[1]['url'], 'https://example.com/press/release2')

    @patch('python_statement.statement.Scraper.open_html')
    def test_empty_table(self, mock_open_html):
        """Test handling of empty table."""
        from python_statement.statement import Scraper

        html_empty = """
        <html>
            <body>
                <table>
                    <tbody>
                    </tbody>
                </table>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_empty, 'html.parser')

        results = Scraper.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=1
        )

        self.assertEqual(len(results), 0)

    @patch('python_statement.statement.Scraper.open_html')
    def test_network_error(self, mock_open_html):
        """Test handling of network errors."""
        from python_statement.statement import Scraper

        mock_open_html.return_value = None

        results = Scraper.table_recordlist_date(
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

    @patch('python_statement.statement.Scraper.open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with jet listing pattern."""
        from python_statement.statement import Scraper

        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = Scraper.jet_listing_elementor(
            urls=["https://www.scott.senate.gov/media-center/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
        self.assertEqual(results[0]['url'], 'https://example.com/press/release1')

    @patch('python_statement.statement.Scraper.open_html')
    def test_alternative_selector(self, mock_open_html):
        """Test parsing with alternative elementor-widget-wrap selector."""
        from python_statement.statement import Scraper

        html_alternative = """
        <html>
            <body>
                <div class="elementor-widget-wrap">
                    <h3><a href="https://example.com/press/release1">First Press Release</a></h3>
                    <span class="elementor-icon-list-text">January 15, 2024</span>
                </div>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_alternative, 'html.parser')

        results = Scraper.jet_listing_elementor(
            urls=["https://www.scott.senate.gov/media-center/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'First Press Release')

    @patch('python_statement.statement.Scraper.open_html')
    def test_multiple_date_formats(self, mock_open_html):
        """Test parsing of multiple date formats."""
        from python_statement.statement import Scraper

        html_different_dates = """
        <html>
            <body>
                <div class="jet-listing-grid">
                    <div class="jet-listing-grid__item">
                        <h3><a href="/press/release1">Long format</a></h3>
                        <span class="elementor-icon-list-text">January 15, 2024</span>
                    </div>
                    <div class="jet-listing-grid__item">
                        <h3><a href="/press/release2">Slash format full</a></h3>
                        <span class="elementor-icon-list-text">01/15/2024</span>
                    </div>
                    <div class="jet-listing-grid__item">
                        <h3><a href="/press/release3">Slash format short</a></h3>
                        <span class="elementor-icon-list-text">01/15/24</span>
                    </div>
                </div>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_different_dates, 'html.parser')

        results = Scraper.jet_listing_elementor(
            urls=["https://www.scott.senate.gov/media-center/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 3)
        # All should parse to the same date
        for result in results:
            self.assertEqual(result['date'], datetime.date(2024, 1, 15))


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

    @patch('python_statement.statement.Scraper.open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with ArticleBlock pattern."""
        from python_statement.statement import Scraper

        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = Scraper.article_block_h2_p_date(
            urls=["https://www.durbin.senate.gov/newsroom/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
        self.assertEqual(results[1]['date'], datetime.date(2024, 1, 14))

    @patch('python_statement.statement.Scraper.open_html')
    def test_h3_fallback(self, mock_open_html):
        """Test fallback to h3 when h2 is not present."""
        from python_statement.statement import Scraper

        html_with_h3 = """
        <html>
            <body>
                <div class="ArticleBlock">
                    <h3><a href="https://example.com/press/release1">H3 Press Release</a></h3>
                    <p>01/15/24</p>
                </div>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_with_h3, 'html.parser')

        results = Scraper.article_block_h2_p_date(
            urls=["https://www.durbin.senate.gov/newsroom/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'H3 Press Release')

    @patch('python_statement.statement.Scraper.open_html')
    def test_time_element(self, mock_open_html):
        """Test parsing with time element instead of p tag."""
        from python_statement.statement import Scraper

        html_with_time = """
        <html>
            <body>
                <div class="ArticleBlock">
                    <h2><a href="https://example.com/press/release1">Press Release</a></h2>
                    <time datetime="2024-01-15">January 15, 2024</time>
                </div>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_with_time, 'html.parser')

        results = Scraper.article_block_h2_p_date(
            urls=["https://www.durbin.senate.gov/newsroom/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))

    @patch('python_statement.statement.Scraper.open_html')
    def test_date_format_normalization(self, mock_open_html):
        """Test that dots in dates are normalized to slashes."""
        from python_statement.statement import Scraper

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

        results = Scraper.article_block_h2_p_date(
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

    @patch('python_statement.statement.Scraper.open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with table time pattern."""
        from python_statement.statement import Scraper

        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = Scraper.table_time(
            urls=["https://barr.house.gov/media-center/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))

    @patch('python_statement.statement.Scraper.open_html')
    def test_datetime_attribute(self, mock_open_html):
        """Test that datetime attribute is preferred over text."""
        from python_statement.statement import Scraper

        html_with_datetime = """
        <html>
            <body>
                <table>
                    <tr>
                        <td><a href="/press/release1">Press Release</a></td>
                        <td><time datetime="2024-01-15">Wrong date text</time></td>
                    </tr>
                </table>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_with_datetime, 'html.parser')

        results = Scraper.table_time(
            urls=["https://barr.house.gov/media-center/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 1)
        # Should use datetime attribute, not text
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

    @patch('python_statement.statement.Scraper.open_html')
    def test_basic_parsing(self, mock_open_html):
        """Test basic HTML parsing with element post-media pattern."""
        from python_statement.statement import Scraper

        mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

        results = Scraper.element_post_media(
            urls=["https://www.wicker.senate.gov/media/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'First Press Release')
        self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
        self.assertEqual(results[1]['date'], datetime.date(2024, 1, 14))

    @patch('python_statement.statement.Scraper.open_html')
    def test_alternative_class_names(self, mock_open_html):
        """Test parsing with alternative class names (element-title, element-datetime)."""
        from python_statement.statement import Scraper

        html_alternative = """
        <html>
            <body>
                <div class="element">
                    <a href="https://example.com/press/release1">Link</a>
                    <div class="element-title">Alternative Class Press Release</div>
                    <div class="element-datetime">January 15, 2024</div>
                </div>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(html_alternative, 'html.parser')

        results = Scraper.element_post_media(
            urls=["https://www.wicker.senate.gov/media/press-releases"],
            page=1
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Alternative Class Press Release')


class TestIntegration(unittest.TestCase):
    """Integration tests for multiple URLs and edge cases."""

    @patch('python_statement.statement.Scraper.open_html')
    def test_multiple_urls(self, mock_open_html):
        """Test processing multiple URLs in a single call."""
        from python_statement.statement import Scraper

        sample_html = """
        <html>
            <body>
                <table>
                    <tbody>
                        <tr>
                            <td class="recordListDate">01/15/24</td>
                            <td><a href="/press/release1">Press Release</a></td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(sample_html, 'html.parser')

        results = Scraper.table_recordlist_date(
            urls=[
                "https://www.moran.senate.gov/public/index.cfm/news-releases",
                "https://www.boozman.senate.gov/public/index.cfm/press-releases",
                "https://www.thune.senate.gov/public/index.cfm/press-releases"
            ],
            page=1
        )

        # Should have results from all three URLs
        self.assertEqual(len(results), 3)

    @patch('python_statement.statement.Scraper.open_html')
    def test_pagination(self, mock_open_html):
        """Test that pagination parameter is applied correctly."""
        from python_statement.statement import Scraper

        sample_html = """
        <html>
            <body>
                <table>
                    <tbody>
                        <tr>
                            <td class="recordListDate">01/15/24</td>
                            <td><a href="/press/release1">Press Release</a></td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """

        mock_open_html.return_value = BeautifulSoup(sample_html, 'html.parser')

        # Test with page 2
        results = Scraper.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=2
        )

        # Verify the URL was called with page=2
        mock_open_html.assert_called_once()
        called_url = mock_open_html.call_args[0][0]
        self.assertIn('page=2', called_url)


def run_tests():
    """Run all tests."""
    unittest.main()


if __name__ == '__main__':
    run_tests()
