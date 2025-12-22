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
            cls.aguilar, cls.angusking, cls.article_block, cls.article_block_h2, cls.article_block_h2_date,
            cls.article_newsblocker, cls.article_span_published, cls.bacon, cls.baldwin, cls.barr,
            cls.barragan, cls.barrasso, cls.bennet, cls.bera, cls.bergman, cls.blackburn, cls.boozman,
            cls.britt, cls.brownley, cls.budd, cls.cantwell, cls.capito, cls.cardin, cls.carey,
            cls.carper, cls.casey, cls.cassidy, cls.castor, cls.clark, cls.clarke, cls.clyburn,
            cls.connolly, cls.coons, cls.cornyn, cls.cortezmasto, cls.cotton, cls.crapo, cls.crawford,
            cls.cruz, cls.daines, cls.document_query_new, cls.duckworth, cls.durbin, cls.elementor_post_date,
            cls.ellzey, cls.emmer, cls.ernst, cls.fetterman, cls.fischer, cls.foxx, cls.garypeters,
            cls.gillibrand, cls.gimenez, cls.gosar, cls.graham, cls.grassley, cls.griffith, cls.grijalva,
            cls.hagerty, cls.hassan, cls.hawley, cls.heinrich, cls.hirono, cls.hoeven, cls.houlahan,
            cls.house_title_header, cls.huizenga, cls.hydesmith, cls.jackreed, cls.jasonsmith, cls.jayapal,
            cls.jeffries, cls.jetlisting_h2, cls.joyce, cls.kaine, cls.kennedy, cls.lankford, cls.larsen,
            cls.lofgren, cls.lucas, cls.lujan, cls.lummis, cls.manchin, cls.markey, cls.markkelly,
            cls.marshall, cls.mast, cls.mcgovern, cls.media_body, cls.media_digest, cls.meeks,
            cls.menendez, cls.merkley, cls.mikelee, cls.mooney, cls.moran, cls.mullin, cls.murphy,
            cls.murray, cls.norcross, cls.ossoff, cls.padilla, cls.paul, cls.porter, cls.pressley,
            cls.react, cls.recordlist, cls.reschenthaler, cls.rickscott, cls.risch, cls.ronjohnson,
            cls.rosen, cls.rounds, cls.rubio, cls.scanlon, cls.schatz, cls.schumer, cls.schweikert,
            cls.senate_drupal, cls.senate_drupal_newscontent, cls.shaheen, cls.sherrod_brown, cls.stabenow,
            cls.steube, cls.sykes, cls.takano, cls.tester, cls.thune, cls.tillis, cls.timscott,
            cls.tinasmith, cls.titus, cls.tlaib, cls.toddyoung, cls.tokuda, cls.tonko, cls.trentkelly,
            cls.tuberville, cls.vance, cls.vanhollen, cls.warner, cls.welch, cls.whitehouse, cls.wicker,
            cls.wyden
        ]
    
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
                "https://amodei.house.gov/news-releases",
                "https://palmer.house.gov/media-center/press-releases",
                "https://newhouse.house.gov/media-center/press-releases",
                "https://doggett.house.gov/media/press-releases",
                "https://ocasio-cortez.house.gov/media/press-releases",
                "https://hudson.house.gov/media/press-releases",
                "https://davis.house.gov/media",
                "https://espaillat.house.gov/media/press-releases",
                "https://algreen.house.gov/media/press-releases",
                "https://mariodiazbalart.house.gov/media-center/press-releases",
                "https://biggs.house.gov/media/press-releases",
                "https://johnjoyce.house.gov/media/press-releases",
                "https://larson.house.gov/media-center/press-releases",
                "https://kaptur.house.gov/media-center/press-releases",
                "https://benniethompson.house.gov/media/press-releases",
                "https://walberg.house.gov/media/press-releases",
                "https://burchett.house.gov/media/press-releases",
                "https://cline.house.gov/media/press-releases",
                "https://golden.house.gov/media/press-releases",
                "https://harder.house.gov/media/press-releases",
                "https://dustyjohnson.house.gov/media/press-releases",
                "https://meuser.house.gov/media/press-releases",
                "https://miller.house.gov/media/press-releases",
                "https://johnrose.house.gov/media/press-releases",
                "https://roy.house.gov/media/press-releases",
                "https://sherrill.house.gov/media/press-releases",
                "https://steil.house.gov/media/press-releases",
                "https://schrier.house.gov/media/press-releases",
                "https://cherfilus-mccormick.house.gov/media/press-releases",
                "https://shontelbrown.house.gov/media/press-releases",
                "https://stansbury.house.gov/media/press-releases",
                "https://troycarter.house.gov/media/press-releases",
                "https://letlow.house.gov/media/press-releases",
                "https://matsui.house.gov/media",
                "https://harris.house.gov/media/press-releases",
                "https://wagner.house.gov/media-center/press-releases",
                "https://pappas.house.gov/media/press-releases",
                "https://crow.house.gov/media/press-releases",
                "https://chuygarcia.house.gov/media/press-releases",
                "https://omar.house.gov/media/press-releases",
                "https://underwood.house.gov/media/press-releases",
                "https://casten.house.gov/media/press-releases",
                "https://fleischmann.house.gov/media/press-releases",
                "https://stevens.house.gov/media/press-releases",
                "https://guest.house.gov/media/press-releases",
                "https://morelle.house.gov/media/press-releases",
                "https://beatty.house.gov/media-center/press-releases",
                "https://robinkelly.house.gov/media-center/press-releases",
                "https://moolenaar.house.gov/media-center/press-releases",
                "https://adams.house.gov/media-center/press-releases",
                "https://mfume.house.gov/media/press-releases",
                "https://tiffany.house.gov/media/press-releases",
                "https://barrymoore.house.gov/media/press-releases",
                "https://obernolte.house.gov/media/press-releases",
                "https://boebert.house.gov/media/press-releases",
                "https://cammack.house.gov/media/press-releases",
                "https://salazar.house.gov/media/press-releases",
                "https://hinson.house.gov/media/press-releases",
                "https://millermeeks.house.gov/media/press-releases",
                "https://feenstra.house.gov/media/press-releases",
                "https://marymiller.house.gov/media/press-releases",
                "https://mrvan.house.gov/media/press-releases",
                "https://spartz.house.gov/media/press-releases",
                "https://mann.house.gov/media/press-releases",
                "https://garbarino.house.gov/media/press-releases",
                "https://malliotakis.house.gov/media/press-releases",
                "https://bice.house.gov/media/press-releases",
                "https://bentz.house.gov/media/press-releases",
                "https://mace.house.gov/media/press-releases",
                "https://harshbarger.house.gov/media/press-releases",
                "https://blakemoore.house.gov/media/press-releases",
                "https://fitzgerald.house.gov/media/press-releases",
                "https://flood.house.gov/media/press-releases",
                "https://patryan.house.gov/media/press-releases",
                "https://kamlager-dove.house.gov/media/press-releases",
                "https://robertgarcia.house.gov/media/press-releases",
                "https://bean.house.gov/media/press-releases",
                "https://mccormick.house.gov/media/press-releases",
                "https://collins.house.gov/media/press-releases",
                "https://edwards.house.gov/media/press-releases",
                "https://kean.house.gov/media/press-releases",
                "https://goldman.house.gov/media/press-releases",
                "https://langworthy.house.gov/media/press-releases",
                "https://magaziner.house.gov/media/press-releases",
                "https://vanorden.house.gov/media/press-releases",
                "https://hunt.house.gov/media/press-releases",
                "https://casar.house.gov/media/press-releases",
                "https://crockett.house.gov/media/press-releases",
                "https://luttrell.house.gov/media/press-releases",
                "https://deluzio.house.gov/media/press-releases",
                "https://lalota.house.gov/media/press-releases",
                "https://vasquez.house.gov/media/press-releases",
                "https://scholten.house.gov/media/press-releases",
                "https://ivey.house.gov/media/press-releases",
                "https://sorensen.house.gov/media/press-releases",
                "https://nunn.house.gov/media/press-releases",
                "https://laurellee.house.gov/media/press-releases",
                "https://mills.house.gov/media/press-releases",
                "https://ciscomani.house.gov/media/press-releases",
                "https://democraticleader.house.gov/media/press-releases",
                "https://horsford.house.gov/media/press-releases",
                "https://cleaver.house.gov/media-center/press-releases",
                "https://aderholt.house.gov/media-center/press-releases",
                "https://courtney.house.gov/media-center/press-releases",
                "https://stauber.house.gov/media/press-releases",
                "https://mccaul.house.gov/media-center/press-releases",
                "https://foster.house.gov/media/press-releases",
                "https://schakowsky.house.gov/media/press-releases",
                "https://craig.house.gov/media/press-releases",
                "https://desaulnier.house.gov/media-center/press-releases",
                "https://scalise.house.gov/media/press-releases",
                "https://neguse.house.gov/media/press-releases",
                "https://murphy.house.gov/media/press-releases",
                "https://boyle.house.gov/media-center/press-releases",
                "https://calvert.house.gov/media/press-releases",
                "https://bobbyscott.house.gov/media-center/press-releases",
                "https://bilirakis.house.gov/media/press-releases",
                "https://delauro.house.gov/media-center/press-releases",
                "https://norton.house.gov/media/press-releases",
                "https://mikethompson.house.gov/newsroom/press-releases",
                "https://smucker.house.gov/media/press-releases",
                "https://degette.house.gov/media-center/press-releases",
                "https://ruiz.house.gov/media-center/press-releases",
                "https://sherman.house.gov/media-center/press-releases",
                "https://quigley.house.gov/media-center/press-releases",
                "https://waters.house.gov/media-center/press-releases",
                "https://swalwell.house.gov/media-center/press-releases",
                "https://khanna.house.gov/media/press-releases",
                "https://panetta.house.gov/media/press-releases",
                "https://schneider.house.gov/media/press-releases",
                "https://dankildee.house.gov/media/press-releases",
                "https://sylviagarcia.house.gov/media/press-releases",
                "https://susielee.house.gov/media/press-releases",
                "https://amo.house.gov/press-releases",
                "https://mcclellan.house.gov/media/press-releases",
                "https://rulli.house.gov/media/press-releases",
                "https://suozzi.house.gov/media/press-releases",
                "https://fong.house.gov/media/press-releases",
                "https://lopez.house.gov/media/press-releases",
                "https://mciver.house.gov/media/press-releases",
                "https://wied.house.gov/media/press-releases",
                "https://ericaleecarter.house.gov/media/press-releases",
                "https://moulton.house.gov/news/press-releases",
                "https://nehls.house.gov/media",
                "https://meng.house.gov/media-center/press-releases",
                "https://lindasanchez.house.gov/media-center/press-releases",
                "https://lamalfa.house.gov/media-center/press-releases",
                "https://dondavis.house.gov/media/press-releases",
                "https://strong.house.gov/media/press-releases",
                "https://chu.house.gov/media-center/press-releases",
                "https://lieu.house.gov/media-center/press-releases",
                "https://joewilson.house.gov/media/press-releases",
                "https://zinke.house.gov/media/press-releases",
                "https://pelosi.house.gov/news/press-releases",
                "https://rutherford.house.gov/media/press-releases",
                "https://veasey.house.gov/media-center/press-releases",
                "https://garamendi.house.gov/media/press-releases",
                "https://kustoff.house.gov/media/press-releases",
                "https://gonzalez.house.gov/media/press-releases",
                "https://costa.house.gov/media/press-releases",
                "https://houchin.house.gov/media/press-releases",
                "https://williams.house.gov/media-center/press-releases",
                "https://menendez.house.gov/media/press-releases",
                "https://pocan.house.gov/media-center/press-releases",
                "https://ogles.house.gov/media/press-releases",
                "https://velazquez.house.gov/media-center/press-releases",
                "https://bonamici.house.gov/media/press-releases",
                "https://keithself.house.gov/media/press-releases",
                "https://bishop.house.gov/media-center/press-releases",
                "https://hoyer.house.gov/media",
                "https://burlison.house.gov/media/press-releases",
                "https://jonathanjackson.house.gov/media/press-releases",
                "https://davids.house.gov/media/press-releases",
                "https://mccollum.house.gov/media/press-releases",
                "https://adamsmith.house.gov/news/press-releases",
                "https://hankjohnson.house.gov/media-center/press-releases",
                "https://evans.house.gov/media/press-releases",
                "https://salinas.house.gov/media/press-releases",
                "https://pallone.house.gov/media/press-releases",
                "https://ramirez.house.gov/media/press-releases",
                "https://graves.house.gov/media/press-releases",
                "https://cole.house.gov/media-center/press-releases",
                "https://jordan.house.gov/media/press-releases",
                "https://hageman.house.gov/media/press-releases",
                "https://figures.house.gov/media",
                "https://begich.house.gov/media/press-releases",
                "https://ansari.house.gov/media/press-releases",
                "https://simon.house.gov/media/press-releases",
                "https://gray.house.gov/media/press-releases",
                "https://liccardo.house.gov/media/press-releases",
                "https://rivas.house.gov/media/press-releases",
                "https://friedman.house.gov/media/press-releases",
                "https://tran.house.gov/media/press-releases",
                "https://min.house.gov/media/press-releases",
                "https://hurd.house.gov/media/press-releases",
                "https://crank.house.gov/media/press-releases",
                "https://gabeevans.house.gov/media/press-releases",
                "https://mcbride.house.gov/media/press-releases",
                "https://haridopolos.house.gov/media/press-releases",
                "https://jack.house.gov/media/press-releases",
                "https://stutzman.house.gov/media/press-releases",
                "https://shreve.house.gov/media/press-releases",
                "https://fields.house.gov/media/press-releases",
                "https://olszewski.house.gov/media/press-releases",
                "https://elfreth.house.gov/media/press-releases",
                "https://mcclaindelaney.house.gov/media/press-releases",
                "https://mcdonaldrivet.house.gov/media/press-releases",
                "https://barrett.house.gov/media/press-releases",
                "https://morrison.house.gov/media/press-releases",
                "https://bell.house.gov/media/press-releases",
                "https://downing.house.gov/media/press-releases",
                "https://goodlander.house.gov/media/press-releases",
                "https://pou.house.gov/media/press-releases",
                "https://mciver.house.gov/media/press-releases",
                "https://gillen.house.gov/media/press-releases",
                "https://latimer.house.gov/media/press-releases",
                "https://riley.house.gov/media/press-releases",
                "https://mannion.house.gov/media/press-releases",
                "https://mcdowell.house.gov/media/press-releases",
                "https://markharris.house.gov/media/press-releases",
                "https://harrigan.house.gov/media/press-releases",
                "https://knott.house.gov/media/press-releases",
                "https://timmoore.house.gov/media/press-releases",
                "https://fedorchak.house.gov/media/press-releases",
                "https://king-hinds.house.gov/media",
                "https://taylor.house.gov/media/press-releases",
                "https://dexter.house.gov/media/press-releases",
                "https://bynum.house.gov/media/press-releases",
                "https://mackenzie.house.gov/media/press-releases",
                "https://bresnahan.house.gov/media",
                "https://hernandez.house.gov/media/press-releases",
                "https://sheribiggs.house.gov/media/press-releases",
                "https://craiggoldman.house.gov/media/press-releases",
                "https://sylvesterturner.house.gov/media/press-releases",
                "https://gill.house.gov/media/press-releases",
                "https://juliejohnson.house.gov/media/press-releases",
                "https://mcguire.house.gov/media/press-releases",
                "https://vindman.house.gov/media/press-releases",
                "https://subramanyam.house.gov/media/press-releases",
                "https://baumgartner.house.gov/media/press-releases",
                "https://randall.house.gov/media/press-releases",
                "https://rileymoore.house.gov/media/press-releases"
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
    
    @classmethod
    def tillis(cls, page=1):
        """Scrape Senator Tillis's press releases."""
        results = []
        url = f"https://www.tillis.senate.gov/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        elements = doc.select(".element")
        for row in elements:
            link = row.select_one('a')
            title_elem = row.select_one(".element-title")
            date_elem = row.select_one(".element-datetime")
            
            if not (link and title_elem and date_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': title_elem.text.strip(),
                'date': date,
                'domain': "www.tillis.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def wicker(cls, page=1):
        """Scrape Senator Wicker's press releases."""
        results = []
        url = f"https://www.wicker.senate.gov/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        elements = doc.select(".element")
        for row in elements:
            link = row.select_one('a')
            title_elem = row.select_one(".post-media-list-title")
            date_elem = row.select_one(".post-media-list-date")
            
            if not (link and title_elem and date_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': title_elem.text.strip(),
                'date': date,
                'domain': "www.wicker.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def moran(cls, page=1):
        """Scrape Senator Moran's press releases."""
        results = []
        domain = "www.moran.senate.gov"
        url = f"https://www.moran.senate.gov/public/index.cfm/news-releases?page={page}"
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
                'url': f"https://www.moran.senate.gov{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def boozman(cls, page=1):
        """Scrape Senator Boozman's press releases."""
        results = []
        domain = "www.boozman.senate.gov"
        url = f"https://www.boozman.senate.gov/public/index.cfm/press-releases?page={page}"
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
                'url': f"https://www.boozman.senate.gov{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def thune(cls, page=1):
        """Scrape Senator Thune's press releases."""
        results = []
        url = f"https://www.thune.senate.gov/public/index.cfm/press-releases?page={page}"
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
                'url': f"https://www.thune.senate.gov{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': "www.thune.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def murphy(cls, page=1):
        """Scrape Senator Murphy's press releases."""
        results = []
        url = f"https://www.murphy.senate.gov/newsroom/press-releases?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select("li.PageList__item")
        for row in items:
            link = row.select_one('a')
            h1 = row.select_one('h1')
            date_elem = row.select_one('.ArticleBlock__date')
            
            if not (link and h1 and date_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': h1.text.strip(),
                'date': date,
                'domain': 'www.murphy.senate.gov'
            }
            results.append(result)
        
        return results
    
    @classmethod
    def markey(cls, page=1):
        """Scrape Senator Markey's press releases."""
        results = []
        domain = 'www.markey.senate.gov'
        url = f"https://www.markey.senate.gov/news/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select(".ArticleBlock")
        for row in blocks:
            link = row.select_one('a')
            date_elem = row.select_one('.ArticleBlock__date')
            
            if not (link and date_elem):
                continue
                
            date = None
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
    def cotton(cls, page=1):
        """Scrape Senator Cotton's press releases."""
        results = []
        domain = 'www.cotton.senate.gov'
        url = f"https://www.cotton.senate.gov/news/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select(".ArticleBlock")
        for row in blocks:
            link = row.select_one('a')
            date_elem = row.select_one('.ArticleBlock__date')
            
            if not (link and date_elem):
                continue
                
            date = None
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
                try:
                    date = datetime.datetime.strptime(prev.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
            
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
    def cassidy(cls, page=1):
        """Scrape Senator Cassidy's press releases."""
        results = []
        url = f"https://www.cassidy.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("a")
            date_elem = row.select_one("ul li")
            
            if not (link and date_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': "www.cassidy.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def britt(cls, page=1):
        """Scrape Senator Britt's press releases."""
        results = []
        url = f"https://www.britt.senate.gov/media/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            date_elem = row.select_one("h3.elementor-heading-title")
            
            if not (link and date_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': "www.britt.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def toddyoung(cls, page=1):
        """Scrape Senator Todd Young's press releases."""
        results = []
        url = f"https://www.young.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("a")
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
                'domain': "www.young.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def markkelly(cls, page=1):
        """Scrape Senator Mark Kelly's press releases."""
        results = []
        url = f"https://www.kelly.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select('div.jet-listing-grid__item')
        for row in items:
            link = row.select_one("h3 a")
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
                'domain': "www.kelly.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def hagerty(cls, page=1):
        """Scrape Senator Hagerty's press releases."""
        results = []
        url = f"https://www.hagerty.senate.gov/press-releases/?et_blog&sf_paged={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        posts = doc.select("article.et_pb_post")
        for row in posts:
            link = row.select_one("h2 a")
            date_span = row.select_one("p span.published")
            
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
                'domain': "www.hagerty.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def budd(cls, page=1):
        """Scrape Senator Budd's press releases."""
        results = []
        url = f"https://www.budd.senate.gov/category/news/press-releases/page/{page}/?et_blog"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        posts = doc.select("article.et_pb_post")
        for row in posts:
            link = row.select_one("h2 a")
            date_span = row.select_one("p span.published")
            
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
                'domain': "www.budd.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def vance(cls, page=1):
        """Scrape Senator Vance's press releases."""
        results = []
        url = f"https://www.vance.senate.gov/press-releases/page/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        posts = doc.select(".elementor .post")
        for row in posts:
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
                'domain': "www.vance.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def lummis(cls, page=1):
        """Scrape Senator Lummis's press releases."""
        results = []
        url = f"https://www.lummis.senate.gov/press-releases/page/{page}/?et_blog"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        posts = doc.select("article.et_pb_post")
        for row in posts:
            link = row.select_one("h2 a")
            date_span = row.select_one("p span.published")
            
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
                'domain': "www.lummis.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def welch(cls, page=1):
        """Scrape Senator Welch's press releases."""
        results = []
        url = f"https://www.welch.senate.gov/category/press-release/page/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("a")
            h2 = row.select_one("h2")
            date_span = row.select_one(".postDate span")
            
            if not (link and h2 and date_span):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': h2.text.strip(),
                'date': date,
                'domain': "www.welch.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def rubio(cls, page=1):
        """Scrape Senator Rubio's press releases."""
        results = []
        url = f"https://www.rubio.senate.gov/news/page/{page}/?et_blog"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        posts = doc.select("article.et_pb_post")
        for row in posts:
            link = row.select_one("h3 a")
            date_span = row.select_one("p span.published")
            
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
                'domain': "www.rubio.senate.gov"
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
                    
                date = None
                try:
                    date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
                except ValueError:
                    pass
                
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
                
            date = None
            try:
                date = datetime.datetime.strptime(cells[0].text.strip(), "%m/%d/%y").date()
            except ValueError:
                pass
            
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
    def grassley(cls, page=1):
        """Scrape Senator Grassley's press releases."""
        results = []
        url = f"https://www.grassley.senate.gov/news/news-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select("li.PageList__item")
        for row in items:
            link = row.select_one('a')
            p_elem = row.select_one('p')
            
            if not (link and p_elem):
                continue
                
            date = None
            try:
                date_text = p_elem.text.replace('.', '/')
                date = datetime.datetime.strptime(date_text, "%m/%d/%y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': "www.grassley.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def vanhollen(cls, page=1):
        """Scrape Senator Van Hollen's press releases."""
        results = []
        url = f"https://www.vanhollen.senate.gov/news/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select("ul li.PageList__item")
        for row in items:
            link = row.select_one('a')
            p_elem = row.select_one('p')
            
            if not (link and p_elem):
                continue
                
            date = None
            try:
                date_text = p_elem.text.replace('.', '/')
                date = datetime.datetime.strptime(date_text, "%m/%d/%y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': "www.vanhollen.senate.gov"
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
                
            date = None
            try:
                date = datetime.datetime.strptime(cells[0].text.strip(), "%m/%d/%y").date()
            except ValueError:
                pass
            
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
    def garypeters(cls, page=1):
        """Scrape Senator Gary Peters's press releases."""
        results = []
        url = f"https://www.peters.senate.gov/newsroom/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one('a')
            h2 = row.select_one('h2')
            p_elem = row.select_one('p')
            
            if not (link and h2 and p_elem):
                continue
                
            date = None
            try:
                date_text = p_elem.text.replace('.', '/')
                date = datetime.datetime.strptime(date_text, "%m/%d/%y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': h2.text.strip(),
                'date': date,
                'domain': 'www.peters.senate.gov'
            }
            results.append(result)
        
        return results
    
    @classmethod
    def jackreed(cls, page=1):
        """Scrape Senator Jack Reed's press releases."""
        results = []
        url = f"https://www.reed.senate.gov/news/releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
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
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': 'www.reed.senate.gov'
            }
            results.append(result)
        
        return results
    
    @classmethod
    def rounds(cls, page=1):
        """Scrape Senator Rounds's press releases."""
        results = []
        url = f"https://www.rounds.senate.gov/newsroom/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one('a')
            p_elem = row.select_one("p")
            
            if not (link and p_elem):
                continue
                
            date = None
            try:
                date_text = p_elem.text.replace(".", "/")
                date = datetime.datetime.strptime(date_text, "%m/%d/%y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': 'www.rounds.senate.gov'
            }
            results.append(result)
        
        return results
    
    @classmethod
    def kaine(cls, page=1):
        """Scrape Senator Kaine's press releases."""
        results = []
        url = f"https://www.kaine.senate.gov/news?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one('a')
            p_elem = row.select_one("p")
            
            if not (link and p_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(p_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': 'www.kaine.senate.gov'
            }
            results.append(result)
        
        return results
    
    @classmethod
    def blackburn(cls, page=1):
        """Scrape Senator Blackburn's press releases."""
        results = []
        url = f"https://www.blackburn.senate.gov/news/cc8c80c1-d564-4bbb-93a4-f1d772346ae0?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        elements = doc.select("div.element")
        for row in elements:
            link = row.select_one('a')
            title_div = row.select_one('div.element-title')
            date_span = row.select_one('span.element-datetime')
            
            if not (link and title_div and date_span):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': title_div.text.strip(),
                'date': date,
                'domain': 'www.blackburn.senate.gov'
            }
            results.append(result)
        
        return results
    
    @classmethod
    def gillibrand(cls, page=1):
        """Scrape Senator Gillibrand's press releases."""
        results = []
        url = f"https://www.gillibrand.senate.gov/press-releases/page/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select(".et_pb_ajax_pagination_container article")
        for row in articles:
            link = row.select_one('h2 a')
            date_p = row.select_one('p.published')
            
            if not (link and date_p):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(date_p.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': "www.gillibrand.senate.gov"
            }
            results.append(result)
        
        return results
    
    @classmethod
    def heinrich(cls, page=1):
        """Scrape Senator Heinrich's press releases."""
        results = []
        url = f"https://www.heinrich.senate.gov/newsroom/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one('a')
            h2 = row.select_one('h2')
            p_elem = row.select_one('p')
            
            if not (link and h2 and p_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(p_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': h2.text.strip(),
                'date': date,
                'domain': 'www.heinrich.senate.gov'
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
                
            date = None
            try:
                date = datetime.datetime.strptime(cells[0].text.strip(), "%m/%d/%y").date()
            except ValueError:
                pass
            
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
    def clyburn(cls):
        """Scrape Congressman Clyburn's press releases."""
        results = []
        domain = 'clyburn.house.gov'
        url = "https://clyburn.house.gov/press-releases/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        cards = doc.select('.elementor-post__card')
        for row in cards:
            link = row.select_one("a")
            h3 = row.select_one("h3 a")
            date_span = row.select_one("span.elementor-post-date")
            
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
    def trentkelly(cls, page=1):
        """Scrape Congressman Trent Kelly's press releases."""
        results = []
        domain = 'trentkelly.house.gov'
        url = f"https://trentkelly.house.gov/newsroom/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one('a')
            h3 = row.select_one('h3')
            time_elem = row.select_one('time')
            
            if not (link and h3 and time_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': f"https://trentkelly.house.gov/newsroom/{link.get('href')}",
                'title': h3.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def jeffries(cls, page=1):
        """Scrape Congressman Jeffries's press releases."""
        results = []
        domain = 'jeffries.house.gov'
        url = f"https://jeffries.house.gov/category/press-release/page/{page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")[:10]
        for row in articles:
            link = row.select_one('a')
            h1 = row.select_one("h1")
            time_elem = row.select_one('time')
            
            if not (link and h1 and time_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': link.get('href'),
                'title': h1.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def bacon(cls, page=1):
        """Scrape Congressman Bacon's press releases."""
        results = []
        domain = 'bacon.house.gov'
        url = f"https://bacon.house.gov/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            h2 = row.select_one("h2")
            time_elem = row.select_one('time')
            
            if not (link and h2 and time_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': f"https://bacon.house.gov/news/{link.get('href')}",
                'title': h2.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def larsen(cls, page=1):
        """Scrape Congressman Larsen's press releases."""
        results = []
        domain = 'larsen.house.gov'
        url = f"https://larsen.house.gov/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        news_holds = doc.select('.news-texthold')
        for row in news_holds:
            link = row.select_one('h2 a')
            time_elem = row.select_one('time')
            
            if not (link and time_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': f"https://larsen.house.gov/news/{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def connolly(cls, page=1):
        """Scrape Congressman Connolly's press releases."""
        results = []
        domain = 'connolly.house.gov'
        url = f"https://connolly.house.gov/news/documentquery.aspx?DocumentTypeID=1952&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        news_holds = doc.select('.news-texthold')
        for row in news_holds:
            link = row.select_one('h2 a')
            time_elem = row.select_one('time')
            
            if not (link and time_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': f"https://connolly.house.gov/news/{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def tonko(cls, page=1):
        """Scrape Congressman Tonko's press releases."""
        results = []
        domain = 'tonko.house.gov'
        url = f"https://tonko.house.gov/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        news_holds = doc.select('.news-texthold')
        for row in news_holds:
            link = row.select_one('h2 a')
            time_elem = row.select_one('time')
            
            if not (link and time_elem):
                continue
                
            date = None
            try:
                date = datetime.datetime.strptime(time_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass
            
            result = {
                'source': url,
                'url': f"https://tonko.house.gov/news/{link.get('href')}",
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def aguilar(cls, page=1):
        """Scrape Congressman Aguilar's press releases."""
        results = []
        domain = 'aguilar.house.gov'
        url = f"https://aguilar.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def bergman(cls, page=1):
        """Scrape Congressman Bergman's press releases."""
        results = []
        domain = 'bergman.house.gov'
        url = f"https://bergman.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def brownley(cls, page=1):
        """Scrape Congresswoman Brownley's press releases."""
        results = []
        domain = 'brownley.house.gov'
        url = f"https://brownley.house.gov/news/documentquery.aspx?DocumentTypeID=2519&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://brownley.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def cantwell(cls, page=1):
        """Scrape Senator Cantwell's press releases."""
        results = []
        domain = 'www.cantwell.senate.gov'
        url = f"https://www.cantwell.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def capito(cls, page=1):
        """Scrape Senator Capito's press releases."""
        results = []
        domain = 'www.capito.senate.gov'
        url = f"https://www.capito.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def carey(cls, page=1):
        """Scrape Congressman Carey's press releases."""
        results = []
        domain = 'carey.house.gov'
        url = f"https://carey.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def clarke(cls, page=1):
        """Scrape Congresswoman Clarke's press releases."""
        results = []
        domain = 'clarke.house.gov'
        url = f"https://clarke.house.gov/newsroom/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
            date_elem = row.select_one("td time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://clarke.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def cortezmasto(cls, page=1):
        """Scrape Senator Cortez Masto's press releases."""
        results = []
        domain = 'www.cortezmasto.senate.gov'
        url = f"https://www.cortezmasto.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def crawford(cls, page=1):
        """Scrape Congressman Crawford's press releases."""
        results = []
        domain = 'crawford.house.gov'
        url = f"https://crawford.house.gov/media-center/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("td a")
            if not link:
                continue
            date_elem = row.select_one("time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://crawford.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def cruz(cls, page=1):
        """Scrape Senator Cruz's press releases."""
        results = []
        domain = 'www.cruz.senate.gov'
        url = f"https://www.cruz.senate.gov/newsroom/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def daines(cls, page=1):
        """Scrape Senator Daines's press releases."""
        results = []
        domain = 'www.daines.senate.gov'
        url = f"https://www.daines.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def duckworth(cls, page=1):
        """Scrape Senator Duckworth's press releases."""
        results = []
        domain = 'www.duckworth.senate.gov'
        url = f"https://www.duckworth.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def ellzey(cls, page=1):
        """Scrape Congressman Ellzey's press releases."""
        results = []
        domain = 'ellzey.house.gov'
        url = f"https://ellzey.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def emmer(cls, page=1):
        """Scrape Congressman Emmer's press releases."""
        results = []
        domain = 'emmer.house.gov'
        url = f"https://emmer.house.gov/news/documentquery.aspx?DocumentTypeID=2516&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://emmer.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def fetterman(cls, page=1):
        """Scrape Senator Fetterman's press releases."""
        results = []
        domain = 'www.fetterman.senate.gov'
        url = f"https://www.fetterman.senate.gov/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def foxx(cls, page=1):
        """Scrape Congresswoman Foxx's press releases."""
        results = []
        domain = 'foxx.house.gov'
        url = f"https://foxx.house.gov/news/documentquery.aspx?DocumentTypeID=1525&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://foxx.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def gimenez(cls, page=1):
        """Scrape Congressman Gimenez's press releases."""
        results = []
        domain = 'gimenez.house.gov'
        url = f"https://gimenez.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def gosar(cls, page=1):
        """Scrape Congressman Gosar's press releases."""
        results = []
        domain = 'gosar.house.gov'
        url = f"https://gosar.house.gov/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://gosar.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def graham(cls, page=1):
        """Scrape Senator Graham's press releases."""
        results = []
        domain = 'www.lgraham.senate.gov'
        url = f"https://www.lgraham.senate.gov/public/index.cfm/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table tbody tr")
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
            date_elem = row.select_one("td time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://www.lgraham.senate.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def griffith(cls, page=1):
        """Scrape Congressman Griffith's press releases."""
        results = []
        domain = 'griffith.house.gov'
        url = f"https://griffith.house.gov/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://griffith.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def grijalva(cls, page=1):
        """Scrape Congressman Grijalva's press releases."""
        results = []
        domain = 'grijalva.house.gov'
        url = f"https://grijalva.house.gov/media-center/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("td a")
            if not link:
                continue
            date_elem = row.select_one("time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://grijalva.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def hassan(cls, page=1):
        """Scrape Senator Hassan's press releases."""
        results = []
        domain = 'www.hassan.senate.gov'
        url = f"https://www.hassan.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def houlahan(cls, page=1):
        """Scrape Congresswoman Houlahan's press releases."""
        results = []
        domain = 'houlahan.house.gov'
        url = f"https://houlahan.house.gov/news/documentquery.aspx?DocumentTypeID=2545&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://houlahan.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def huizenga(cls, page=1):
        """Scrape Congressman Huizenga's press releases."""
        results = []
        domain = 'huizenga.house.gov'
        url = f"https://huizenga.house.gov/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://huizenga.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def hydesmith(cls, page=1):
        """Scrape Senator Hyde-Smith's press releases."""
        results = []
        domain = 'www.hydesmith.senate.gov'
        url = f"https://www.hydesmith.senate.gov/media/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def jasonsmith(cls, page=1):
        """Scrape Congressman Jason Smith's press releases."""
        results = []
        domain = 'jasonsmith.house.gov'
        url = f"https://jasonsmith.house.gov/news/documentquery.aspx?DocumentTypeID=1545&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://jasonsmith.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def jayapal(cls, page=1):
        """Scrape Congresswoman Jayapal's press releases."""
        results = []
        domain = 'jayapal.house.gov'
        url = f"https://jayapal.house.gov/newsroom/press-releases/?jsf=jet-engine&tax=press_cat:16&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h5 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def lujan(cls, page=1):
        """Scrape Senator Luján's press releases."""
        results = []
        domain = 'www.lujan.senate.gov'
        url = f"https://www.lujan.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def mast(cls, page=1):
        """Scrape Congressman Mast's press releases."""
        results = []
        domain = 'mast.house.gov'
        url = f"https://mast.house.gov/news/documentquery.aspx?DocumentTypeID=2526&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://mast.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def mcgovern(cls, page=1):
        """Scrape Congressman McGovern's press releases."""
        results = []
        domain = 'mcgovern.house.gov'
        url = f"https://mcgovern.house.gov/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://mcgovern.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def mikelee(cls, page=1):
        """Scrape Senator Mike Lee's press releases."""
        results = []
        domain = 'www.lee.senate.gov'
        url = f"https://www.lee.senate.gov/news/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def mooney(cls, page=1):
        """Scrape Congressman Mooney's press releases."""
        results = []
        domain = 'mooney.house.gov'
        url = f"https://mooney.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def mullin(cls, page=1):
        """Scrape Senator Mullin's press releases."""
        results = []
        domain = 'www.mullin.senate.gov'
        url = f"https://www.mullin.senate.gov/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def murray(cls, page=1):
        """Scrape Senator Murray's press releases."""
        results = []
        domain = 'www.murray.senate.gov'
        url = f"https://www.murray.senate.gov/category/press-releases/page/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("time.date")
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
    def norcross(cls, page=1):
        """Scrape Congressman Norcross's press releases."""
        results = []
        domain = 'norcross.house.gov'
        url = f"https://norcross.house.gov/news/documentquery.aspx?DocumentTypeID=27&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://norcross.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def ossoff(cls, page=1):
        """Scrape Senator Ossoff's press releases."""
        results = []
        domain = 'www.ossoff.senate.gov'
        url = f"https://www.ossoff.senate.gov/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def padilla(cls, page=1):
        """Scrape Senator Padilla's press releases."""
        results = []
        domain = 'www.padilla.senate.gov'
        url = f"https://www.padilla.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def paul(cls, page=1):
        """Scrape Senator Rand Paul's press releases."""
        results = []
        domain = 'www.paul.senate.gov'
        url = f"https://www.paul.senate.gov/news/press?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def porter(cls, page=1):
        """Scrape Congresswoman Porter's press releases."""
        results = []
        domain = 'porter.house.gov'
        url = f"https://porter.house.gov/news/documentquery.aspx?DocumentTypeID=2581&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://porter.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def pressley(cls, page=1):
        """Scrape Congresswoman Pressley's press releases."""
        results = []
        domain = 'pressley.house.gov'
        url = f"https://pressley.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def reschenthaler(cls, page=1):
        """Scrape Congressman Reschenthaler's press releases."""
        results = []
        domain = 'reschenthaler.house.gov'
        url = f"https://reschenthaler.house.gov/media/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def rickscott(cls, page=1):
        """Scrape Senator Rick Scott's press releases."""
        results = []
        domain = 'www.rickscott.senate.gov'
        url = f"https://www.rickscott.senate.gov/category/press-releases/page/{page}/"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("time.date")
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
    def ronjohnson(cls, page=1):
        """Scrape Senator Ron Johnson's press releases."""
        results = []
        domain = 'www.ronjohnson.senate.gov'
        url = f"https://www.ronjohnson.senate.gov/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def rosen(cls, page=1):
        """Scrape Senator Rosen's press releases."""
        results = []
        domain = 'www.rosen.senate.gov'
        url = f"https://www.rosen.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def schatz(cls, page=1):
        """Scrape Senator Schatz's press releases."""
        results = []
        domain = 'www.schatz.senate.gov'
        url = f"https://www.schatz.senate.gov/news/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def schumer(cls, page=1):
        """Scrape Senator Schumer's press releases."""
        results = []
        domain = 'www.schumer.senate.gov'
        url = f"https://www.schumer.senate.gov/newsroom/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def schweikert(cls, page=1):
        """Scrape Congressman Schweikert's press releases."""
        results = []
        domain = 'schweikert.house.gov'
        url = f"https://schweikert.house.gov/news/documentquery.aspx?DocumentTypeID=1530&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://schweikert.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def takano(cls, page=1):
        """Scrape Congressman Takano's press releases."""
        results = []
        domain = 'takano.house.gov'
        url = f"https://takano.house.gov/newsroom/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("td a")
            if not link:
                continue
            date_elem = row.select_one("time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://takano.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def tinasmith(cls, page=1):
        """Scrape Senator Tina Smith's press releases."""
        results = []
        domain = 'www.smith.senate.gov'
        url = f"https://www.smith.senate.gov/media/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def titus(cls, page=1):
        """Scrape Congresswoman Titus's press releases."""
        results = []
        domain = 'titus.house.gov'
        url = f"https://titus.house.gov/news/documentquery.aspx?DocumentTypeID=1510&Page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        articles = doc.select("article")
        for row in articles:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("span.middot")
            date = None
            if date_elem and date_elem.next_sibling:
                date_text = date_elem.next_sibling.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://titus.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def tlaib(cls, page=1):
        """Scrape Congresswoman Tlaib's press releases."""
        results = []
        domain = 'tlaib.house.gov'
        url = f"https://tlaib.house.gov/newsroom/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("td a")
            if not link:
                continue
            date_elem = row.select_one("time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://tlaib.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def tuberville(cls, page=1):
        """Scrape Senator Tuberville's press releases."""
        results = []
        domain = 'www.tuberville.senate.gov'
        url = f"https://www.tuberville.senate.gov/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def warner(cls, page=1):
        """Scrape Senator Warner's press releases."""
        results = []
        domain = 'www.warner.senate.gov'
        url = f"https://www.warner.senate.gov/public/index.cfm?p=press-releases&page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table tbody tr")
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
            date_elem = row.select_one("td time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://www.warner.senate.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def whitehouse(cls, page=1):
        """Scrape Senator Whitehouse's press releases."""
        results = []
        domain = 'www.whitehouse.senate.gov'
        url = f"https://www.whitehouse.senate.gov/news/release?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def wyden(cls, page=1):
        """Scrape Senator Wyden's press releases."""
        results = []
        domain = 'www.wyden.senate.gov'
        url = f"https://www.wyden.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def scanlon(cls, page=1):
        """Scrape Congresswoman Scanlon's press releases."""
        results = []
        domain = 'scanlon.house.gov'
        url = f"https://scanlon.house.gov/media/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("td a")
            if not link:
                continue
            date_elem = row.select_one("time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://scanlon.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
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
                date_text = date_text_elem.text.strip()
                try:
                    date = datetime.datetime.strptime(date_text, "%m.%d.%Y").date()
                except (ValueError, AttributeError):
                    pass
            
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
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
                except (ValueError, AttributeError):
                    pass
            
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
                    try:
                        date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
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
    
    @classmethod
    def barr(cls, page=1):
        """Scrape Congressman Barr's press releases."""
        results = []
        domain = 'barr.house.gov'
        url = f"https://barr.house.gov/media-center/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("td a")
            if not link:
                continue
            date_elem = row.select_one("time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://barr.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def tester(cls, page=1):
        """Scrape Senator Tester's press releases."""
        results = []
        domain = 'www.tester.senate.gov'
        url = f"https://www.tester.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        items = doc.select(".jet-listing-grid__item")
        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue
            date_elem = row.select_one("span.elementor-icon-list-text")
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
    def sherrod_brown(cls, page=1):
        """Scrape Senator Sherrod Brown's press releases."""
        results = []
        domain = 'www.brown.senate.gov'
        url = f"https://www.brown.senate.gov/newsroom/press?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def durbin(cls, page=1):
        """Scrape Senator Durbin's press releases."""
        results = []
        domain = 'www.durbin.senate.gov'
        url = f"https://www.durbin.senate.gov/newsroom/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def bennet(cls, page=1):
        """Scrape Senator Bennet's press releases."""
        results = []
        domain = 'www.bennet.senate.gov'
        url = f"https://www.bennet.senate.gov/public/index.cfm/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table tbody tr")
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
            date_elem = row.select_one("td time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://www.bennet.senate.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def cardin(cls, page=1):
        """Scrape Senator Cardin's press releases."""
        results = []
        domain = 'www.cardin.senate.gov'
        url = f"https://www.cardin.senate.gov/newsroom/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def carper(cls, page=1):
        """Scrape Senator Carper's press releases."""
        results = []
        domain = 'www.carper.senate.gov'
        url = f"https://www.carper.senate.gov/news/press-releases?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def casey(cls, page=1):
        """Scrape Senator Casey's press releases."""
        results = []
        domain = 'www.casey.senate.gov'
        url = f"https://www.casey.senate.gov/news/releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def coons(cls, page=1):
        """Scrape Senator Coons's press releases."""
        results = []
        domain = 'www.coons.senate.gov'
        url = f"https://www.coons.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def ernst(cls, page=1):
        """Scrape Senator Ernst's press releases."""
        results = []
        domain = 'www.ernst.senate.gov'
        url = f"https://www.ernst.senate.gov/public/index.cfm/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table tbody tr")
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
            date_elem = row.select_one("td time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://www.ernst.senate.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def hirono(cls, page=1):
        """Scrape Senator Hirono's press releases."""
        results = []
        domain = 'www.hirono.senate.gov'
        url = f"https://www.hirono.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def hoeven(cls, page=1):
        """Scrape Senator Hoeven's press releases."""
        results = []
        domain = 'www.hoeven.senate.gov'
        url = f"https://www.hoeven.senate.gov/public/index.cfm/news-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table tbody tr")
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
            date_elem = row.select_one("td time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://www.hoeven.senate.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def lankford(cls, page=1):
        """Scrape Senator Lankford's press releases."""
        results = []
        domain = 'www.lankford.senate.gov'
        url = f"https://www.lankford.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def manchin(cls, page=1):
        """Scrape Senator Manchin's press releases."""
        results = []
        domain = 'www.manchin.senate.gov'
        url = f"https://www.manchin.senate.gov/newsroom/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def menendez(cls, page=1):
        """Scrape Senator Menendez's press releases."""
        results = []
        domain = 'www.menendez.senate.gov'
        url = f"https://www.menendez.senate.gov/newsroom/press?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def merkley(cls, page=1):
        """Scrape Senator Merkley's press releases."""
        results = []
        domain = 'www.merkley.senate.gov'
        url = f"https://www.merkley.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def risch(cls, page=1):
        """Scrape Senator Risch's press releases."""
        results = []
        domain = 'www.risch.senate.gov'
        url = f"https://www.risch.senate.gov/public/index.cfm/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("table tbody tr")
        for row in rows:
            link = row.select_one("a")
            if not link:
                continue
            date_elem = row.select_one("td time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://www.risch.senate.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def stabenow(cls, page=1):
        """Scrape Senator Stabenow's press releases."""
        results = []
        domain = 'www.stabenow.senate.gov'
        url = f"https://www.stabenow.senate.gov/news?PageNum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def baldwin(cls, page=1):
        """Scrape Senator Baldwin's press releases."""
        results = []
        domain = 'www.baldwin.senate.gov'
        url = f"https://www.baldwin.senate.gov/news/press-releases?PageNum_rs={page}&"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                continue
            date_elem = row.select_one("p")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m.%d.%Y").date()
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
    def lofgren(cls, page=1):
        """Scrape Congresswoman Lofgren's press releases."""
        results = []
        domain = 'lofgren.house.gov'
        url = f"https://lofgren.house.gov/media/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("td a")
            if not link:
                continue
            date_elem = row.select_one("time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://lofgren.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results
    
    @classmethod
    def lucas(cls, page=1):
        """Scrape Congressman Lucas's press releases."""
        results = []
        domain = 'lucas.house.gov'
        url = f"https://lucas.house.gov/media-center/press-releases?page={page}"
        doc = cls.open_html(url)
        if not doc:
            return []
        
        rows = doc.select("tr")[1:]
        for row in rows:
            link = row.select_one("td a")
            if not link:
                continue
            date_elem = row.select_one("time")
            date = None
            if date_elem:
                try:
                    date = datetime.datetime.strptime(date_elem.text.strip(), "%m/%d/%y").date()
                except ValueError:
                    pass
            
            result = {
                'source': url,
                'url': "https://lucas.house.gov" + link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)
        
        return results