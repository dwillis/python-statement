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
                    parsed = datetime.datetime.strptime(normalized, fmt).date()
                    if parsed.year == 1900 and '%y' not in fmt.lower():
                        parsed = Utils._infer_year(parsed)
                    return parsed
                except ValueError:
                    continue
            # Try original text (unnormalized)
            for fmt in formats:
                try:
                    parsed = datetime.datetime.strptime(text, fmt).date()
                    if parsed.year == 1900 and '%y' not in fmt.lower():
                        parsed = Utils._infer_year(parsed)
                    return parsed
                except ValueError:
                    continue

        # Fallback: dateutil fuzzy parsing
        try:
            import re
            from dateutil import parser as dateutil_parser
            parsed = dateutil_parser.parse(text, fuzzy=True).date()
            # dateutil defaults missing year to current year (not 1900).
            # If the original text didn't contain a 4-digit or 2-digit year,
            # the year was inferred and is unreliable — return None.
            if parsed.year == 1900:
                return Utils._infer_year(parsed)
            has_year = bool(re.search(r'\b\d{4}\b', text) or re.search(r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b', text))
            if not has_year:
                return None
            return parsed
        except (ValueError, OverflowError, TypeError):
            return None

    @staticmethod
    def _infer_year(parsed):
        """Return None when the year had to be inferred (was 1900).

        Previously this guessed current/previous year, but that produces
        incorrect dates for historical pages. Returning None lets downstream
        consumers (e.g., collect_text.py) extract the real date from the
        individual release page instead.
        """
        return None
