"""
Statement module for parsing RSS feeds and HTML pages containing press releases
from members of Congress. This is a Python 3 port of the Ruby gem 'statement'.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import datetime
import json
import time
import re
import os
from dateutil import parser as date_parser  # More robust date parsing


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


class Scraper:
    """Class for scraping HTML pages."""
    
    @staticmethod
    def open_html(url):
        """Open an HTML page and return a BeautifulSoup object."""
        try:
            # Set a user agent to avoid being blocked by some websites
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Add timeout to prevent hanging on slow websites
            response = requests.get(url, headers=headers, timeout=30)
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            # Try to use lxml parser first (faster), fall back to html.parser
            try:
                return BeautifulSoup(response.content, 'lxml')
            except:
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
        """Return a list of member scraper methods."""
        return [
            cls.crapo, cls.trentkelly, cls.heinrich, cls.document_query_new, cls.barr, cls.media_body, 
            cls.steube, cls.bera, cls.meeks, cls.sykes, cls.barragan, cls.castor, cls.marshall, cls.hawley, 
            cls.jetlisting_h2, cls.barrasso, cls.timscott, cls.senate_drupal_newscontent, 
            # ... (remaining methods)
        ]
    
    @classmethod
    def committee_methods(cls):
        """Return a list of committee scraper methods."""
        return [
            cls.senate_approps_majority, cls.senate_approps_minority, cls.senate_banking_majority,
            # ... (remaining methods)
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
    def crapo(cls, page=1):
        """Scrape Senator Crapo's press releases."""
        results = []
        url = f"https://www.crapo.senate.gov/media/newsreleases/?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        article_blocks = doc.find_all('div', {'class': 'ArticleBlock'})
        for block in article_blocks:
            link = block.find('a')
            if not link:
                continue
                
            href = link.get('href')
            title = link.text.strip()
            date_text = block.find('p').text if block.find('p') else None
            date = None
            if date_text:
                try:
                    date = datetime.datetime.strptime(date_text, "%m.%d.%y").date()
                except ValueError:
                    try:
                        date = datetime.datetime.strptime(date_text, "%B %d, %Y").date()
                    except ValueError:
                        date = None
            
            result = {
                'source': url,
                'url': href,
                'title': title,
                'date': date,
                'domain': 'www.crapo.senate.gov'
            }
            results.append(result)
        
        return results

    @classmethod
    def shaheen(cls, page=1):
        """Scrape Senator Shaheen's press releases."""
        results = []
        domain = "www.shaheen.senate.gov"
        url = f"https://www.shaheen.senate.gov/news/press?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        article_blocks = doc.find_all("div", {"class": "ArticleBlock"})
        for row in article_blocks:
            link = row.find('a')
            title_elem = row.find(class_="ArticleTitle")
            time_elem = row.find("time")
            
            if not (link and title_elem and time_elem):
                continue
                
            date_text = time_elem.text.replace(".", "/")
            date = None
            try:
                date = datetime.datetime.strptime(date_text, "%m/%d/%y").date()
            except ValueError:
                try:
                    date = datetime.datetime.strptime(date_text, "%B %d, %Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': title_elem.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results

    @classmethod
    def timscott(cls, page=1):
        """Scrape Senator Tim Scott's press releases."""
        results = []
        domain = "www.scott.senate.gov"
        url = f"https://www.scott.senate.gov/media-center/press-releases/jsf/jet-engine:press-list/pagenum/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        grid_items = doc.select('.jet-listing-grid .elementor-widget-wrap')
        for row in grid_items:
            link = row.select_one("h3 a")
            if not link:
                continue
                
            date_elem = row.select_one("li span.elementor-icon-list-text")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
            
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
    def angusking(cls, page=1):
        """Scrape Senator Angus King's press releases."""
        results = []
        url = f"https://www.king.senate.gov/newsroom/press-releases/table?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select('table tr')[1:]  # Skip header row
        for row in rows:
            links = row.select('a')
            if not links:
                continue
                
            link = links[0]
            date_cell = row.find_all('td')[0] if row.find_all('td') else None
            date = None
            if date_cell:
                try:
                    date = datetime.datetime.strptime(date_cell.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://www.king.senate.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': "www.king.senate.gov"
            }
            results.append(result)
        
        return results

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
                        
                    date = None
                    try:
                        date_attr = time_elem.get('datetime') or time_elem.text
                        date = datetime.datetime.strptime(date_attr, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        try:
                            date = datetime.datetime.strptime(time_elem.text, "%B %d, %Y").date()
                        except ValueError:
                            pass
                    
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
        """Scrape press releases from websites with media-body class."""
        results = []
        if urls is None:
            urls = [
                "https://issa.house.gov/media/press-releases",
                "https://tenney.house.gov/media/press-releases",
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
            
            media_bodies = doc.find_all("div", {"class": "media-body"})
            for row in media_bodies:
                link = row.find('a')
                date_elem = row.select_one('.row .col-auto')
                
                if not (link and date_elem):
                    continue
                    
                date = None
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    try:
                        date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
                    except ValueError:
                        pass
                
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
    def steube(cls, page=1):
        """Scrape Congressman Steube's press releases."""
        results = []
        domain = "steube.house.gov"
        url = f"https://steube.house.gov/category/press-releases/page/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article.item")
        for row in articles:
            link = row.select_one('a')
            h3 = row.select_one('h3')
            date_span = row.select_one("span.date")
            
            if not (link and h3 and date_span):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': h3.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results

    @classmethod
    def bera(cls, page=1):
        """Scrape Congressman Bera's press releases."""
        results = []
        domain = 'bera.house.gov'
        url = f"https://bera.house.gov/news/documentquery.aspx?DocumentTypeID=2402&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.find_all("article")
        for row in articles:
            link = row.select_one('a')
            time_elem = row.select_one("time")
            
            if not (link and time_elem):
                continue
                
            date = None
            try:
                date_attr = time_elem.get('datetime')
                date = datetime.datetime.strptime(date_attr, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
            
            result = {
                'source': url,
                'url': f"https://bera.house.gov/news/{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results

    @classmethod
    def meeks(cls, page=0):
        """Scrape Congressman Meeks's press releases."""
        results = []
        domain = 'meeks.house.gov'
        url = f"https://meeks.house.gov/media/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select(".views-row")[:10]  # First 10 items
        for row in rows:
            link = row.select_one("a.h4")
            date_elem = row.select_one(".evo-card-date")
            
            if not (link and date_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': f"https://meeks.house.gov{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
        
    @classmethod
    def sykes(cls, page=1):
        """Scrape Congresswoman Sykes's press releases."""
        results = []
        url = f"https://sykes.house.gov/media/press-releases?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table#browser_table tbody tr")
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
                
            time_elem = row.select_one("time")
            date = None
            if time_elem:
                try:
                    date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': f"https://sykes.house.gov{link.get('href').strip()}",
                'title': link.text.strip(),
                'date': date,
                'domain': "sykes.house.gov"
            }
            results.append(result)
        
        return results

    @classmethod
    def barragan(cls, page=1):
        """Scrape Congresswoman Barragan's press releases."""
        results = []
        domain = "barragan.house.gov"
        url = f"https://barragan.house.gov/category/news-releases/page/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        posts = doc.select(".post")
        for row in posts:
            link = row.select_one('a')
            if not link:
                continue
                
            h2 = row.select_one('h2')
            p = row.select_one("p")
            
            if not (h2 and p):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(p.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
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
    def castor(cls, page=1):
        """Scrape Congresswoman Castor's press releases."""
        results = []
        domain = 'castor.house.gov'
        url = f"https://castor.house.gov/news/documentquery.aspx?DocumentTypeID=821&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.find_all("article")
        for row in articles:
            link = row.select_one('a')
            time_elem = row.select_one("time")
            
            if not (link and time_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': f"https://castor.house.gov/news/{link.get('href').strip()}",
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
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
                    
                date = None
                try:
                    date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
                
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
    def hawley(cls, page=1):
        """Scrape Senator Hawley's press releases."""
        results = []
        url = f"https://www.hawley.senate.gov/press-releases/page/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        posts = doc.select('article .post')
        for row in posts:
            link = row.select_one('h2 a')
            date_span = row.select_one('span.published')
            
            if not (link and date_span):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': 'www.hawley.senate.gov'
            }
            results.append(result)
        
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
                    
                date = None
                try:
                    date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
                
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
    def barrasso(cls, page=1):
        """Scrape Senator Barrasso's press releases."""
        results = []
        url = f"https://www.barrasso.senate.gov/public/index.cfm/news-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table tbody tr")
        for row in rows:
            link = row.select_one('a')
            date_cell = row.select_one('td.recordListDate')
            
            if not (link and date_cell):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_cell.text.strip(), "%m/%d/%y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': "www.barrasso.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def senate_drupal_newscontent(cls, urls=None, page=1):
        """Scrape press releases from Senate Drupal sites with newscontent divs."""
        results = []
        if urls is None:
            urls = [
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
                    try:
                        date = datetime.datetime.strptime(date_text, "%m.%d.%y").date()
                    except ValueError:
                        try:
                            date = datetime.datetime.strptime(date_text, "%B %d, %Y").date()
                        except ValueError:
                            pass
                
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
                try:
                    date = datetime.datetime.strptime(raw_date, "%m.%d.%y").date()
                except ValueError:
                    pass
            
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
                try:
                    date = datetime.datetime.strptime(date_cell.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
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
                    try:
                        date = datetime.datetime.strptime(date_cell.text.strip(), "%m/%d/%y").date()
                    except ValueError:
                        try:
                            date = datetime.datetime.strptime(date_cell.text.strip(), "%B %d, %Y").date()
                        except ValueError:
                            pass
                
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
                    try:
                        date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
                    except ValueError:
                        pass
                
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
                    try:
                        date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
                    except ValueError:
                        pass
                
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
                    try:
                        date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
                    except ValueError:
                        pass
                
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
                    
                date = None
                try:
                    date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
                
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
                    
                date = None
                try:
                    date_attr = time_elem.get('datetime')
                    if date_attr:
                        date = datetime.datetime.strptime(date_attr, "%Y-%m-%d").date()
                    else:
                        date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
                
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
                        try:
                            date = datetime.datetime.strptime(raw_date, "%B %d, %Y").date()
                        except ValueError:
                            pass
                elif url == 'https://www.republicanleader.senate.gov/newsroom/press-releases':
                    domain = 'mcconnell.senate.gov'
                    if raw_date:
                        try:
                            date = datetime.datetime.strptime(raw_date.replace('.', '/'), "%m/%d/%y").date()
                        except ValueError:
                            pass
                    release_url = release_url.replace('mcconnell.senate.gov', 'www.republicanleader.senate.gov')
                else:
                    if raw_date:
                        try:
                            date = datetime.datetime.strptime(raw_date, "%m.%d.%y").date()
                        except ValueError:
                            pass
                
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
                    
                date = None
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
                
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
                # ... other domains
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