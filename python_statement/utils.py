"""
Utility classes for the Statement module.
"""

import datetime
from urllib.parse import urljoin, urlparse


class Statement:
    """Main class for the Statement module."""

    @staticmethod
    def configure(config=None):
        """Configure with a dictionary."""
        if config is None:
            config = {}
        return config

    @staticmethod
    def configure_with(path_to_yaml_file):
        """Configure with a YAML file."""
        try:
            import yaml
            with open(path_to_yaml_file, 'r') as file:
                config = yaml.safe_load(file)
            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return {}


class Utils:
    """Utility methods for the Statement module."""

    @staticmethod
    def absolute_link(url, link):
        """Convert a relative link to an absolute link."""
        if link.startswith('http'):
            return link
        return urljoin(url, link)

    @staticmethod
    def remove_generic_urls(results):
        """Remove generic URLs from results."""
        if not results:
            return []

        filtered_results = [r for r in results if r and 'url' in r]
        return [r for r in filtered_results if urlparse(r['url']).path not in ['/news/', '/news']]

    @staticmethod
    def parse_date(text, formats=None):
        """Parse a date string, trying explicit formats first, then dateutil fallback.

        Args:
            text: Date string to parse (e.g., "January 15, 2024", "01/15/24")
            formats: Optional list of strptime format strings to try first

        Returns:
            datetime.date or None
        """
        if not text:
            return None
        text = text.strip()
        if not text:
            return None

        if formats:
            # First pass: normalize dots to slashes for numeric formats like
            # "01.15.24" → "01/15/24". Second pass tries original text for
            # abbreviated months like "Jan. 15, 2024" where dots aren't separators.
            normalized = text.replace('.', '/')
            for fmt in formats:
                try:
                    return datetime.datetime.strptime(normalized, fmt).date()
                except ValueError:
                    continue
            # Try original text (unnormalized)
            for fmt in formats:
                try:
                    return datetime.datetime.strptime(text, fmt).date()
                except ValueError:
                    continue

        # Fallback: dateutil fuzzy parsing
        try:
            from dateutil import parser as dateutil_parser
            return dateutil_parser.parse(text, fuzzy=True).date()
        except (ValueError, OverflowError, TypeError):
            return None
