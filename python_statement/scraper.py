"""
Scraper class for scraping HTML pages containing press releases.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import datetime
import json
import time
import re
import os
import hashlib

from .utils import Utils
from .config import SCRAPER_CONFIG


class Scraper:
    """Class for scraping HTML pages."""

    # Configuration for scrapers that use generic methods
    # Maps scraper_method name -> {method: generic_method_name, url_base: base_url}
    SCRAPER_CONFIG = SCRAPER_CONFIG

    # Opt-in disk cache for HTTP responses (off by default)
    _cache_enabled = False
    _cache_dir = os.path.expanduser('~/.cache/python-statement')
    _cache_ttl = 3600  # seconds

    @classmethod
    def enable_cache(cls, ttl=3600, cache_dir=None):
        """Enable disk caching of HTTP responses.

        Args:
            ttl: Cache time-to-live in seconds (default: 1 hour)
            cache_dir: Custom cache directory (default: ~/.cache/python-statement)
        """
        cls._cache_enabled = True
        cls._cache_ttl = ttl
        if cache_dir:
            cls._cache_dir = cache_dir
        os.makedirs(cls._cache_dir, exist_ok=True)

    @classmethod
    def disable_cache(cls):
        """Disable disk caching (HTTP requests go to the network)."""
        cls._cache_enabled = False

    @classmethod
    def clear_cache(cls):
        """Delete all cached HTTP responses."""
        import shutil
        if os.path.exists(cls._cache_dir):
            shutil.rmtree(cls._cache_dir)

    @classmethod
    def run_scraper(cls, scraper_name, page=1, **kwargs):
        """
        Configuration-driven scraper dispatcher.
        
        For scrapers in SCRAPER_CONFIG, routes to the appropriate generic method with URL.
        For others, calls the method directly if it exists.
        
        Args:
            scraper_name: Name of the scraper to run (e.g., 'moran', 'boozman')
            page: Page number for pagination
            **kwargs: Additional arguments (e.g., urls for generic methods)
            
        Returns:
            List of scraped results or empty list if scraper not found
        """
        config = cls.SCRAPER_CONFIG.get(scraper_name)
        if not config:
            # Fall back to calling the method directly if it exists
            if hasattr(cls, scraper_name):
                method = getattr(cls, scraper_name)
                return method(page=page, **kwargs)
            return []
        
        method_name = config['method']
        url_base = config['url_base']

        # Route 'rss' to Feed.from_rss
        if method_name == 'rss':
            from .feed import Feed
            return Feed.from_rss(url_base)

        # Route 'generic' to the universal dispatcher
        if method_name == 'generic':
            return cls.generic_scraper(scraper_name, page)

        # Get the named generic method
        method = getattr(cls, method_name)

        # Inspect the method signature to determine how to call it
        import inspect
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        if params and params[0] == 'urls':
            return method([url_base], page)
        elif params and params[0] == 'domains':
            # Extract domain from url_base for domain-based methods
            domain = urlparse(url_base).netloc or url_base
            if 'page' in sig.parameters:
                return method([domain], page)
            else:
                return method([domain])
        else:
            # Methods with no urls/domains param (e.g., cornyn, fischer, clark)
            if 'page' in sig.parameters:
                return method(page=page)
            else:
                return method()

    @classmethod
    def generic_scraper(cls, scraper_name, page=1):
        """
        Universal config-driven scraper dispatcher.

        Reads CSS selectors and date formats from SCRAPER_CONFIG to extract
        press releases from any HTML page without a custom method.

        Config keys:
            method: Must be 'generic'
            url_base: Base URL for the press page
            container: CSS selector for each press release container
            title_sel: CSS selector for title element (relative to container)
            date_sel: CSS selector for date element (relative to container)
            date_fmt: List of strptime format strings to try
            pagination: URL pagination pattern with {page} placeholder
            link_sel: Optional separate CSS selector for link (if different from title_sel)
            link_attr: Optional attribute name for URL (default: 'href')
            date_attr: Optional attribute name for date (e.g., 'datetime')
            base_domain: Optional domain override for relative URLs
            max_results: Optional max number of results per page
            skip_first: Optional number of containers to skip (e.g., 1 to skip header row)
            date_from_next_sibling: If True, get date text from next sibling of date_sel element
            url_prefix: Optional path prefix for relative URLs (e.g., '/news/')
        """
        config = cls.SCRAPER_CONFIG.get(scraper_name)
        if not config or config['method'] != 'generic':
            return []

        url_base = config['url_base']
        container_sel = config['container']
        title_sel = config['title_sel']
        date_sel = config.get('date_sel')
        date_fmts = config.get('date_fmt', ['%B %d, %Y'])
        pagination = config.get('pagination', '?page={page}')
        link_sel = config.get('link_sel')
        link_attr = config.get('link_attr', 'href')
        date_attr = config.get('date_attr')
        base_domain = config.get('base_domain')
        max_results = config.get('max_results')
        skip_first = config.get('skip_first', 0)
        date_from_next_sibling = config.get('date_from_next_sibling', False)
        url_prefix = config.get('url_prefix', '')
        page_offset = config.get('page_offset', 0)
        date_regex = config.get('date_regex')

        # Build paginated URL
        if pagination and '{page}' in pagination:
            url = url_base + pagination.format(page=page + page_offset)
        elif pagination:
            url = url_base + pagination
        else:
            url = url_base

        parsed_url = urlparse(url_base)
        domain = base_domain or parsed_url.netloc

        doc = cls.open_html(url)
        if not doc:
            return []

        containers = doc.select(container_sel)
        if skip_first:
            containers = containers[skip_first:]
        if max_results:
            containers = containers[:max_results]

        results = []
        for container in containers:
            # Extract title and link
            title_elem = container.select_one(title_sel)
            if not title_elem:
                continue

            title = title_elem.text.strip()

            # Get link - from title element or separate link selector
            if link_sel:
                link_elem = container.select_one(link_sel)
            else:
                # If title_sel points to an <a>, use it; otherwise find first <a>
                link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
                if link_elem is None:
                    link_elem = container.select_one('a')

            if link_elem is None:
                # Check if the container itself is a link
                if container.name == 'a':
                    link_elem = container
                else:
                    continue

            href = link_elem.get(link_attr, '').strip()
            if not href:
                continue

            # Make URL absolute
            if not href.startswith('http'):
                if url_prefix and not href.startswith('/'):
                    href = f"https://{domain}{url_prefix}{href}"
                else:
                    href = urljoin(url, href)

            # Extract date
            date = None
            if date_sel:
                date_elem = container.select_one(date_sel)
                if date_elem:
                    date_text = None
                    if date_from_next_sibling:
                        # Get date from next sibling text node (e.g., after span.middot)
                        sibling = date_elem.next_sibling
                        if sibling:
                            date_text = str(sibling).strip()
                    elif date_attr:
                        # Try attribute first (e.g., <time datetime="2024-01-15">)
                        date_text = date_elem.get(date_attr)
                    if not date_text:
                        date_text = date_elem.text.strip()

                    if date_text:
                        date = Utils.parse_date(date_text, date_fmts)
            elif date_regex:
                # Extract date from container text using regex
                m = re.search(date_regex, container.get_text())
                if m:
                    date = Utils.parse_date(m.group(1), date_fmts)

            result = {
                'source': url_base,
                'url': href,
                'title': title,
                'date': date,
                'domain': domain
            }
            results.append(result)

        return results

    @classmethod
    def open_html(cls, url):
        """Open an HTML page and return a BeautifulSoup object.

        If caching is enabled via enable_cache(), checks for a cached
        response before making an HTTP request. Cached responses are
        stored as raw bytes in ~/.cache/python-statement/.
        """
        # Check cache first
        cache_path = None
        if cls._cache_enabled:
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            cache_path = os.path.join(cls._cache_dir, url_hash)
            if os.path.exists(cache_path):
                age = time.time() - os.path.getmtime(cache_path)
                if age < cls._cache_ttl:
                    try:
                        with open(cache_path, 'rb') as f:
                            content = f.read()
                        try:
                            return BeautifulSoup(content, 'lxml')
                        except Exception:
                            return BeautifulSoup(content, 'html.parser')
                    except OSError:
                        pass  # Cache read failed, fetch from network

        time.sleep(0.5)  # Rate limit: be polite to congressional servers
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Write to cache before parsing
            if cache_path is not None:
                try:
                    os.makedirs(cls._cache_dir, exist_ok=True)
                    with open(cache_path, 'wb') as f:
                        f.write(response.content)
                except OSError:
                    pass  # Cache write failed, not critical

            try:
                return BeautifulSoup(response.content, 'lxml')
            except Exception:
                return BeautifulSoup(response.content, 'html.parser')

        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            print(f"Error opening HTML page {url}: {e}")
            return None
    
    @staticmethod
    def current_year():
        """Return the current year."""
        return datetime.datetime.now().year
    
    @staticmethod
    def current_month():
        """Return the current month."""
        return datetime.datetime.now().month
    
    @classmethod
    def house_gop(cls, url):
        """Scrape House GOP press releases."""
        doc = cls.open_html(url)
        if not doc:
            return []
        
        uri = urlparse(url)
        try:
            date_param = dict(param.split('=') for param in uri.query.split('&')).get('Date')
            date = datetime.datetime.strptime(date_param, "%m/%d/%Y").date() if date_param else None
        except Exception:
            date = None
        
        member_news = doc.find('ul', {'id': 'membernews'})
        if not member_news:
            return []
            
        links = member_news.find_all('a')
        results = []
        
        for link in links:
            abs_link = Utils.absolute_link(url, link.get('href'))
            result = {
                'source': url,
                'url': abs_link,
                'title': link.text.strip(),
                'date': date,
                'domain': urlparse(link.get('href')).netloc
            }
            results.append(result)
        
        return Utils.remove_generic_urls(results)
    
    @classmethod
    def member_methods(cls):
        """Return a sorted list of all member scraper names."""
        return sorted(SCRAPER_CONFIG.keys())
    
    @classmethod
    def committee_methods(cls):
        """Return a list of committee scraper methods."""
        return [
            cls.house_gop, cls.senate_approps_majority, cls.senate_approps_minority,
            cls.senate_banking_majority, cls.senate_banking_minority
        ]
    
    @classmethod
    def member_scrapers(cls):
        """Scrape all member websites."""
        year = datetime.datetime.now().year
        results = []
        
        # Call all the member scrapers
        scraper_results = [
            cls.shaheen(), cls.timscott(), cls.angusking(), cls.document_query_new(), 
            cls.media_body(), cls.scanlon(), cls.bera(), cls.meeks(), cls.vanhollen(), 
            # ... (remaining scrapers)
        ]
        
        # Flatten the list and remove None values
        for result in scraper_results:
            if isinstance(result, list):
                results.extend(result)
            elif result:
                results.append(result)
        
        return Utils.remove_generic_urls(results)

    # Example implementation of a specific scraper method

    @classmethod
    def document_query_new(cls, domains=None, page=1):
        """Scrape press releases from multiple domains using document query."""
        results = []
        if domains is None:
            domains = [
                {"wassermanschultz.house.gov": 27},
                {'hern.house.gov': 27},
                {'fletcher.house.gov': 27},
                # ... other domains
            ]
        
        for domain_dict in domains:
            for domain, doc_type_id in domain_dict.items():
                source_url = f"https://{domain}/news/documentquery.aspx?DocumentTypeID={doc_type_id}&Page={page}"
                doc = cls.open_html(source_url)
                if not doc:
                    continue
                
                articles = doc.find_all("article")
                for row in articles:
                    link = row.select_one("h2 a")
                    time_elem = row.select_one('time')
                    
                    if not (link and time_elem):
                        continue
                        
                    date_attr = time_elem.get('datetime') or time_elem.text
                    date = Utils.parse_date(date_attr, ["%Y-%m-%d"])
                    if date is None:
                        date = Utils.parse_date(time_elem.text, ["%B %d, %Y"])
                    
                    result = {
                        'source': source_url,
                        'url': f"https://{domain}/news/{link.get('href')}",
                        'title': link.text.strip(),
                        'date': date,
                        'domain': domain
                    }
                    results.append(result)
        
        return results

    @classmethod
    def media_body(cls, urls=None, page=0):
        """
        Scrape press releases from websites with media-body class.
        
        If urls is None, automatically collects all URLs from SCRAPER_CONFIG 
        where method='media_body'.
        """
        results = []
        if urls is None:
            # Collect all URLs from SCRAPER_CONFIG where method='media_body'
            urls = [
                config['url_base'] 
                for config in cls.SCRAPER_CONFIG.values() 
                if config['method'] == 'media_body'
            ]
        
        for url in urls:
            print(url)
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}?page={page}"
            doc = cls.open_html(source_url)
            if not doc:
                continue
            
            media_bodies = doc.find_all("div", {"class": "media-body"})
            for row in media_bodies:
                link = row.find('a')
                date_elem = row.select_one('.row .col-auto')
                
                if not (link and date_elem):
                    continue
                    
                date = Utils.parse_date(date_elem.text.strip(), ["%m/%d/%y", "%B %d, %Y"])

                result = {
                    'source': url,
                    'url': f"https://{domain}{link.get('href')}",
                    'title': link.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    # More scraper methods would be implemented here following the same pattern



        


    
    @classmethod
    def marshall(cls, page=1, posts_per_page=20):
        """Scrape Senator Marshall's press releases."""
        results = []
        ajax_url = f"https://www.marshall.senate.gov/wp-admin/admin-ajax.php?action=jet_smart_filters&provider=jet-engine%2Fpress-list&defaults%5Bpost_status%5D%5B%5D=publish&defaults%5Bpost_type%5D%5B%5D=press_releases&defaults%5Bposts_per_page%5D=6&defaults%5Bpaged%5D=1&defaults%5Bignore_sticky_posts%5D=1&settings%5Blisitng_id%5D=67853&settings%5Bcolumns%5D=1&settings%5Bcolumns_tablet%5D=&settings%5Bcolumns_mobile%5D=&settings%5Bpost_status%5D%5B%5D=publish&settings%5Buse_random_posts_num%5D=&settings%5Bposts_num%5D=6&settings%5Bmax_posts_num%5D=9&settings%5Bnot_found_message%5D=No+data+was+found&settings%5Bis_masonry%5D=&settings%5Bequal_columns_height%5D=&settings%5Buse_load_more%5D=&settings%5Bload_more_id%5D=&settings%5Bload_more_type%5D=click&settings%5Bload_more_offset%5D%5Bunit%5D=px&settings%5Bload_more_offset%5D%5Bsize%5D=0&settings%5Bloader_text%5D=&settings%5Bloader_spinner%5D=&settings%5Buse_custom_post_types%5D=yes&settings%5Bcustom_post_types%5D%5B%5D=press_releases&settings%5Bhide_widget_if%5D=&settings%5Bcarousel_enabled%5D=&settings%5Bslides_to_scroll%5D=1&settings%5Barrows%5D=true&settings%5Barrow_icon%5D=fa+fa-angle-left&settings%5Bdots%5D=&settings%5Bautoplay%5D=true&settings%5Bautoplay_speed%5D=5000&settings%5Binfinite%5D=true&settings%5Bcenter_mode%5D=&settings%5Beffect%5D=slide&settings%5Bspeed%5D=500&settings%5Binject_alternative_items%5D=&settings%5Bscroll_slider_enabled%5D=&settings%5Bscroll_slider_on%5D%5B%5D=desktop&settings%5Bscroll_slider_on%5D%5B%5D=tablet&settings%5Bscroll_slider_on%5D%5B%5D=mobile&settings%5Bcustom_query%5D=&settings%5Bcustom_query_id%5D=&settings%5B_element_id%5D=press-list&settings%5Bjet_cct_query%5D=&settings%5Bjet_rest_query%5D=&props%5Bfound_posts%5D=1484&props%5Bmax_num_pages%5D=248&props%5Bpage%5D=1&paged={page}"
        
        try:
            response = requests.get(ajax_url)
            json_data = response.json()
            content_html = json_data.get('content', '')
            
            if not content_html:
                return []
                
            content_soup = BeautifulSoup(content_html, 'html.parser')
            widgets = content_soup.select(".elementor-widget-wrap")
            
            for row in widgets:
                link = row.select_one("h4 a")
                date_span = row.select_one("span.elementor-post-info__item--type-date")
                
                if not (link and date_span):
                    continue
                    
                date = Utils.parse_date(date_span.text.strip(), ["%B %d, %Y"])

                result = {
                    'source': "https://www.marshall.senate.gov/newsroom/press-releases",
                    'url': link.get('href'),
                    'title': link.text.strip(),
                    'date': date,
                    'domain': "www.marshall.senate.gov"
                }
                results.append(result)
                
        except Exception as e:
            print(f"Error processing AJAX request: {e}")
        
        return results
    
    
    @classmethod
    def jetlisting_h2(cls, urls=None, page=1):
        """Scrape press releases from websites with JetEngine listing grid."""
        results = []
        if urls is None:
            urls = [
                "https://www.lankford.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum=",
                "https://www.ricketts.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum="
            ]
        
        for url in urls:
            doc = cls.open_html(f"{url}{page}")
            if not doc:
                continue
                
            grid_items = doc.select(".jet-listing-grid__item")
            for row in grid_items:
                link = row.select_one("h2 a")
                date_span = row.select_one("span.elementor-post-info__item--type-date")
                
                if not (link and date_span):
                    continue
                    
                date = Utils.parse_date(date_span.text.strip(), ["%B %d, %Y"])

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': link.text.strip(),
                    'date': date,
                    'domain': urlparse(url).netloc
                }
                results.append(result)

        return results

    @classmethod
    def senate_drupal_newscontent(cls, urls=None, page=1):
        """Scrape press releases from Senate Drupal sites with newscontent divs."""
        results = []
        if urls is None:
            urls = [
                "https://ansari.house.gov/media/press-releases",
                "https://huffman.house.gov/media-center/press-releases",
                "https://castro.house.gov/media-center/press-releases",
                "https://mikelevin.house.gov/media/press-releases",
                # ... other URLs
            ]
        
        for url in urls:
            print(url)
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}?PageNum_rs={page}"
            
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            h2_elements = doc.select('#newscontent h2')
            for row in h2_elements:
                link = row.select_one('a')
                if not link:
                    continue
                    
                # Find the date element which is two previous siblings of h2
                prev = row.previous_sibling
                if prev:
                    prev = prev.previous_sibling
                
                date_text = prev.text if prev else None
                date = None
                if date_text:
                    date = Utils.parse_date(date_text, ["%m.%d.%y", "%B %d, %Y"])

                result = {
                    'source': url,
                    'url': f"https://{domain}{link.get('href')}",
                    'title': row.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    @classmethod
    def senate_approps_majority(cls, page=1):
        """Scrape Senate Appropriations Committee majority press releases."""
        results = []
        url = f"https://www.appropriations.senate.gov/news/majority?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        h2_elements = doc.select("#newscontent h2")
        for row in h2_elements:
            link = row.select_one('a')
            if not link:
                continue
                
            title = row.text.strip()
            release_url = f"https://www.appropriations.senate.gov{link.get('href').strip()}"
            
            # Get the date from previous sibling
            prev = row.previous_sibling
            if prev:
                prev = prev.previous_sibling
            
            raw_date = prev.text if prev else None
            date = None
            if raw_date:
                date = Utils.parse_date(raw_date, ["%m.%d.%y"])

            result = {
                'source': url,
                'url': release_url,
                'title': title,
                'date': date,
                'domain': 'www.appropriations.senate.gov',
                'party': "majority"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def senate_banking_majority(cls, page=1):
        """Scrape Senate Banking Committee majority press releases."""
        results = []
        url = f"https://www.banking.senate.gov/newsroom/majority-press-releases?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("#browser_table tr")
        for row in rows:
            if row.get('class') and 'divider' in row.get('class'):
                continue
                
            # Find the title and link
            title_cell = row.find_all('td')[2] if len(row.find_all('td')) > 2 else None
            if not title_cell:
                continue
                
            link = title_cell.select_one('a')
            if not link:
                continue
                
            title = title_cell.text.strip()
            release_url = link.get('href').strip()
            
            # Find the date
            date_cell = row.find_all('td')[0] if len(row.find_all('td')) > 0 else None
            date = None
            if date_cell:
                date = Utils.parse_date(date_cell.text.strip(), ["%m/%d/%y"])

            result = {
                'source': url,
                'url': release_url,
                'title': title,
                'date': date,
                'domain': 'www.banking.senate.gov',
                'party': "majority"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def recordlist(cls, urls=None, page=1):
        """Scrape press releases from websites with recordList table."""
        results = []
        if urls is None:
            urls = [
                "https://emmer.house.gov/press-releases",
                "https://fitzpatrick.house.gov/press-releases",
                # ... other URLs
            ]
        
        for url in urls:
            print(url)
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}?page={page}"
            
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            rows = doc.select("table.table.recordList tr")[1:]  # Skip header row
            for row in rows:
                # Skip if it's a header row
                if row.select_one('td') and row.select_one('td').text.strip() == 'Title':
                    continue
                
                # Find title cell and link
                title_cell = row.find_all('td')[2] if len(row.find_all('td')) > 2 else None
                if not title_cell:
                    continue
                    
                link = title_cell.select_one('a')
                if not link:
                    continue
                    
                # Find date cell
                date_cell = row.find_all('td')[0] if len(row.find_all('td')) > 0 else None
                date = None
                if date_cell:
                    date = Utils.parse_date(date_cell.text.strip(), ["%m/%d/%y", "%B %d, %Y"])
                
                result = {
                    'source': url,
                    'url': f"https://{domain}{link.get('href')}",
                    'title': title_cell.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)
        
        return results
    
    @classmethod
    def article_block(cls, urls=None, page=1):
        """Scrape press releases from websites with ArticleBlock class."""
        results = []
        if urls is None:
            urls = [
                "https://www.coons.senate.gov/news/press-releases",
                "https://www.booker.senate.gov/news/press",
                "https://www.cramer.senate.gov/news/press-releases"
            ]
        
        for url in urls:
            print(url)
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}?pagenum_rs={page}"
            
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            blocks = doc.select(".ArticleBlock")
            for row in blocks:
                link = row.select_one('a')
                if not link:
                    continue
                    
                title = row.select_one('h3').text.strip() if row.select_one('h3') else ''
                date_elem = row.select_one('.ArticleBlock__date')
                date = None
                if date_elem:
                    date = Utils.parse_date(date_elem.text.strip(), ["%B %d, %Y"])

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': title,
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    @classmethod
    def article_block_h2(cls, urls=None, page=1):
        """Scrape press releases from websites with ArticleBlock class and h2 titles."""
        results = []
        if urls is None:
            urls = []
        
        for url in urls:
            print(url)
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}?pagenum_rs={page}"
            
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            blocks = doc.select(".ArticleBlock")
            for row in blocks:
                link = row.select_one('a')
                if not link:
                    continue
                    
                title = row.select_one('h2').text.strip() if row.select_one('h2') else ''
                date_elem = row.select_one('.ArticleBlock__date')
                date = None
                if date_elem:
                    date = Utils.parse_date(date_elem.text.strip(), ["%B %d, %Y"])

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': title,
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    @classmethod
    def article_block_h2_date(cls, urls=None, page=1):
        """Scrape press releases from websites with ArticleBlock class, h2 titles and date in p tag."""
        results = []
        if urls is None:
            urls = [
                "https://www.blumenthal.senate.gov/newsroom/press",
                "https://www.collins.senate.gov/newsroom/press-releases",
                "https://www.hirono.senate.gov/news/press-releases",
                "https://www.ernst.senate.gov/news/press-releases"
            ]
        
        for url in urls:
            print(url)
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}?pagenum_rs={page}"
            
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            blocks = doc.select(".ArticleBlock")
            for row in blocks:
                link = row.select_one('a')
                if not link:
                    continue
                    
                title = row.select_one('h2').text.strip() if row.select_one('h2') else ''
                date_elem = row.select_one('p')
                date = None
                if date_elem:
                    date = Utils.parse_date(date_elem.text.strip(), ["%B %d, %Y"])
                
                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': title,
                    'date': date,
                    'domain': domain
                }
                results.append(result)
        
        return results
    
    @classmethod
    def article_span_published(cls, urls=None, page=1):
        """Scrape press releases from websites with published span for dates."""
        if urls is None:
            urls = [
                "https://www.bennet.senate.gov/news/page/",
                "https://www.hickenlooper.senate.gov/press/page/"
            ]
        
        results = []
        for url in urls:
            print(url)
            doc = cls.open_html(f"{url}{page}")
            if not doc:
                continue
                
            articles = doc.select("article")
            for row in articles:
                link = row.select_one("h3 a")
                date_span = row.select_one("span.published")
                
                if not (link and date_span):
                    continue
                    
                date = Utils.parse_date(date_span.text.strip(), ["%B %d, %Y"])

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': link.text.strip(),
                    'date': date,
                    'domain': urlparse(url).netloc
                }
                results.append(result)

        return results

    @classmethod
    def article_newsblocker(cls, domains=None, page=1):
        """Scrape press releases from websites that use documentquery but return article elements."""
        results = []
        if domains is None:
            domains = [
                "balderson.house.gov",
                "case.house.gov",
                # ... other domains
            ]
        
        for domain in domains:
            print(domain)
            url = f"https://{domain}/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
            doc = cls.open_html(url)
            if not doc:
                continue
                
            articles = doc.select("article")
            for row in articles:
                link = row.select_one('a')
                time_elem = row.select_one("time")
                
                if not (link and time_elem):
                    continue
                    
                date_attr = time_elem.get('datetime')
                if date_attr:
                    date = Utils.parse_date(date_attr, ["%Y-%m-%d"])
                else:
                    date = Utils.parse_date(time_elem.text.strip(), ["%B %d, %Y"])
                
                result = {
                    'source': url,
                    'url': f"https://{domain}/news/{link.get('href')}",
                    'title': link.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)
        
        return results

    @classmethod
    def senate_drupal(cls, urls=None, page=1):
        """Scrape Senate Drupal sites."""
        if urls is None:
            urls = [
                "https://www.hoeven.senate.gov/news/news-releases",
                "https://www.murkowski.senate.gov/press/press-releases",
                "https://www.republicanleader.senate.gov/newsroom/press-releases",
                "https://www.sullivan.senate.gov/newsroom/press-releases"
            ]
        
        results = []
        for url in urls:
            print(url)
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}?PageNum_rs={page}"
            
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            h2_elements = doc.select("#newscontent h2")
            for row in h2_elements:
                link = row.select_one('a')
                if not link:
                    continue
                    
                title = row.text.strip()
                release_url = f"{parsed_url.scheme}://{domain}{link.get('href')}"
                
                # Get the date from previous sibling
                prev = row.previous_sibling
                if prev:
                    prev = prev.previous_sibling
                
                raw_date = prev.text if prev else None
                date = None
                
                if domain == 'www.tomudall.senate.gov' or domain == "www.vanhollen.senate.gov" or domain == "www.warren.senate.gov":
                    if raw_date:
                        date = Utils.parse_date(raw_date, ["%B %d, %Y"])
                elif url == 'https://www.republicanleader.senate.gov/newsroom/press-releases':
                    domain = 'mcconnell.senate.gov'
                    if raw_date:
                        date = Utils.parse_date(raw_date, ["%m/%d/%y"])
                    release_url = release_url.replace('mcconnell.senate.gov', 'www.republicanleader.senate.gov')
                else:
                    if raw_date:
                        date = Utils.parse_date(raw_date, ["%m.%d.%y"])
                
                result = {
                    'source': source_url,
                    'url': release_url,
                    'title': title,
                    'date': date,
                    'domain': domain
                }
                results.append(result)
        
        return results

    @classmethod
    def elementor_post_date(cls, urls=None, page=1):
        """Scrape sites that use Elementor with post-date class."""
        if urls is None:
            urls = [
                "https://www.sanders.senate.gov/media/press-releases/",
                "https://www.merkley.senate.gov/news/press-releases/"
            ]
        
        results = []
        for url in urls:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            source_url = f"{url}{page}/"
            
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            post_texts = doc.select('.elementor-post__text')
            for row in post_texts:
                link = row.select_one('a')
                h2 = row.select_one('h2')
                date_elem = row.select_one('.elementor-post-date')
                
                if not (link and h2 and date_elem):
                    continue
                    
                date = Utils.parse_date(date_elem.text.strip(), ["%B %d, %Y"])

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': h2.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)
        
        return results

    @classmethod
    def react(cls, domains=None):
        """Scrape sites built with React."""
        results = []
        if domains is None:
            domains = [
                "nikemawilliams.house.gov",
                "kiley.house.gov",
                "nehls.house.gov",
                "yakym.house.gov",
                "ritchietorres.house.gov",
                "cloud.house.gov",
                "owens.house.gov",
                "budzinski.house.gov",
                "gluesenkampperez.house.gov",
                "landsman.house.gov",
                "moskowitz.house.gov",
                "gottheimer.house.gov",
                "kiggans.house.gov",
                "luna.house.gov",
                "maxmiller.house.gov",
            ]
        
        for domain in domains:
            url = f"https://{domain}/press"
            doc = cls.open_html(url)
            if not doc:
                continue
                
            # Find the Next.js data script
            next_data_script = doc.select_one('[id="__NEXT_DATA__"]')
            if not next_data_script:
                continue
                
            try:
                json_data = json.loads(next_data_script.text)
                posts = json_data['props']['pageProps']['dehydratedState']['queries'][11]['state']['data']['posts']['edges']
                
                for post in posts:
                    node = post.get('node', {})
                    date_str = node.get('date')
                    date = None
                    if date_str:
                        try:
                            date = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                        except ValueError:
                            pass
                    
                    result = {
                        'source': url,
                        'url': node.get('link', ''),
                        'title': node.get('title', ''),
                        'date': date,
                        'domain': domain
                    }
                    results.append(result)
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"Error parsing JSON from {domain}: {e}")
        
        return results
    
    # Generic scraper methods that can be reused across multiple members
    
    @classmethod
    def table_recordlist_date(cls, urls=None, page=1):
        """
        Scrape press releases from websites with table tbody tr and td.recordListDate.

        This pattern is used by Senate sites that display press releases in a table
        with a specific recordListDate class for the date column.

        Args:
            urls: List of URLs to scrape (default: None, auto-collected from SCRAPER_CONFIG)
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
            # Collect all URLs from SCRAPER_CONFIG where method='table_recordlist_date'
            urls = [
                config['url_base']
                for config in cls.SCRAPER_CONFIG.values()
                if config['method'] == 'table_recordlist_date'
            ]

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
                date_text = date_cell.text.strip()
                date = Utils.parse_date(date_text, [
                    "%m/%d/%y",      # 01/15/24
                    "%m/%d/%Y",      # 01/15/2024
                    "%m.%d.%y",      # 01.15.24
                    "%m.%d.%Y",      # 01.15.2024
                    "%B %d, %Y",     # January 15, 2024
                ])

                # Handle relative URL
                href = link.get('href')
                full_url = urljoin(url, href)

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
            urls: List of URLs to scrape (default: None, auto-collected from SCRAPER_CONFIG)
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
            # Collect all URLs from SCRAPER_CONFIG where method='jet_listing_elementor'
            urls = [
                config['url_base']
                for config in cls.SCRAPER_CONFIG.values()
                if config['method'] == 'jet_listing_elementor'
            ]

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
            elif url.endswith('/page/'):
                # URL structure like /press-releases/page/
                source_url = f"{url}{page}/"
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
                # Some sites split date across multiple spans (e.g., "Jan.", "22", "2026")
                date = None
                date_spans = row.select("span.elementor-icon-list-text")
                if date_spans:
                    # Filter out non-date spans like "Continue Reading"
                    date_parts = [
                        s.get_text(strip=True) for s in date_spans
                        if s.get_text(strip=True) and not s.get_text(strip=True).isalpha()
                        or len(s.get_text(strip=True)) <= 4  # month abbreviations
                    ]
                    # Try joining all parts as a single date string
                    date_text = " ".join(date_parts)
                    if date_text:
                        date = Utils.parse_date(date_text, [
                            "%b. %d %Y",     # Jan. 22 2026
                            "%B %d, %Y",     # January 15, 2024
                            "%B %d %Y",      # January 15 2024
                            "%m/%d/%Y",      # 01/15/2024
                            "%m/%d/%y",      # 01/15/24
                        ])

                if date is None:
                    date_elem = row.select_one(".elementor-post-date")
                    if date_elem:
                        date_text = date_elem.text.strip()
                        date = Utils.parse_date(date_text, [
                            "%B %d, %Y",
                            "%m/%d/%Y",
                            "%m/%d/%y",
                        ])

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
            urls: List of URLs to scrape (default: None, auto-collected from SCRAPER_CONFIG)
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
            # Collect all URLs from SCRAPER_CONFIG where method='article_block_h2_p_date'
            urls = [
                config['url_base']
                for config in cls.SCRAPER_CONFIG.values()
                if config['method'] == 'article_block_h2_p_date'
            ]

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

                    # Utils.parse_date handles dot→slash normalization internally
                    date = Utils.parse_date(date_text, [
                        "%m/%d/%y",      # 01/15/24 or 01.15.24
                        "%m/%d/%Y",      # 01/15/2024 or 01.15.2024
                        "%B %d, %Y",     # January 15, 2024
                        "%b %d, %Y",     # Jan 15, 2024
                        "%Y-%m-%d",      # 2024-01-15 (ISO format from datetime attr)
                    ])

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

                    date = Utils.parse_date(date_text, [
                        "%m/%d/%y",      # 01/15/24
                        "%m/%d/%Y",      # 01/15/2024
                        "%Y-%m-%d",      # 2024-01-15
                        "%B %d, %Y",     # January 15, 2024
                    ])

                # Handle relative URL
                href = link.get('href')
                full_url = urljoin(url, href)

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
            urls: List of URLs to scrape (default: None, auto-collected from SCRAPER_CONFIG)
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain

        Example URLs:
            - https://www.wicker.senate.gov/media/press-releases (wicker)
            - https://www.tillis.senate.gov/press-releases (tillis)
        """
        results = []
        if urls is None:
            # Collect all URLs from SCRAPER_CONFIG where method='element_post_media'
            urls = [
                config['url_base']
                for config in cls.SCRAPER_CONFIG.values()
                if config['method'] == 'element_post_media'
            ]

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

                date_text = date_elem.text.strip()
                date = Utils.parse_date(date_text, [
                    "%B %d, %Y",     # January 15, 2024
                    "%m/%d/%Y",      # 01/15/2024
                    "%m/%d/%y",      # 01/15/24
                    "%m.%d.%Y",      # 01.15.2024
                ])

                result = {
                    'source': url,
                    'url': link.get('href'),
                    'title': title_elem.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results
    
    # Individual member scraper methods
    
    @classmethod
    def tokuda(cls, page=1):
        """Scrape Congresswoman Tokuda's press releases."""
        results = []
        url = f"https://tokuda.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        press_div = doc.select_one("#press")
        if not press_div:
            return []
            
        rows = press_div.select('h2')
        for row in rows:
            link = row.select_one('a')
            if not link:
                continue
                
            # Get date from previous sibling
            prev = row.previous_sibling
            if prev:
                prev = prev.previous_sibling
            
            date = None
            if prev:
                date = Utils.parse_date(prev.text.strip(), ["%B %d, %Y"])

            result = {
                'source': url,
                'url': f"https://tokuda.house.gov{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': "tokuda.house.gov"
            }
            results.append(result)
        
        return results
    
    
    
    

    
    
    
    
    @classmethod
    def cornyn(cls, page=1, posts_per_page=15):
        """Scrape Senator Cornyn's press releases."""
        results = []
        ajax_url = f"https://www.cornyn.senate.gov/wp-admin/admin-ajax.php?action=jet_smart_filters&provider=jet-engine%2Fdefault&defaults[post_status]=publish&defaults[found_posts]=1261&defaults[maximum_pages]=85&defaults[post_type]=news&defaults[orderby]=&defaults[order]=DESC&defaults[paged]=0&defaults[posts_per_page]={posts_per_page}&settings[lisitng_id]=16387&settings[columns]=1&settings[columns_tablet]=&settings[columns_mobile]=&settings[column_min_width]=240&settings[column_min_width_tablet]=&settings[column_min_width_mobile]=&settings[inline_columns_css]=false&settings[post_status][]=publish&settings[use_random_posts_num]=&settings[posts_num]=20&settings[max_posts_num]=9&settings[not_found_message]=No+data+was+found&settings[is_masonry]=&settings[equal_columns_height]=&settings[use_load_more]=&settings[load_more_id]=&settings[load_more_type]=click&settings[load_more_offset][unit]=px&settings[load_more_offset][size]=0&settings[loader_text]=&settings[loader_spinner]=&settings[use_custom_post_types]=yes&settings[custom_post_types][]=news&settings[hide_widget_if]=&settings[carousel_enabled]=&settings[slides_to_scroll]=1&settings[arrows]=true&settings[arrow_icon]=fa+fa-angle-left&settings[dots]=&settings[autoplay]=true&settings[pause_on_hover]=true&settings[autoplay_speed]=5000&settings[infinite]=true&settings[center_mode]=&settings[effect]=slide&settings[speed]=500&settings[inject_alternative_items]=&settings[scroll_slider_enabled]=&settings[scroll_slider_on][]=desktop&settings[scroll_slider_on][]=tablet&settings[scroll_slider_on][]=mobile&settings[custom_query]=&settings[custom_query_id]=&settings[_element_id]=&props[found_posts]=1261&props[max_num_pages]=85&props[page]=0&paged={page}"
        
        try:
            response = requests.get(ajax_url)
            json_data = response.json()
            content_html = json_data.get('content', '')
            
            if not content_html:
                return []
                
            content_soup = BeautifulSoup(content_html, 'html.parser')
            widgets = content_soup.select(".elementor-widget-wrap")
            
            for row in widgets:
                link = row.select_one("h2 a")
                date_span = row.select_one("span.elementor-heading-title")
                
                if not (link and date_span):
                    continue
                    
                date = Utils.parse_date(date_span.text.strip(), ["%B %d, %Y"])

                result = {
                    'source': "https://www.cornyn.senate.gov/news/",
                    'url': link.get('href'),
                    'title': link.text.strip(),
                    'date': date,
                    'domain': "www.cornyn.senate.gov"
                }
                results.append(result)
                
        except Exception as e:
            print(f"Error processing AJAX request: {e}")
        
        return results
    
    @classmethod
    def fischer(cls, page=1):
        """Scrape Senator Fischer's press releases."""
        results = []
        url = f"https://www.fischer.senate.gov/public/index.cfm/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[2:]  # Skip header rows
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 4 or cells[2].text.strip()[:4] == "Date":
                continue
                
            link = cells[2].select_one('a')
            if not link:
                continue
                
            date = Utils.parse_date(cells[0].text.strip(), ["%m/%d/%y"])

            result = {
                'source': url,
                'url': link.get('href'),
                'title': cells[2].text.strip(),
                'date': date,
                'domain': "www.fischer.senate.gov"
            }
            results.append(result)
        
        return results
    
    
    @classmethod
    def kennedy(cls, page=1):
        """Scrape Senator Kennedy's press releases."""
        results = []
        url = f"https://www.kennedy.senate.gov/public/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table.table.recordList tr")[1:]
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 4 or cells[2].text.strip() == 'Title':
                continue
                
            link = cells[2].select_one('a')
            if not link:
                continue
                
            date = Utils.parse_date(cells[0].text.strip(), ["%m/%d/%y"])

            result = {
                'source': url,
                'url': f"https://www.kennedy.senate.gov{link.get('href')}",
                'title': cells[2].text.strip(),
                'date': date,
                'domain': "www.kennedy.senate.gov"
            }
            results.append(result)
        
        return results

    
    @classmethod
    def clark(cls, page=1):
        """Scrape Congresswoman Katherine Clark's press releases."""
        results = []
        domain = 'katherineclark.house.gov'
        url = f"https://katherineclark.house.gov/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select('tr')[1:]
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 4 or cells[0].text.strip() == 'Date':
                continue
                
            link = cells[2].select_one('a')
            if not link:
                continue
                
            date = Utils.parse_date(cells[0].text.strip(), ["%m/%d/%y"])
            
            result = {
                'source': url,
                'url': f"https://katherineclark.house.gov{link.get('href')}",
                'title': cells[2].text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    
    @classmethod
    def joyce(cls):
        """Scrape Congressman Joyce's press releases."""
        results = []
        domain = 'joyce.house.gov'
        url = "https://joyce.house.gov/press"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        # Find the Next.js data script
        next_data_script = doc.select_one('[id="__NEXT_DATA__"]')
        if not next_data_script:
            return []
            
        try:
            json_data = json.loads(next_data_script.text)
            posts = json_data['props']['pageProps']['dehydratedState']['queries'][11]['state']['data']['posts']['edges']
            
            for post in posts:
                node = post.get('node', {})
                date_str = node.get('date')
                date = None
                if date_str:
                    try:
                        date = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                    except ValueError:
                        pass
                
                result = {
                    'source': url,
                    'url': node.get('link', ''),
                    'title': node.get('title', ''),
                    'date': date,
                    'domain': domain
                }
                results.append(result)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error parsing JSON from {domain}: {e}")
        
        return results
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    


    
    
    
    
    
    
    
    
    
    
    
    
    @classmethod
    def senate_approps_minority(cls, page=1):
        """Scrape Senate Appropriations Committee minority press releases."""
        results = []
        url = f"https://www.appropriations.senate.gov/news/minority?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        h2_elements = doc.select("#newscontent h2")
        for row in h2_elements:
            link = row.find('a')
            if not link:
                continue
            
            date = None
            date_text_elem = row.find_next_sibling('p')
            if date_text_elem:
                date = Utils.parse_date(date_text_elem.text.strip(), ["%m.%d.%Y"])
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': 'www.appropriations.senate.gov'
            }
            results.append(result)
        
        return results
    
    @classmethod
    def senate_banking_minority(cls, page=1):
        """Scrape Senate Banking Committee minority press releases."""
        results = []
        url = f"https://www.banking.senate.gov/newsroom/minority-press-releases?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("#browser_table tr")
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
            
            date_elem = row.find('td', text=lambda x: x and '.' in str(x))
            date = None
            if date_elem:
                date = Utils.parse_date(date_elem.text.strip(), ["%m.%d.%Y"])
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': 'www.banking.senate.gov'
            }
            results.append(result)
        
        return results
    
    @classmethod
    def house_title_header(cls, urls=None, page=1):
        """Scrape House press releases with title-header class."""
        if urls is None:
            urls = []
        
        results = []
        for url in urls:
            source_url = f"{url}?page={page}"
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            domain = urlparse(url).netloc
            rows = doc.select("tr")[1:]
            for row in rows:
                link = row.select_one("td a")
                if not link:
                    continue
                date_elem = row.select_one("time")
                date = None
                if date_elem:
                    date = Utils.parse_date(date_elem.text.strip(), ["%m/%d/%y"])

                result = {
                    'source': source_url,
                    'url': f"https://{domain}{link.get('href')}",
                    'title': link.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results

    @classmethod
    def media_digest(cls, urls=None, page=1):
        """Scrape House press releases with media digest pattern."""
        if urls is None:
            urls = []
        
        results = []
        for url in urls:
            source_url = f"{url}?page={page}"
            doc = cls.open_html(source_url)
            if not doc:
                continue
                
            domain = urlparse(url).netloc
            rows = doc.select(".views-row")
            for row in rows:
                link = row.select_one("a")
                if not link:
                    continue
                date_elem = row.select_one("time")
                date = None
                if date_elem:
                    date_attr = date_elem.get('datetime')
                    if date_attr:
                        try:
                            date = datetime.datetime.fromisoformat(date_attr.replace('Z', '+00:00')).date()
                        except ValueError:
                            pass
                
                result = {
                    'source': source_url,
                    'url': f"https://{domain}{link.get('href')}",
                    'title': link.text.strip(),
                    'date': date,
                    'domain': domain
                }
                results.append(result)

        return results


# Auto-generate wrapper methods for all SCRAPER_CONFIG entries
# that don't already have a method on the Scraper class.
# This means adding a new scraper only requires a config.py edit.
def _make_scraper_method(name):
    """Create a classmethod wrapper that calls run_scraper."""
    @classmethod
    def method(cls, page=1):
        return cls.run_scraper(name, page)
    method.__func__.__doc__ = f"Scrape {name} press releases."
    method.__func__.__name__ = name
    return method


for _name in SCRAPER_CONFIG:
    if not hasattr(Scraper, _name):
        setattr(Scraper, _name, _make_scraper_method(_name))

