"""
Generic scraper methods for consolidating member-specific scrapers.

These methods implement common scraping patterns used across multiple
congressional member websites, reducing code duplication and improving
maintainability.

Author: Generated for python-statement consolidation
Date: 2025-12-20
"""

import datetime
from urllib.parse import urlparse


class GenericScrapers:
    """Collection of generic scraper methods to be added to the Scraper class."""

    @classmethod
    def table_recordlist_date(cls, urls=None, page=1):
        """
        Scrape press releases from websites with table tbody tr and td.recordListDate.

        This pattern is used by Senate sites that display press releases in a table
        with a specific recordListDate class for the date column.

        Args:
            urls: List of URLs to scrape (default: None)
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain

        Example URLs:
            - https://www.moran.senate.gov/public/index.cfm/news-releases
            - https://www.boozman.senate.gov/public/index.cfm/press-releases
            - https://www.thune.senate.gov/public/index.cfm/press-releases
            - https://www.barrasso.senate.gov/public/index.cfm/news-releases
            - https://www.lgraham.senate.gov/public/index.cfm/press-releases
        """
        results = []
        if urls is None:
            urls = []

        for url in urls:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}?page={page}" if "?" not in url else f"{url}&page={page}"

            doc = cls.open_html(source_url)
            if not doc:
                continue

            rows = doc.select("table tbody tr")
            for row in rows:
                link = row.select_one('a')
                date_cell = row.select_one('td.recordListDate')

                if not (link and date_cell):
                    continue

                # Parse date with multiple format attempts
                date = None
                date_text = date_cell.text.strip()

                # Try multiple date formats
                date_formats = [
                    "%m/%d/%y",      # 01/15/24
                    "%m/%d/%Y",      # 01/15/2024
                    "%m.%d.%y",      # 01.15.24
                    "%m.%d.%Y",      # 01.15.2024
                    "%B %d, %Y",     # January 15, 2024
                ]

                for fmt in date_formats:
                    try:
                        date = datetime.datetime.strptime(date_text, fmt).date()
                        break
                    except ValueError:
                        continue

                # Handle relative URL
                href = link.get('href')
                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://{domain}{href}"

                result = {
                    'source': url,
                    'url': full_url,
                    'title': link.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    @classmethod
    def jet_listing_elementor(cls, urls=None, page=1):
        """
        Scrape press releases from websites using Jet Engine listing with Elementor.

        This pattern is used by sites built with WordPress, Elementor, and the Jet Engine plugin.
        The press releases are displayed in a grid with each item containing an h3 link and
        an elementor-icon-list-text span for the date.

        Args:
            urls: List of URLs to scrape (default: None)
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain

        Example URLs:
            - https://www.scott.senate.gov/media-center/press-releases (timscott)
            - https://www.fetterman.senate.gov/press-releases (fetterman)
            - https://www.tester.senate.gov/newsroom/press-releases (tester)
            - https://www.hawley.senate.gov/media/press-releases (hawley)
            - https://www.marshall.senate.gov/media/press-releases (marshall)
        """
        results = []
        if urls is None:
            urls = []

        for url in urls:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Handle different URL structures for pagination
            if "?jsf=" in url:
                source_url = f"{url}&pagenum={page}"
            elif "/pagenum/" in url:
                # Replace existing page number or add it
                if f"/pagenum/{page}/" in url:
                    source_url = url
                else:
                    # Find and replace the page number
                    import re
                    source_url = re.sub(r'/pagenum/\d+/', f'/pagenum/{page}/', url)
                    if '/pagenum/' not in source_url:
                        source_url = f"{url.rstrip('/')}/pagenum/{page}/"
            elif "/jsf/" in url:
                source_url = f"{url}/pagenum/{page}/"
            else:
                source_url = f"{url}{'&' if '?' in url else '?'}jsf=jet-engine:press-list&pagenum={page}"

            doc = cls.open_html(source_url)
            if not doc:
                continue

            # Try both possible selectors for jet listing items
            items = doc.select(".jet-listing-grid__item")
            if not items:
                items = doc.select(".elementor-widget-wrap")

            for row in items:
                link = row.select_one("h3 a")
                if not link:
                    continue

                # Try multiple selectors for date
                date_elem = (
                    row.select_one("span.elementor-icon-list-text") or
                    row.select_one("li span.elementor-icon-list-text") or
                    row.select_one(".elementor-post-date")
                )

                date = None
                if date_elem:
                    date_text = date_elem.text.strip()
                    date_formats = [
                        "%B %d, %Y",     # January 15, 2024
                        "%m/%d/%Y",      # 01/15/2024
                        "%m/%d/%y",      # 01/15/24
                    ]

                    for fmt in date_formats:
                        try:
                            date = datetime.datetime.strptime(date_text, fmt).date()
                            break
                        except ValueError:
                            continue

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': link.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    @classmethod
    def article_block_h2_p_date(cls, urls=None, page=1):
        """
        Scrape press releases from websites with ArticleBlock class, h2 titles, and date in p tag.

        This is an enhanced version that handles multiple date formats automatically.
        Used by many Senate sites that use the ArticleBlock layout pattern.

        Args:
            urls: List of URLs to scrape (default: None)
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain

        Example URLs:
            - https://www.durbin.senate.gov/newsroom/press-releases (durbin)
            - https://www.brown.senate.gov/newsroom/press (sherrod_brown)
            - https://www.crapo.senate.gov/media/newsreleases (crapo)
            - https://www.hirono.senate.gov/news/press-releases (hirono)
            - https://www.ernst.senate.gov/news/press-releases (ernst)
        """
        results = []
        if urls is None:
            urls = []

        for url in urls:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Handle different URL structures for pagination
            if "PageNum_rs" in url:
                source_url = url  # Already has PageNum_rs
                if f"PageNum_rs={page}" not in url:
                    import re
                    source_url = re.sub(r'PageNum_rs=\d+', f'PageNum_rs={page}', url)
            elif "?" in url:
                source_url = f"{url}&PageNum_rs={page}"
            else:
                source_url = f"{url}?PageNum_rs={page}"

            doc = cls.open_html(source_url)
            if not doc:
                continue

            blocks = doc.select("div.ArticleBlock")
            for row in blocks:
                # Try h2 first, then h3 as fallback
                link = row.select_one("h2 a")
                if not link:
                    link = row.select_one("h3 a")

                if not link:
                    continue

                # Get date from p tag or time tag
                date_elem = row.select_one("p") or row.select_one("time")
                date = None

                if date_elem:
                    date_text = date_elem.text.strip()
                    if date_elem.name == 'time' and date_elem.get('datetime'):
                        date_text = date_elem.get('datetime')

                    # Replace dots with slashes for consistent parsing
                    date_text_normalized = date_text.replace(".", "/")

                    # Try multiple date formats
                    date_formats = [
                        "%m/%d/%y",      # 01/15/24 or 01.15.24
                        "%m/%d/%Y",      # 01/15/2024 or 01.15.2024
                        "%B %d, %Y",     # January 15, 2024
                        "%b %d, %Y",     # Jan 15, 2024
                        "%Y-%m-%d",      # 2024-01-15 (ISO format from datetime attr)
                    ]

                    for fmt in date_formats:
                        try:
                            date = datetime.datetime.strptime(date_text_normalized, fmt).date()
                            break
                        except ValueError:
                            try:
                                # Try with original text if normalized doesn't work
                                date = datetime.datetime.strptime(date_text, fmt).date()
                                break
                            except ValueError:
                                continue

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': link.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    @classmethod
    def table_time(cls, urls=None, page=1):
        """
        Scrape press releases from websites with simple table tr structure and time element.

        This pattern is used by House sites that display press releases in a table
        with a time element for dates.

        Args:
            urls: List of URLs to scrape (default: None)
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain

        Example URLs:
            - https://barr.house.gov/media-center/press-releases (barr)
        """
        results = []
        if urls is None:
            urls = []

        for url in urls:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}{'&' if '?' in url else '?'}page={page}"

            doc = cls.open_html(source_url)
            if not doc:
                continue

            # Skip first row (header)
            rows = doc.select("table tr")[1:]

            for row in rows:
                link = row.select_one("td a") or row.select_one("a")
                if not link:
                    continue

                time_elem = row.select_one("time")
                date = None

                if time_elem:
                    # Try datetime attribute first
                    date_text = time_elem.get('datetime') or time_elem.text.strip()

                    date_formats = [
                        "%m/%d/%y",      # 01/15/24
                        "%m/%d/%Y",      # 01/15/2024
                        "%Y-%m-%d",      # 2024-01-15
                        "%B %d, %Y",     # January 15, 2024
                    ]

                    for fmt in date_formats:
                        try:
                            date = datetime.datetime.strptime(date_text, fmt).date()
                            break
                        except ValueError:
                            continue

                # Handle relative URL
                href = link.get('href')
                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://{domain}{href}"

                result = {
                    'source': url,
                    'url': full_url,
                    'title': link.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    @classmethod
    def element_post_media(cls, urls=None, page=1):
        """
        Scrape press releases from websites with .element class and post-media-list structure.

        This pattern is used by some Senate sites that use a custom element layout
        with post-media-list-title and post-media-list-date classes.

        Args:
            urls: List of URLs to scrape (default: None)
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain

        Example URLs:
            - https://www.wicker.senate.gov/media/press-releases (wicker)
        """
        results = []
        if urls is None:
            urls = []

        for url in urls:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}{'&' if '?' in url else '?'}page={page}"

            doc = cls.open_html(source_url)
            if not doc:
                continue

            elements = doc.select(".element")
            for row in elements:
                link = row.select_one('a')
                title_elem = row.select_one(".post-media-list-title") or row.select_one(".element-title")
                date_elem = row.select_one(".post-media-list-date") or row.select_one(".element-datetime")

                if not (link and title_elem and date_elem):
                    continue

                date = None
                date_text = date_elem.text.strip()

                date_formats = [
                    "%B %d, %Y",     # January 15, 2024
                    "%m/%d/%Y",      # 01/15/2024
                    "%m/%d/%y",      # 01/15/24
                    "%m.%d.%Y",      # 01.15.2024
                ]

                for fmt in date_formats:
                    try:
                        date = datetime.datetime.strptime(date_text, fmt).date()
                        break
                    except ValueError:
                        continue

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': title_elem.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results
