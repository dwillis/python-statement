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
    
    # Configuration for scrapers that use generic methods
    # Maps scraper_method name -> {method: generic_method_name, url_base: base_url}
    SCRAPER_CONFIG = {
        # table_recordlist_date pattern - Senate sites with table.recordListDate
        'moran': {'method': 'table_recordlist_date', 'url_base': 'https://www.moran.senate.gov/public/index.cfm/news-releases'},
        'boozman': {'method': 'table_recordlist_date', 'url_base': 'https://www.boozman.senate.gov/public/index.cfm/press-releases'},
        'thune': {'method': 'table_recordlist_date', 'url_base': 'https://www.thune.senate.gov/public/index.cfm/press-releases'},
        'barrasso': {'method': 'table_recordlist_date', 'url_base': 'https://www.barrasso.senate.gov/public/index.cfm/news-releases'},
        'graham': {'method': 'table_recordlist_date', 'url_base': 'https://www.lgraham.senate.gov/public/index.cfm/press-releases'},
        
        # jet_listing_elementor pattern - WordPress/Elementor sites
        'timscott': {'method': 'jet_listing_elementor', 'url_base': 'https://www.scott.senate.gov/media-center/press-releases/jsf/jet-engine:press-list'},
        'cassidy': {'method': 'jet_listing_elementor', 'url_base': 'https://www.cassidy.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list'},
        'fetterman': {'method': 'jet_listing_elementor', 'url_base': 'https://www.fetterman.senate.gov/press-releases/?jsf=jet-engine:press-list'},
        'tester': {'method': 'jet_listing_elementor', 'url_base': 'https://www.tester.senate.gov/newsroom/press-releases'},
        'marshall': {'method': 'jet_listing_elementor', 'url_base': 'https://www.marshall.senate.gov/media/press-releases'},
        'britt': {'method': 'jet_listing_elementor', 'url_base': 'https://www.britt.senate.gov/media/press-releases/?jsf=jet-engine:press-list'},
        'toddyoung': {'method': 'jet_listing_elementor', 'url_base': 'https://www.young.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list'},
        'markkelly': {'method': 'jet_listing_elementor', 'url_base': 'https://www.kelly.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list'},
        'lujan': {'method': 'jet_listing_elementor', 'url_base': 'https://www.lujan.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list'},
        'mullin': {'method': 'jet_listing_elementor', 'url_base': 'https://www.mullin.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list'},
        'ossoff': {'method': 'jet_listing_elementor', 'url_base': 'https://www.ossoff.senate.gov/press-releases/?jsf=jet-engine:press-list'},
        
        # article_block_h2_p_date pattern - Senate sites with ArticleBlock
        'chrismurphy': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.murphy.senate.gov/newsroom/press-releases'},
        'markey': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.markey.senate.gov/news/press-releases'},
        'cotton': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.cotton.senate.gov/news/press-releases'},
        'rounds': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.rounds.senate.gov/newsroom/press-releases'},
        'kaine': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.kaine.senate.gov/news'},
        'durbin': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.durbin.senate.gov/newsroom/press-releases'},
        'sherrod_brown': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.brown.senate.gov/newsroom/press'},
        'crapo': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.crapo.senate.gov/media/newsreleases'},
        'hirono': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.hirono.senate.gov/news/press-releases'},
        'garypeters': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.peters.senate.gov/newsroom/press-releases'},
        'jackreed': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.reed.senate.gov/news/releases'},
        'heinrich': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.heinrich.senate.gov/newsroom/press-releases'},
        'aguilar': {'method': 'article_block_h2_p_date', 'url_base': 'https://aguilar.house.gov/media/press-releases'},
        'bergman': {'method': 'article_block_h2_p_date', 'url_base': 'https://bergman.house.gov/media/press-releases'},
        'cantwell': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.cantwell.senate.gov/news/press-releases'},
        'capito': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.capito.senate.gov/news/press-releases'},
        'carey': {'method': 'article_block_h2_p_date', 'url_base': 'https://carey.house.gov/media/press-releases'},
        'cortezmasto': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.cortezmasto.senate.gov/news/press-releases'},
        'cruz': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.cruz.senate.gov/newsroom/press-releases'},
        'daines': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.daines.senate.gov/news/press-releases'},
        'duckworth': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.duckworth.senate.gov/news/press-releases'},
        'ellzey': {'method': 'article_block_h2_p_date', 'url_base': 'https://ellzey.house.gov/media/press-releases'},
        'gimenez': {'method': 'article_block_h2_p_date', 'url_base': 'https://gimenez.house.gov/media/press-releases'},
        'hassan': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.hassan.senate.gov/news/press-releases'},
        
        # element_post_media pattern - Senate sites with .element class
        'tillis': {'method': 'element_post_media', 'url_base': 'https://www.tillis.senate.gov/press-releases'},
        'wicker': {'method': 'element_post_media', 'url_base': 'https://www.wicker.senate.gov/press-releases'},
        'blackburn': {'method': 'element_post_media', 'url_base': 'https://www.blackburn.senate.gov/news/cc8c80c1-d564-4bbb-93a4-f1d772346ae0'},

        # middot_sibling_date pattern - House sites with documentquery and middot date separator
        'brownley': {'method': 'middot_sibling_date', 'url_base': 'https://brownley.house.gov', 'doc_type_id': '2519'},
        'emmer': {'method': 'middot_sibling_date', 'url_base': 'https://emmer.house.gov', 'doc_type_id': '2516'},
        'foxx': {'method': 'middot_sibling_date', 'url_base': 'https://foxx.house.gov', 'doc_type_id': '1525'},
        'gosar': {'method': 'middot_sibling_date', 'url_base': 'https://gosar.house.gov', 'doc_type_id': '27'},
        'griffith': {'method': 'middot_sibling_date', 'url_base': 'https://griffith.house.gov', 'doc_type_id': '27'},
        'houlahan': {'method': 'middot_sibling_date', 'url_base': 'https://houlahan.house.gov', 'doc_type_id': '27'},
        'huizenga': {'method': 'middot_sibling_date', 'url_base': 'https://huizenga.house.gov', 'doc_type_id': '27'},
        'jasonsmith': {'method': 'middot_sibling_date', 'url_base': 'https://jasonsmith.house.gov', 'doc_type_id': '27'},
        'mast': {'method': 'middot_sibling_date', 'url_base': 'https://mast.house.gov', 'doc_type_id': '27'},
        'mcgovern': {'method': 'middot_sibling_date', 'url_base': 'https://mcgovern.house.gov', 'doc_type_id': '27'},
        'norcross': {'method': 'middot_sibling_date', 'url_base': 'https://norcross.house.gov', 'doc_type_id': '27'},
        'porter': {'method': 'middot_sibling_date', 'url_base': 'https://porter.house.gov', 'doc_type_id': '27'},
        'schweikert': {'method': 'middot_sibling_date', 'url_base': 'https://schweikert.house.gov', 'doc_type_id': '27'},
        'titus': {'method': 'middot_sibling_date', 'url_base': 'https://titus.house.gov', 'doc_type_id': '27'},

        # news_texthold pattern - House sites with .news-texthold class
        'larsen': {'method': 'news_texthold', 'url_base': 'https://larsen.house.gov', 'doc_type_id': '27'},
        'connolly': {'method': 'news_texthold', 'url_base': 'https://connolly.house.gov', 'doc_type_id': '1952'},
        'tonko': {'method': 'news_texthold', 'url_base': 'https://tonko.house.gov', 'doc_type_id': '27'},

        # et_pb_post pattern - Divi theme sites (Senate)
        'hagerty': {'method': 'et_pb_post', 'url_base': 'https://www.hagerty.senate.gov/press-releases/?et_blog'},
        'budd': {'method': 'et_pb_post', 'url_base': 'https://www.budd.senate.gov/category/news/press-releases/?et_blog'},
        'lummis': {'method': 'et_pb_post', 'url_base': 'https://www.lummis.senate.gov/press-releases/?et_blog'},
        'rubio': {'method': 'et_pb_post', 'url_base': 'https://www.rubio.senate.gov/news/?et_blog'},

        # media_body pattern - House sites with media-body class (200+ members)
        'issa': {'method': 'media_body', 'url_base': 'https://issa.house.gov/media/press-releases'},
        'tenney': {'method': 'media_body', 'url_base': 'https://tenney.house.gov/media/press-releases'},
        'amodei': {'method': 'media_body', 'url_base': 'https://amodei.house.gov/news-releases'},
        'palmer': {'method': 'media_body', 'url_base': 'https://palmer.house.gov/media-center/press-releases'},
        'newhouse': {'method': 'media_body', 'url_base': 'https://newhouse.house.gov/media-center/press-releases'},
        'doggett': {'method': 'media_body', 'url_base': 'https://doggett.house.gov/media/press-releases'},
        'ocasio-cortez': {'method': 'media_body', 'url_base': 'https://ocasio-cortez.house.gov/media/press-releases'},
        'hudson': {'method': 'media_body', 'url_base': 'https://hudson.house.gov/media/press-releases'},
        'davis': {'method': 'media_body', 'url_base': 'https://davis.house.gov/media'},
        'espaillat': {'method': 'media_body', 'url_base': 'https://espaillat.house.gov/media/press-releases'},
        'algreen': {'method': 'media_body', 'url_base': 'https://algreen.house.gov/media/press-releases'},
        'mariodiazbalart': {'method': 'media_body', 'url_base': 'https://mariodiazbalart.house.gov/media-center/press-releases'},
        'biggs': {'method': 'media_body', 'url_base': 'https://biggs.house.gov/media/press-releases'},
        'johnjoyce': {'method': 'media_body', 'url_base': 'https://johnjoyce.house.gov/media/press-releases'},
        'larson': {'method': 'media_body', 'url_base': 'https://larson.house.gov/media-center/press-releases'},
        'kaptur': {'method': 'media_body', 'url_base': 'https://kaptur.house.gov/media-center/press-releases'},
        'benniethompson': {'method': 'media_body', 'url_base': 'https://benniethompson.house.gov/media/press-releases'},
        'walberg': {'method': 'media_body', 'url_base': 'https://walberg.house.gov/media/press-releases'},
        'burchett': {'method': 'media_body', 'url_base': 'https://burchett.house.gov/media/press-releases'},
        'cline': {'method': 'media_body', 'url_base': 'https://cline.house.gov/media/press-releases'},
        'golden': {'method': 'media_body', 'url_base': 'https://golden.house.gov/media/press-releases'},
        'harder': {'method': 'media_body', 'url_base': 'https://harder.house.gov/media/press-releases'},
        'dustyjohnson': {'method': 'media_body', 'url_base': 'https://dustyjohnson.house.gov/media/press-releases'},
        'meuser': {'method': 'media_body', 'url_base': 'https://meuser.house.gov/media/press-releases'},
        'miller': {'method': 'media_body', 'url_base': 'https://miller.house.gov/media/press-releases'},
        'johnrose': {'method': 'media_body', 'url_base': 'https://johnrose.house.gov/media/press-releases'},
        'roy': {'method': 'media_body', 'url_base': 'https://roy.house.gov/media/press-releases'},
        'sherrill': {'method': 'media_body', 'url_base': 'https://sherrill.house.gov/media/press-releases'},
        'steil': {'method': 'media_body', 'url_base': 'https://steil.house.gov/media/press-releases'},
        'schrier': {'method': 'media_body', 'url_base': 'https://schrier.house.gov/media/press-releases'},
        'scalise': {'method': 'media_body', 'url_base': 'https://scalise.house.gov/media/press-releases'},
        'neguse': {'method': 'media_body', 'url_base': 'https://neguse.house.gov/media/press-releases'},
        'boyle': {'method': 'media_body', 'url_base': 'https://boyle.house.gov/media-center/press-releases'},
        'smucker': {'method': 'media_body', 'url_base': 'https://smucker.house.gov/media/press-releases'},
        'waters': {'method': 'media_body', 'url_base': 'https://waters.house.gov/media-center/press-releases'},
        'khanna': {'method': 'media_body', 'url_base': 'https://khanna.house.gov/media/press-releases'},
        'pelosi': {'method': 'media_body', 'url_base': 'https://pelosi.house.gov/news/press-releases'},
        'cherfilus-mccormick': {'method': 'media_body', 'url_base': 'https://cherfilus-mccormick.house.gov/media/press-releases'},
        'shontelbrown': {'method': 'media_body', 'url_base': 'https://shontelbrown.house.gov/media/press-releases'},
        'stansbury': {'method': 'media_body', 'url_base': 'https://stansbury.house.gov/media/press-releases'},
        'troycarter': {'method': 'media_body', 'url_base': 'https://troycarter.house.gov/media/press-releases'},
        'letlow': {'method': 'media_body', 'url_base': 'https://letlow.house.gov/media/press-releases'},
        'matsui': {'method': 'media_body', 'url_base': 'https://matsui.house.gov/media'},
        'harris': {'method': 'media_body', 'url_base': 'https://harris.house.gov/media/press-releases'},
        'wagner': {'method': 'media_body', 'url_base': 'https://wagner.house.gov/media-center/press-releases'},
        'pappas': {'method': 'media_body', 'url_base': 'https://pappas.house.gov/media/press-releases'},
        'crow': {'method': 'media_body', 'url_base': 'https://crow.house.gov/media/press-releases'},
        'chuygarcia': {'method': 'media_body', 'url_base': 'https://chuygarcia.house.gov/media/press-releases'},
        'omar': {'method': 'media_body', 'url_base': 'https://omar.house.gov/media/press-releases'},
        'underwood': {'method': 'media_body', 'url_base': 'https://underwood.house.gov/media/press-releases'},
        'casten': {'method': 'media_body', 'url_base': 'https://casten.house.gov/media/press-releases'},
        'fleischmann': {'method': 'media_body', 'url_base': 'https://fleischmann.house.gov/media/press-releases'},
        'stevens': {'method': 'media_body', 'url_base': 'https://stevens.house.gov/media/press-releases'},
        'guest': {'method': 'media_body', 'url_base': 'https://guest.house.gov/media/press-releases'},
        'morelle': {'method': 'media_body', 'url_base': 'https://morelle.house.gov/media/press-releases'},
        'beatty': {'method': 'media_body', 'url_base': 'https://beatty.house.gov/media-center/press-releases'},
        'robinkelly': {'method': 'media_body', 'url_base': 'https://robinkelly.house.gov/media-center/press-releases'},
        'moolenaar': {'method': 'media_body', 'url_base': 'https://moolenaar.house.gov/media-center/press-releases'},
        'adams': {'method': 'media_body', 'url_base': 'https://adams.house.gov/media-center/press-releases'},
        'mfume': {'method': 'media_body', 'url_base': 'https://mfume.house.gov/media/press-releases'},
        'tiffany': {'method': 'media_body', 'url_base': 'https://tiffany.house.gov/media/press-releases'},
        'barrymoore': {'method': 'media_body', 'url_base': 'https://barrymoore.house.gov/media/press-releases'},
        'obernolte': {'method': 'media_body', 'url_base': 'https://obernolte.house.gov/media/press-releases'},
        'boebert': {'method': 'media_body', 'url_base': 'https://boebert.house.gov/media/press-releases'},
        'cammack': {'method': 'media_body', 'url_base': 'https://cammack.house.gov/media/press-releases'},
        'salazar': {'method': 'media_body', 'url_base': 'https://salazar.house.gov/media/press-releases'},
        'hinson': {'method': 'media_body', 'url_base': 'https://hinson.house.gov/media/press-releases'},
        'millermeeks': {'method': 'media_body', 'url_base': 'https://millermeeks.house.gov/media/press-releases'},
        'feenstra': {'method': 'media_body', 'url_base': 'https://feenstra.house.gov/media/press-releases'},
        'marymiller': {'method': 'media_body', 'url_base': 'https://marymiller.house.gov/media/press-releases'},
        'mrvan': {'method': 'media_body', 'url_base': 'https://mrvan.house.gov/media/press-releases'},
        'spartz': {'method': 'media_body', 'url_base': 'https://spartz.house.gov/media/press-releases'},
        'mann': {'method': 'media_body', 'url_base': 'https://mann.house.gov/media/press-releases'},
        'garbarino': {'method': 'media_body', 'url_base': 'https://garbarino.house.gov/media/press-releases'},
        'malliotakis': {'method': 'media_body', 'url_base': 'https://malliotakis.house.gov/media/press-releases'},
        'bice': {'method': 'media_body', 'url_base': 'https://bice.house.gov/media/press-releases'},
        'bentz': {'method': 'media_body', 'url_base': 'https://bentz.house.gov/media/press-releases'},
        'mace': {'method': 'media_body', 'url_base': 'https://mace.house.gov/media/press-releases'},
        'harshbarger': {'method': 'media_body', 'url_base': 'https://harshbarger.house.gov/media/press-releases'},
        'blakemoore': {'method': 'media_body', 'url_base': 'https://blakemoore.house.gov/media/press-releases'},
        'fitzgerald': {'method': 'media_body', 'url_base': 'https://fitzgerald.house.gov/media/press-releases'},
        'flood': {'method': 'media_body', 'url_base': 'https://flood.house.gov/media/press-releases'},
        'patryan': {'method': 'media_body', 'url_base': 'https://patryan.house.gov/media/press-releases'},
        'kamlager-dove': {'method': 'media_body', 'url_base': 'https://kamlager-dove.house.gov/media/press-releases'},
        'robertgarcia': {'method': 'media_body', 'url_base': 'https://robertgarcia.house.gov/media/press-releases'},
        'bean': {'method': 'media_body', 'url_base': 'https://bean.house.gov/media/press-releases'},
        'mccormick': {'method': 'media_body', 'url_base': 'https://mccormick.house.gov/media/press-releases'},
        'collins': {'method': 'media_body', 'url_base': 'https://collins.house.gov/media/press-releases'},
        'edwards': {'method': 'media_body', 'url_base': 'https://edwards.house.gov/media/press-releases'},
        'kean': {'method': 'media_body', 'url_base': 'https://kean.house.gov/media/press-releases'},
        'goldman': {'method': 'media_body', 'url_base': 'https://goldman.house.gov/media/press-releases'},
        'langworthy': {'method': 'media_body', 'url_base': 'https://langworthy.house.gov/media/press-releases'},
        'magaziner': {'method': 'media_body', 'url_base': 'https://magaziner.house.gov/media/press-releases'},
        'vanorden': {'method': 'media_body', 'url_base': 'https://vanorden.house.gov/media/press-releases'},
        'hunt': {'method': 'media_body', 'url_base': 'https://hunt.house.gov/media/press-releases'},
        'casar': {'method': 'media_body', 'url_base': 'https://casar.house.gov/media/press-releases'},
        'crockett': {'method': 'media_body', 'url_base': 'https://crockett.house.gov/media/press-releases'},
        'luttrell': {'method': 'media_body', 'url_base': 'https://luttrell.house.gov/media/press-releases'},
        'deluzio': {'method': 'media_body', 'url_base': 'https://deluzio.house.gov/media/press-releases'},
        'lalota': {'method': 'media_body', 'url_base': 'https://lalota.house.gov/media/press-releases'},
        'vasquez': {'method': 'media_body', 'url_base': 'https://vasquez.house.gov/media/press-releases'},
        'scholten': {'method': 'media_body', 'url_base': 'https://scholten.house.gov/media/press-releases'},
        'ivey': {'method': 'media_body', 'url_base': 'https://ivey.house.gov/media/press-releases'},
        'sorensen': {'method': 'media_body', 'url_base': 'https://sorensen.house.gov/media/press-releases'},
        'nunn': {'method': 'media_body', 'url_base': 'https://nunn.house.gov/media/press-releases'},
        'laurellee': {'method': 'media_body', 'url_base': 'https://laurellee.house.gov/media/press-releases'},
        'mills': {'method': 'media_body', 'url_base': 'https://mills.house.gov/media/press-releases'},
        'ciscomani': {'method': 'media_body', 'url_base': 'https://ciscomani.house.gov/media/press-releases'},
        'democraticleader': {'method': 'media_body', 'url_base': 'https://democraticleader.house.gov/media/press-releases'},
        'horsford': {'method': 'media_body', 'url_base': 'https://horsford.house.gov/media/press-releases'},
        'cleaver': {'method': 'media_body', 'url_base': 'https://cleaver.house.gov/media-center/press-releases'},
        'aderholt': {'method': 'media_body', 'url_base': 'https://aderholt.house.gov/media-center/press-releases'},
        'courtney': {'method': 'media_body', 'url_base': 'https://courtney.house.gov/media-center/press-releases'},
        'stauber': {'method': 'media_body', 'url_base': 'https://stauber.house.gov/media/press-releases'},
        'mccaul': {'method': 'media_body', 'url_base': 'https://mccaul.house.gov/media-center/press-releases'},
        'foster': {'method': 'media_body', 'url_base': 'https://foster.house.gov/media/press-releases'},
        'schakowsky': {'method': 'media_body', 'url_base': 'https://schakowsky.house.gov/media/press-releases'},
        'craig': {'method': 'media_body', 'url_base': 'https://craig.house.gov/media/press-releases'},
        'desaulnier': {'method': 'media_body', 'url_base': 'https://desaulnier.house.gov/media-center/press-releases'},
        'murphy': {'method': 'media_body', 'url_base': 'https://murphy.house.gov/media/press-releases'},
        'calvert': {'method': 'media_body', 'url_base': 'https://calvert.house.gov/media/press-releases'},
        'bobbyscott': {'method': 'media_body', 'url_base': 'https://bobbyscott.house.gov/media-center/press-releases'},
        'bilirakis': {'method': 'media_body', 'url_base': 'https://bilirakis.house.gov/media/press-releases'},
        'delauro': {'method': 'media_body', 'url_base': 'https://delauro.house.gov/media-center/press-releases'},
        'norton': {'method': 'media_body', 'url_base': 'https://norton.house.gov/media/press-releases'},
        'mikethompson': {'method': 'media_body', 'url_base': 'https://mikethompson.house.gov/newsroom/press-releases'},
        'degette': {'method': 'media_body', 'url_base': 'https://degette.house.gov/media-center/press-releases'},
        'ruiz': {'method': 'media_body', 'url_base': 'https://ruiz.house.gov/media-center/press-releases'},
        'sherman': {'method': 'media_body', 'url_base': 'https://sherman.house.gov/media-center/press-releases'},
        'quigley': {'method': 'media_body', 'url_base': 'https://quigley.house.gov/media-center/press-releases'},
        'swalwell': {'method': 'media_body', 'url_base': 'https://swalwell.house.gov/media-center/press-releases'},
        'panetta': {'method': 'media_body', 'url_base': 'https://panetta.house.gov/media/press-releases'},
        'schneider': {'method': 'media_body', 'url_base': 'https://schneider.house.gov/media/press-releases'},
        'dankildee': {'method': 'media_body', 'url_base': 'https://dankildee.house.gov/media/press-releases'},
        'sylviagarcia': {'method': 'media_body', 'url_base': 'https://sylviagarcia.house.gov/media/press-releases'},
        'susielee': {'method': 'media_body', 'url_base': 'https://susielee.house.gov/media/press-releases'},
        'amo': {'method': 'media_body', 'url_base': 'https://amo.house.gov/press-releases'},
        'mcclellan': {'method': 'media_body', 'url_base': 'https://mcclellan.house.gov/media/press-releases'},
        'rulli': {'method': 'media_body', 'url_base': 'https://rulli.house.gov/media/press-releases'},
        'suozzi': {'method': 'media_body', 'url_base': 'https://suozzi.house.gov/media/press-releases'},
        'fong': {'method': 'media_body', 'url_base': 'https://fong.house.gov/media/press-releases'},
        'lopez': {'method': 'media_body', 'url_base': 'https://lopez.house.gov/media/press-releases'},
        'mciver': {'method': 'media_body', 'url_base': 'https://mciver.house.gov/media/press-releases'},
        'wied': {'method': 'media_body', 'url_base': 'https://wied.house.gov/media/press-releases'},
        'ericaleecarter': {'method': 'media_body', 'url_base': 'https://ericaleecarter.house.gov/media/press-releases'},
        'moulton': {'method': 'media_body', 'url_base': 'https://moulton.house.gov/news/press-releases'},
        'nehls': {'method': 'media_body', 'url_base': 'https://nehls.house.gov/media'},
        'meng': {'method': 'media_body', 'url_base': 'https://meng.house.gov/media-center/press-releases'},
        'lindasanchez': {'method': 'media_body', 'url_base': 'https://lindasanchez.house.gov/media-center/press-releases'},
        'lamalfa': {'method': 'media_body', 'url_base': 'https://lamalfa.house.gov/media-center/press-releases'},
        'dondavis': {'method': 'media_body', 'url_base': 'https://dondavis.house.gov/media/press-releases'},
        'strong': {'method': 'media_body', 'url_base': 'https://strong.house.gov/media/press-releases'},
        'chu': {'method': 'media_body', 'url_base': 'https://chu.house.gov/media-center/press-releases'},
        'lieu': {'method': 'media_body', 'url_base': 'https://lieu.house.gov/media-center/press-releases'},
        'joewilson': {'method': 'media_body', 'url_base': 'https://joewilson.house.gov/media/press-releases'},
        'zinke': {'method': 'media_body', 'url_base': 'https://zinke.house.gov/media/press-releases'},
        'rutherford': {'method': 'media_body', 'url_base': 'https://rutherford.house.gov/media/press-releases'},
        'veasey': {'method': 'media_body', 'url_base': 'https://veasey.house.gov/media-center/press-releases'},
        'garamendi': {'method': 'media_body', 'url_base': 'https://garamendi.house.gov/media/press-releases'},
        'kustoff': {'method': 'media_body', 'url_base': 'https://kustoff.house.gov/media/press-releases'},
        'gonzalez': {'method': 'media_body', 'url_base': 'https://gonzalez.house.gov/media/press-releases'},
        'costa': {'method': 'media_body', 'url_base': 'https://costa.house.gov/media/press-releases'},
        'houchin': {'method': 'media_body', 'url_base': 'https://houchin.house.gov/media/press-releases'},
        'williams': {'method': 'media_body', 'url_base': 'https://williams.house.gov/media-center/press-releases'},
        'menendez': {'method': 'media_body', 'url_base': 'https://menendez.house.gov/media/press-releases'},
        'pocan': {'method': 'media_body', 'url_base': 'https://pocan.house.gov/media-center/press-releases'},
        'ogles': {'method': 'media_body', 'url_base': 'https://ogles.house.gov/media/press-releases'},
        'velazquez': {'method': 'media_body', 'url_base': 'https://velazquez.house.gov/media-center/press-releases'},
        'bonamici': {'method': 'media_body', 'url_base': 'https://bonamici.house.gov/media/press-releases'},
        'keithself': {'method': 'media_body', 'url_base': 'https://keithself.house.gov/media/press-releases'},
        'bishop': {'method': 'media_body', 'url_base': 'https://bishop.house.gov/media-center/press-releases'},
        'hoyer': {'method': 'media_body', 'url_base': 'https://hoyer.house.gov/media'},
        'burlison': {'method': 'media_body', 'url_base': 'https://burlison.house.gov/media/press-releases'},
        'jonathanjackson': {'method': 'media_body', 'url_base': 'https://jonathanjackson.house.gov/media/press-releases'},
        'davids': {'method': 'media_body', 'url_base': 'https://davids.house.gov/media/press-releases'},
        'mccollum': {'method': 'media_body', 'url_base': 'https://mccollum.house.gov/media/press-releases'},
        'adamsmith': {'method': 'media_body', 'url_base': 'https://adamsmith.house.gov/news/press-releases'},
        'hankjohnson': {'method': 'media_body', 'url_base': 'https://hankjohnson.house.gov/media-center/press-releases'},
        'evans': {'method': 'media_body', 'url_base': 'https://evans.house.gov/media/press-releases'},
        'salinas': {'method': 'media_body', 'url_base': 'https://salinas.house.gov/media/press-releases'},
        'pallone': {'method': 'media_body', 'url_base': 'https://pallone.house.gov/media/press-releases'},
        'ramirez': {'method': 'media_body', 'url_base': 'https://ramirez.house.gov/media/press-releases'},
        'graves': {'method': 'media_body', 'url_base': 'https://graves.house.gov/media/press-releases'},
        'cole': {'method': 'media_body', 'url_base': 'https://cole.house.gov/media-center/press-releases'},
        'jordan': {'method': 'media_body', 'url_base': 'https://jordan.house.gov/media/press-releases'},
        'hageman': {'method': 'media_body', 'url_base': 'https://hageman.house.gov/media/press-releases'},
        'figures': {'method': 'media_body', 'url_base': 'https://figures.house.gov/media'},
        'begich': {'method': 'media_body', 'url_base': 'https://begich.house.gov/media/press-releases'},
        'ansari': {'method': 'media_body', 'url_base': 'https://ansari.house.gov/media/press-releases'},
        'simon': {'method': 'media_body', 'url_base': 'https://simon.house.gov/media/press-releases'},
        'gray': {'method': 'media_body', 'url_base': 'https://gray.house.gov/media/press-releases'},
        'liccardo': {'method': 'media_body', 'url_base': 'https://liccardo.house.gov/media/press-releases'},
        'rivas': {'method': 'media_body', 'url_base': 'https://rivas.house.gov/media/press-releases'},
        'friedman': {'method': 'media_body', 'url_base': 'https://friedman.house.gov/media/press-releases'},
        'tran': {'method': 'media_body', 'url_base': 'https://tran.house.gov/media/press-releases'},
        'min': {'method': 'media_body', 'url_base': 'https://min.house.gov/media/press-releases'},
        'hurd': {'method': 'media_body', 'url_base': 'https://hurd.house.gov/media/press-releases'},
        'crank': {'method': 'media_body', 'url_base': 'https://crank.house.gov/media/press-releases'},
        'gabeevans': {'method': 'media_body', 'url_base': 'https://gabeevans.house.gov/media/press-releases'},
        'mcbride': {'method': 'media_body', 'url_base': 'https://mcbride.house.gov/media/press-releases'},
        'haridopolos': {'method': 'media_body', 'url_base': 'https://haridopolos.house.gov/media/press-releases'},
        'jack': {'method': 'media_body', 'url_base': 'https://jack.house.gov/media/press-releases'},
        'stutzman': {'method': 'media_body', 'url_base': 'https://stutzman.house.gov/media/press-releases'},
        'shreve': {'method': 'media_body', 'url_base': 'https://shreve.house.gov/media/press-releases'},
        'fields': {'method': 'media_body', 'url_base': 'https://fields.house.gov/media/press-releases'},
        'olszewski': {'method': 'media_body', 'url_base': 'https://olszewski.house.gov/media/press-releases'},
        'elfreth': {'method': 'media_body', 'url_base': 'https://elfreth.house.gov/media/press-releases'},
        'mcclaindelaney': {'method': 'media_body', 'url_base': 'https://mcclaindelaney.house.gov/media/press-releases'},
        'mcdonaldrivet': {'method': 'media_body', 'url_base': 'https://mcdonaldrivet.house.gov/media/press-releases'},
        'barrett': {'method': 'media_body', 'url_base': 'https://barrett.house.gov/media/press-releases'},
        'morrison': {'method': 'media_body', 'url_base': 'https://morrison.house.gov/media/press-releases'},
        'bell': {'method': 'media_body', 'url_base': 'https://bell.house.gov/media/press-releases'},
        'downing': {'method': 'media_body', 'url_base': 'https://downing.house.gov/media/press-releases'},
        'goodlander': {'method': 'media_body', 'url_base': 'https://goodlander.house.gov/media/press-releases'},
        'pou': {'method': 'media_body', 'url_base': 'https://pou.house.gov/media/press-releases'},
        'gillen': {'method': 'media_body', 'url_base': 'https://gillen.house.gov/media/press-releases'},
        'latimer': {'method': 'media_body', 'url_base': 'https://latimer.house.gov/media/press-releases'},
        'riley': {'method': 'media_body', 'url_base': 'https://riley.house.gov/media/press-releases'},
        'mannion': {'method': 'media_body', 'url_base': 'https://mannion.house.gov/media/press-releases'},
        'mcdowell': {'method': 'media_body', 'url_base': 'https://mcdowell.house.gov/media/press-releases'},
        'markharris': {'method': 'media_body', 'url_base': 'https://markharris.house.gov/media/press-releases'},
        'harrigan': {'method': 'media_body', 'url_base': 'https://harrigan.house.gov/media/press-releases'},
        'knott': {'method': 'media_body', 'url_base': 'https://knott.house.gov/media/press-releases'},
        'timmoore': {'method': 'media_body', 'url_base': 'https://timmoore.house.gov/media/press-releases'},
        'fedorchak': {'method': 'media_body', 'url_base': 'https://fedorchak.house.gov/media/press-releases'},
        'king-hinds': {'method': 'media_body', 'url_base': 'https://king-hinds.house.gov/media'},
        'taylor': {'method': 'media_body', 'url_base': 'https://taylor.house.gov/media/press-releases'},
        'dexter': {'method': 'media_body', 'url_base': 'https://dexter.house.gov/media/press-releases'},
        'bynum': {'method': 'media_body', 'url_base': 'https://bynum.house.gov/media/press-releases'},
        'mackenzie': {'method': 'media_body', 'url_base': 'https://mackenzie.house.gov/media/press-releases'},
        'bresnahan': {'method': 'media_body', 'url_base': 'https://bresnahan.house.gov/media'},
        'hernandez': {'method': 'media_body', 'url_base': 'https://hernandez.house.gov/media/press-releases'},
        'sheribiggs': {'method': 'media_body', 'url_base': 'https://sheribiggs.house.gov/media/press-releases'},
        'craiggoldman': {'method': 'media_body', 'url_base': 'https://craiggoldman.house.gov/media/press-releases'},
        'sylvesterturner': {'method': 'media_body', 'url_base': 'https://sylvesterturner.house.gov/media/press-releases'},
        'gill': {'method': 'media_body', 'url_base': 'https://gill.house.gov/media/press-releases'},
        'juliejohnson': {'method': 'media_body', 'url_base': 'https://juliejohnson.house.gov/media/press-releases'},
        'mcguire': {'method': 'media_body', 'url_base': 'https://mcguire.house.gov/media/press-releases'},
        'vindman': {'method': 'media_body', 'url_base': 'https://vindman.house.gov/media/press-releases'},
        'subramanyam': {'method': 'media_body', 'url_base': 'https://subramanyam.house.gov/media/press-releases'},
        'baumgartner': {'method': 'media_body', 'url_base': 'https://baumgartner.house.gov/media/press-releases'},
        'randall': {'method': 'media_body', 'url_base': 'https://randall.house.gov/media/press-releases'},
        'rileymoore': {'method': 'media_body', 'url_base': 'https://rileymoore.house.gov/media/press-releases'},
    }
    
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
        
        # Get the generic method
        method = getattr(cls, method_name)
        
        # All generic methods accept urls and page
        return method([url_base], page)
    
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
        return cls.run_scraper('crapo', page)

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
        return cls.run_scraper('timscott', page)
        
    @classmethod
    def angusking(cls, page=1):
        """Scrape Senator Angus King's press releases."""
        results = []
        url = f"https://www.king.senate.gov/newsroom/press-releases/table?pagenum_rs={page}"
        doc = cls.open_html(url)
        if not doc:
            return []

        rows = doc.select('.press-browser__item-row')
        for row in rows:
            links = row.select('a')
            if not links:
                continue

            link = links[0]
            date = None
            date_cell = row.select_one('td.press-browser__date')
            if date_cell:
                time_elem = date_cell.find('time')
                if time_elem and time_elem.get('datetime'):
                    date = time_elem.get('datetime')

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
        return cls.run_scraper('barrasso', page)
    
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

    @classmethod
    def middot_sibling_date(cls, urls=None, page=1):
        """
        Scrape press releases from House sites using documentquery with middot date pattern.

        This pattern is used by House member sites that display press releases with
        a middot separator before the date text.

        Args:
            urls: List of (domain, doc_type_id) tuples to scrape
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain
        """
        results = []
        if urls is None:
            # Collect all URLs from SCRAPER_CONFIG where method='middot_sibling_date'
            urls = [
                (config['url_base'].split('/')[2], config.get('doc_type_id', '27'))
                for name, config in cls.SCRAPER_CONFIG.items()
                if config['method'] == 'middot_sibling_date'
            ]

        for domain, doc_type_id in urls:
            url = f"https://{domain}/news/documentquery.aspx?DocumentTypeID={doc_type_id}&Page={page}"

            doc = cls.open_html(url)
            if not doc:
                continue

            articles = doc.select("article")
            for row in articles:
                link = row.select_one("h2 a")
                if not link:
                    continue

                date = None
                date_elem = row.select_one("span.middot")
                if date_elem and date_elem.next_sibling:
                    date_text = date_elem.next_sibling.strip()
                    date_formats = ["%m/%d/%Y", "%m/%d/%y", "%B %d, %Y"]
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
                    full_url = f"https://{domain}/news/{href}"

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
    def news_texthold(cls, urls=None, page=1):
        """
        Scrape press releases from House sites using news-texthold pattern.

        This pattern is used by House member sites that display press releases
        in a .news-texthold container.

        Args:
            urls: List of (domain, doc_type_id) tuples to scrape
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain
        """
        results = []
        if urls is None:
            urls = [
                (config['url_base'].split('/')[2], config.get('doc_type_id', '27'))
                for name, config in cls.SCRAPER_CONFIG.items()
                if config['method'] == 'news_texthold'
            ]

        for domain, doc_type_id in urls:
            url = f"https://{domain}/news/documentquery.aspx?DocumentTypeID={doc_type_id}&Page={page}"

            doc = cls.open_html(url)
            if not doc:
                continue

            news_holds = doc.select('.news-texthold')
            for row in news_holds:
                link = row.select_one('h2 a')
                if not link:
                    continue

                time_elem = row.select_one('time')
                date = None
                if time_elem:
                    date_text = time_elem.text.strip()
                    try:
                        date = datetime.datetime.strptime(date_text, "%B %d, %Y").date()
                    except ValueError:
                        pass

                # Handle relative URL
                href = link.get('href')
                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://{domain}/news/{href}"

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
    def et_pb_post(cls, urls=None, page=1):
        """
        Scrape press releases from sites using Divi theme (et_pb_post pattern).

        This pattern is used by Senate sites built with the Divi theme that display
        press releases in article.et_pb_post elements.

        Args:
            urls: List of URL bases to scrape
            page: Page number for pagination (default: 1)

        Returns:
            List of dictionaries with keys: source, url, title, date, domain
        """
        results = []
        if urls is None:
            urls = [
                config['url_base']
                for config in cls.SCRAPER_CONFIG.values()
                if config['method'] == 'et_pb_post'
            ]

        for url_base in urls:
            parsed_url = urlparse(url_base)
            domain = parsed_url.netloc

            # Handle different URL structures for pagination
            if '?et_blog' in url_base or '/?et_blog' in url_base:
                # URL like /press-releases/?et_blog
                url = url_base.replace(f'/page/{page-1}/', f'/page/{page}/') if f'/page/' in url_base else url_base.replace('?et_blog', f'/page/{page}/?et_blog')
            elif url_base.endswith('/'):
                url = f"{url_base}page/{page}/"
            else:
                url = f"{url_base}/page/{page}/"

            doc = cls.open_html(url)
            if not doc:
                continue

            posts = doc.select("article.et_pb_post")
            for row in posts:
                # Try h2 a first, then h3 a
                link = row.select_one("h2 a") or row.select_one("h3 a")
                if not link:
                    continue

                date_span = row.select_one("p span.published") or row.select_one("span.published")
                date = None
                if date_span:
                    try:
                        date = datetime.datetime.strptime(date_span.text.strip(), "%B %d, %Y").date()
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

    # Individual member scraper methods
    
    @classmethod
    def tillis(cls, page=1):
        """Scrape Senator Tillis's press releases."""
        return cls.run_scraper('tillis', page)
    
    @classmethod
    def wicker(cls, page=1):
        """Scrape Senator Wicker's press releases."""
        return cls.run_scraper('wicker', page)
    
    @classmethod
    def moran(cls, page=1):
        """Scrape Senator Moran's press releases."""
        return cls.run_scraper('moran', page)
    
    @classmethod
    def boozman(cls, page=1):
        """Scrape Senator Boozman's press releases."""
        return cls.run_scraper('boozman', page)
    
    @classmethod
    def thune(cls, page=1):
        """Scrape Senator Thune's press releases."""
        return cls.run_scraper('thune', page)
    
    @classmethod
    def murphy(cls, page=1):
        """Scrape Congressman Murphy's press releases."""
        return cls.run_scraper('murphy', page)

    @classmethod
    def chrismurphy(cls, page=1):
        """Scrape Senator Chris Murphy's press releases."""
        return cls.run_scraper('chrismurphy', page)
    
    @classmethod
    def markey(cls, page=1):
        """Scrape Senator Markey's press releases."""
        return cls.run_scraper('markey', page)
    
    @classmethod
    def cotton(cls, page=1):
        """Scrape Senator Cotton's press releases."""
        return cls.run_scraper('cotton', page)
    
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
        return cls.run_scraper('cassidy', page)
    
    @classmethod
    def britt(cls, page=1):
        """Scrape Senator Britt's press releases."""
        return cls.run_scraper('britt', page)
    
    @classmethod
    def toddyoung(cls, page=1):
        """Scrape Senator Todd Young's press releases."""
        return cls.run_scraper('toddyoung', page)
    
    @classmethod
    def markkelly(cls, page=1):
        """Scrape Senator Mark Kelly's press releases."""
        return cls.run_scraper('markkelly', page)
    
    @classmethod
    def hagerty(cls, page=1):
        """Scrape Senator Hagerty's press releases."""
        return cls.run_scraper('hagerty', page)
    
    @classmethod
    def budd(cls, page=1):
        """Scrape Senator Budd's press releases."""
        return cls.run_scraper('budd', page)
    
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
        return cls.run_scraper('lummis', page)
    
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
        return cls.run_scraper('rubio', page)
    
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
        return cls.run_scraper('garypeters', page)
    
    @classmethod
    def jackreed(cls, page=1):
        """Scrape Senator Jack Reed's press releases."""
        return cls.run_scraper('jackreed', page)
    
    @classmethod
    def rounds(cls, page=1):
        """Scrape Senator Rounds's press releases."""
        return cls.run_scraper('rounds', page)
    
    @classmethod
    def kaine(cls, page=1):
        """Scrape Senator Kaine's press releases."""
        return cls.run_scraper('kaine', page)
    
    @classmethod
    def blackburn(cls, page=1):
        """Scrape Senator Blackburn's press releases."""
        return cls.run_scraper('blackburn', page)
    
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
        return cls.run_scraper('heinrich', page)
    
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
        return cls.run_scraper('larsen', page)
    
    @classmethod
    def connolly(cls, page=1):
        """Scrape Congressman Connolly's press releases."""
        return cls.run_scraper('connolly', page)
    
    @classmethod
    def tonko(cls, page=1):
        """Scrape Congressman Tonko's press releases."""
        return cls.run_scraper('tonko', page)
    
    @classmethod
    def aguilar(cls, page=1):
        """Scrape Congressman Aguilar's press releases."""
        return cls.run_scraper('aguilar', page)

    @classmethod
    def bergman(cls, page=1):
        """Scrape Congressman Bergman's press releases."""
        return cls.run_scraper('bergman', page)
    
    @classmethod
    def brownley(cls, page=1):
        """Scrape Congresswoman Brownley's press releases."""
        return cls.run_scraper('brownley', page)
    
    @classmethod
    def cantwell(cls, page=1):
        """Scrape Senator Cantwell's press releases."""
        return cls.run_scraper('cantwell', page)
    
    @classmethod
    def capito(cls, page=1):
        """Scrape Senator Capito's press releases."""
        return cls.run_scraper('capito', page)
    
    @classmethod
    def carey(cls, page=1):
        """Scrape Congressman Carey's press releases."""
        return cls.run_scraper('carey', page)
    
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
        return cls.run_scraper('cortezmasto', page)
    
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
        return cls.run_scraper('cruz', page)
    
    @classmethod
    def daines(cls, page=1):
        """Scrape Senator Daines's press releases."""
        return cls.run_scraper('daines', page)
    
    @classmethod
    def duckworth(cls, page=1):
        """Scrape Senator Duckworth's press releases."""
        return cls.run_scraper('duckworth', page)
    
    @classmethod
    def ellzey(cls, page=1):
        """Scrape Congressman Ellzey's press releases."""
        return cls.run_scraper('ellzey', page)
    
    @classmethod
    def emmer(cls, page=1):
        """Scrape Congressman Emmer's press releases."""
        return cls.run_scraper('emmer', page)
    
    @classmethod
    def fetterman(cls, page=1):
        """Scrape Senator Fetterman's press releases."""
        return cls.run_scraper('fetterman', page)
    
    @classmethod
    def foxx(cls, page=1):
        """Scrape Congresswoman Foxx's press releases."""
        return cls.run_scraper('foxx', page)
    
    @classmethod
    def gimenez(cls, page=1):
        """Scrape Congressman Gimenez's press releases."""
        return cls.run_scraper('gimenez', page)
    
    @classmethod
    def gosar(cls, page=1):
        """Scrape Congressman Gosar's press releases."""
        return cls.run_scraper('gosar', page)
    
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
        return cls.run_scraper('griffith', page)
    
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
        return cls.run_scraper('hassan', page)
    
    @classmethod
    def houlahan(cls, page=1):
        """Scrape Congresswoman Houlahan's press releases."""
        return cls.run_scraper('houlahan', page)
    
    @classmethod
    def huizenga(cls, page=1):
        """Scrape Congressman Huizenga's press releases."""
        return cls.run_scraper('huizenga', page)
    
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
        return cls.run_scraper('jasonsmith', page)
    
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
        return cls.run_scraper('lujan', page)
    
    @classmethod
    def mast(cls, page=1):
        """Scrape Congressman Mast's press releases."""
        return cls.run_scraper('mast', page)
    
    @classmethod
    def mcgovern(cls, page=1):
        """Scrape Congressman McGovern's press releases."""
        return cls.run_scraper('mcgovern', page)
    
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
        """Scrape Mullin's press releases."""
        results = []
        domain = 'www.mullin.senate.gov'
        url = f"https://{domain}/newsroom/press-releases?jsf=jet-engine:press-list&pagenum={page}"

        doc = cls.open_html(url)
        if not doc:
            return []

        # Find all individual press release items
        items = doc.select('.jet-listing-grid__item')

        for item in items:
            link = item.select_one('a')
            if not link:
                continue

            # Extract data
            title = link.text.strip()
            href = link.get('href')

            # Handle relative URLs
            if not href.startswith('http'):
                href = f"https://{domain}{href}"

            # Extract date
            date_elem = item.select_one('span.elementor-post-info__item--type-date')
            date = None
            if date_elem:
                time_elem = date_elem.select_one('time')
                if time_elem:
                    date_text = time_elem.text.strip()
                    try:
                        date = datetime.datetime.strptime(date_text, "%m.%d.%y").date()
                    except ValueError:
                        pass  # Date parsing failed, leave as None

            result = {
                'source': url,
                'url': href,
                'title': title,
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
        return cls.run_scraper('norcross', page)
    
    @classmethod
    def ossoff(cls, page=1):
        """Scrape Senator Ossoff's press releases."""
        return cls.run_scraper('ossoff', page)
    
    @classmethod
    def padilla(cls, page=1):
        """Scrape Senator Padilla's press releases."""
        return cls.run_scraper('padilla', page)
    
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
        return cls.run_scraper('porter', page)
    
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
        return cls.run_scraper('rosen', page)
    
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
        return cls.run_scraper('schweikert', page)
    
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
        return cls.run_scraper('titus', page)
    
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
        return cls.run_scraper('tester', page)
    
    @classmethod
    def sherrod_brown(cls, page=1):
        """Scrape Senator Sherrod Brown's press releases."""
        return cls.run_scraper('sherrod_brown', page)
    
    @classmethod
    def durbin(cls, page=1):
        """Scrape Senator Durbin's press releases."""
        return cls.run_scraper('durbin', page)
    
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
        return cls.run_scraper('hirono', page)
    
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