"""
Feed class for parsing RSS and Atom feeds containing press releases.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import datetime
from dateutil import parser as date_parser

from .utils import Utils


class Feed:
    """Class for parsing RSS feeds."""

    @staticmethod
    def open_rss(url):
        """Open an RSS feed and return a BeautifulSoup object."""
        try:
            response = requests.get(url)
            return BeautifulSoup(response.content, 'xml')
        except Exception as e:
            print(f"Error opening RSS feed: {e}")
            return None

    @staticmethod
    def date_from_rss_item(item):
        """Extract date from an RSS item."""
        # Check for pubDate tag
        pub_date = item.find('pubDate')
        if pub_date and pub_date.text:
            try:
                # Use dateutil for more flexible date parsing
                return date_parser.parse(pub_date.text).date()
            except (ValueError, TypeError):
                pass

        # Check for pubdate tag (alternate case)
        pub_date = item.find('pubdate')
        if pub_date and pub_date.text:
            try:
                return date_parser.parse(pub_date.text).date()
            except (ValueError, TypeError):
                pass

        # Special case for Mikulski senate URLs
        link = item.find('link')
        if link and link.text and "mikulski.senate.gov" in link.text and "-2014" in link.text:
            try:
                date_part = link.text.split('/')[-1].split('-', -1)[:3]
                date_str = '/'.join(date_part).split('.cfm')[0]
                return date_parser.parse(date_str).date()
            except (ValueError, IndexError):
                pass

        return None

    @classmethod
    def from_rss(cls, url):
        """Parse an RSS feed and return a list of items."""
        doc = cls.open_rss(url)
        if not doc:
            return []

        # Check if it's an Atom feed
        if doc.find('feed'):
            return cls.parse_atom(doc, url)

        # Otherwise, assume it's RSS
        return cls.parse_rss(doc, url)

    @classmethod
    def parse_rss(cls, doc, url):
        """Parse an RSS feed and return a list of items."""
        items = doc.find_all('item')
        if not items:
            return []

        results = []
        for item in items:
            link_tag = item.find('link')
            if not link_tag:
                continue

            link = link_tag.text
            abs_link = Utils.absolute_link(url, link)

            # Special case for some websites
            if url == 'http://www.burr.senate.gov/public/index.cfm?FuseAction=RSS.Feed':
                abs_link = "http://www.burr.senate.gov/public/" + link
            elif url == "http://www.johanns.senate.gov/public/?a=RSS.Feed":
                abs_link = link[37:]

            result = {
                'source': url,
                'url': abs_link,
                'title': item.find('title').text if item.find('title') else '',
                'date': cls.date_from_rss_item(item),
                'domain': urlparse(url).netloc
            }
            results.append(result)

        return Utils.remove_generic_urls(results)

    @classmethod
    def parse_atom(cls, doc, url):
        """Parse an Atom feed and return a list of items."""
        entries = doc.find_all('entry')
        if not entries:
            return []

        results = []
        for entry in entries:
            link = entry.find('link')
            if not link:
                continue

            pub_date = entry.find('published') or entry.find('updated')
            date = datetime.datetime.strptime(pub_date.text, "%Y-%m-%dT%H:%M:%S%z").date() if pub_date else None

            result = {
                'source': url,
                'url': link.get('href'),
                'title': entry.find('title').text if entry.find('title') else '',
                'date': date,
                'domain': urlparse(url).netloc
            }
            results.append(result)

        return results

    @classmethod
    def batch(cls, urls):
        """Batch process multiple RSS feeds."""
        results = []
        failures = []

        for url in urls:
            try:
                feed_results = cls.from_rss(url)
                if feed_results:
                    results.extend(feed_results)
                else:
                    failures.append(url)
            except Exception as e:
                print(f"Error processing {url}: {e}")
                failures.append(url)

        return results, failures
