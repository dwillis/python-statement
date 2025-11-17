#!/usr/bin/env python3
"""
Fetch current legislators and discover their RSS feeds or press releases.
"""

import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from python_statement.statement import Feed, Scraper, Utils

def fetch_legislators():
    """Fetch current legislators from unitedstates.github.io."""
    url = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching legislators: {e}")
        return []

def extract_legislator_info(legislator):
    """Extract relevant information from legislator data."""
    info = {
        'bioguide_id': legislator['id'].get('bioguide', ''),
        'first_name': legislator['name'].get('first', ''),
        'last_name': legislator['name'].get('last', ''),
        'full_name': f"{legislator['name'].get('first', '')} {legislator['name'].get('last', '')}",
        'state': legislator['terms'][-1].get('state', ''),
        'party': legislator['terms'][-1].get('party', ''),
        'type': legislator['terms'][-1].get('type', ''),  # sen or rep
        'urls': []
    }

    # Get official URL
    if 'url' in legislator['terms'][-1]:
        info['urls'].append(legislator['terms'][-1]['url'])

    # Get contact form URL (sometimes contains different domain)
    if 'contact_form' in legislator['terms'][-1]:
        info['urls'].append(legislator['terms'][-1]['contact_form'])

    return info

def discover_rss_feeds(url, timeout=10):
    """
    Attempt to discover RSS feeds from a website.
    Returns a list of potential RSS feed URLs.
    """
    rss_feeds = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Look for RSS/Atom feed links in <link> tags
        for link in soup.find_all('link', type=['application/rss+xml', 'application/atom+xml']):
            feed_url = link.get('href')
            if feed_url:
                rss_feeds.append(urljoin(url, feed_url))

        # Look for common RSS feed links in <a> tags
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            if any(keyword in href for keyword in ['rss', 'feed', 'atom']):
                if href.endswith('.xml') or 'rss' in href or 'feed' in href or 'atom' in href:
                    rss_feeds.append(urljoin(url, link['href']))

        # Try common RSS feed paths
        domain = urlparse(url).netloc
        scheme = urlparse(url).scheme
        common_paths = [
            '/rss.xml',
            '/feed',
            '/feed/',
            '/feeds/press.xml',
            '/feeds/news.xml',
            '/media/rss.xml',
            '/news/rss.xml'
        ]

        for path in common_paths:
            potential_feed = f"{scheme}://{domain}{path}"
            # Quick check if URL is accessible
            try:
                head_response = requests.head(potential_feed, headers=headers, timeout=5, allow_redirects=True)
                if head_response.status_code == 200:
                    content_type = head_response.headers.get('Content-Type', '')
                    if 'xml' in content_type or 'rss' in content_type or 'atom' in content_type:
                        rss_feeds.append(potential_feed)
            except:
                pass

    except Exception as e:
        print(f"  Error discovering RSS feeds from {url}: {e}")

    # Remove duplicates
    return list(set(rss_feeds))

def discover_press_release_url(url, timeout=10):
    """
    Attempt to discover press release page URL.
    Returns a potential press release URL or None.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Look for links containing press release keywords
        keywords = ['press-release', 'press release', 'news release', 'media', 'newsroom', 'press']

        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text().lower()

            # Check if link text or href contains press release keywords
            if any(keyword in href for keyword in keywords) or any(keyword in text for keyword in keywords):
                # Prioritize links with "press" in them
                if 'press' in href or 'press' in text:
                    full_url = urljoin(url, link['href'])
                    return full_url

    except Exception as e:
        print(f"  Error discovering press release URL from {url}: {e}")

    return None

def scrape_with_known_scrapers(legislator_info):
    """
    Try to use known scrapers for specific legislators.
    Returns list of press releases or empty list.
    """
    results = []
    last_name_lower = legislator_info['last_name'].lower()

    # Map of known scrapers by last name
    scraper_map = {
        'crapo': Scraper.crapo,
        'shaheen': Scraper.shaheen,
        'scott': Scraper.timscott if legislator_info['first_name'].lower() == 'tim' else None,
        'king': Scraper.angusking if legislator_info['first_name'].lower() == 'angus' else None,
        'bera': Scraper.bera,
        'meeks': Scraper.meeks,
        'steube': Scraper.steube,
        'barragan': Scraper.barragan,
        'castor': Scraper.castor,
        'marshall': Scraper.marshall,
        'hawley': Scraper.hawley,
        'barrasso': Scraper.barrasso,
        'sykes': Scraper.sykes,
    }

    scraper_func = scraper_map.get(last_name_lower)
    if scraper_func:
        try:
            print(f"  Using known scraper for {legislator_info['full_name']}")
            results = scraper_func()
            return results
        except Exception as e:
            print(f"  Error using known scraper: {e}")

    return []

def generic_press_release_scraper(url, domain):
    """
    Attempt to scrape press releases using common patterns.
    Returns list of press releases or empty list.
    """
    results = []
    doc = Scraper.open_html(url)
    if not doc:
        return []

    # Try different common patterns

    # Pattern 1: ArticleBlock
    blocks = doc.select(".ArticleBlock")
    if blocks:
        for block in blocks[:10]:  # Limit to first 10
            link = block.select_one('a')
            if not link:
                continue

            title = ''
            if block.select_one('h2'):
                title = block.select_one('h2').text.strip()
            elif block.select_one('h3'):
                title = block.select_one('h3').text.strip()
            elif link:
                title = link.text.strip()

            result = {
                'source': url,
                'url': Utils.absolute_link(url, link.get('href')),
                'title': title,
                'domain': domain
            }
            results.append(result)
        return results

    # Pattern 2: Media body
    media_bodies = doc.find_all("div", {"class": "media-body"})
    if media_bodies:
        for row in media_bodies[:10]:
            link = row.find('a')
            if not link:
                continue

            result = {
                'source': url,
                'url': Utils.absolute_link(url, link.get('href')),
                'title': link.text.strip(),
                'domain': domain
            }
            results.append(result)
        return results

    # Pattern 3: Article tags
    articles = doc.select("article")
    if articles:
        for article in articles[:10]:
            link = article.select_one('a')
            if not link:
                continue

            title = ''
            if article.select_one('h2'):
                title = article.select_one('h2').text.strip()
            elif article.select_one('h3'):
                title = article.select_one('h3').text.strip()
            else:
                title = link.text.strip()

            result = {
                'source': url,
                'url': Utils.absolute_link(url, link.get('href')),
                'title': title,
                'domain': domain
            }
            results.append(result)
        return results

    # Pattern 4: Common list patterns
    for selector in ['.press-release', '.news-item', '.post', '.views-row']:
        items = doc.select(selector)
        if items:
            for item in items[:10]:
                link = item.select_one('a')
                if not link:
                    continue

                title = ''
                if item.select_one('h2'):
                    title = item.select_one('h2').text.strip()
                elif item.select_one('h3'):
                    title = item.select_one('h3').text.strip()
                elif item.select_one('h4'):
                    title = item.select_one('h4').text.strip()
                else:
                    title = link.text.strip()

                result = {
                    'source': url,
                    'url': Utils.absolute_link(url, link.get('href')),
                    'title': title,
                    'domain': domain
                }
                results.append(result)
            return results

    return results

def process_legislator(legislator_info):
    """
    Process a single legislator: discover RSS or scrape press releases.
    Returns list of press releases with legislator info.
    """
    print(f"\nProcessing: {legislator_info['full_name']} ({legislator_info['party']}-{legislator_info['state']})")

    all_results = []

    # First, try known scrapers
    known_results = scrape_with_known_scrapers(legislator_info)
    if known_results:
        for result in known_results[:5]:  # Limit to 5 most recent
            result['legislator'] = {
                'bioguide_id': legislator_info['bioguide_id'],
                'name': legislator_info['full_name'],
                'state': legislator_info['state'],
                'party': legislator_info['party']
            }
            all_results.append(result)
        print(f"  Found {len(all_results)} press releases using known scraper")
        return all_results

    # Try each URL
    for base_url in legislator_info['urls']:
        if not base_url:
            continue

        print(f"  Checking: {base_url}")

        # Try to discover RSS feeds
        rss_feeds = discover_rss_feeds(base_url)

        if rss_feeds:
            print(f"  Found {len(rss_feeds)} potential RSS feed(s)")
            for feed_url in rss_feeds[:2]:  # Try first 2 feeds
                print(f"  Trying RSS feed: {feed_url}")
                try:
                    feed_results = Feed.from_rss(feed_url)
                    if feed_results:
                        print(f"  Successfully parsed RSS feed with {len(feed_results)} items")
                        for result in feed_results[:5]:  # Limit to 5 most recent
                            result['legislator'] = {
                                'bioguide_id': legislator_info['bioguide_id'],
                                'name': legislator_info['full_name'],
                                'state': legislator_info['state'],
                                'party': legislator_info['party']
                            }
                            all_results.append(result)
                        break  # Stop after first successful RSS feed
                except Exception as e:
                    print(f"  Error parsing RSS feed {feed_url}: {e}")

        # If we found RSS results, we're done
        if all_results:
            break

        # Otherwise, try to find press release page
        press_url = discover_press_release_url(base_url)
        if press_url:
            print(f"  Found press release page: {press_url}")
            try:
                domain = urlparse(press_url).netloc
                scrape_results = generic_press_release_scraper(press_url, domain)
                if scrape_results:
                    print(f"  Successfully scraped {len(scrape_results)} press releases")
                    for result in scrape_results[:5]:  # Limit to 5 most recent
                        result['legislator'] = {
                            'bioguide_id': legislator_info['bioguide_id'],
                            'name': legislator_info['full_name'],
                            'state': legislator_info['state'],
                            'party': legislator_info['party']
                        }
                        all_results.append(result)
                    break
            except Exception as e:
                print(f"  Error scraping press releases: {e}")

        # Brief delay to be respectful
        time.sleep(0.5)

    if not all_results:
        print(f"  No RSS feeds or press releases found for {legislator_info['full_name']}")

    return all_results

def main(local_file=None):
    """Main function."""
    if local_file:
        print(f"Loading legislators from local file: {local_file}...")
        try:
            with open(local_file, 'r') as f:
                legislators = json.load(f)
        except Exception as e:
            print(f"Error loading local file: {e}")
            return
    else:
        print("Fetching current legislators...")
        legislators = fetch_legislators()

        if not legislators:
            print("Failed to fetch legislators")
            return

    print(f"Found {len(legislators)} current legislators\n")

    all_press_releases = []

    # Process first 10 legislators as a test
    # Remove the [:10] slice to process all legislators
    for legislator in legislators[:10]:
        try:
            legislator_info = extract_legislator_info(legislator)
            results = process_legislator(legislator_info)
            all_press_releases.extend(results)

            # Brief delay between legislators
            time.sleep(1)
        except Exception as e:
            print(f"Error processing legislator: {e}")
            continue

    print(f"\n{'='*80}")
    print(f"SUMMARY: Found {len(all_press_releases)} total press releases from {len(legislators[:10])} legislators")
    print(f"{'='*80}\n")

    # Display results
    for release in all_press_releases[:50]:  # Show first 50
        leg = release.get('legislator', {})
        print(f"\nLegislator: {leg.get('name')} ({leg.get('party')}-{leg.get('state')})")
        print(f"Bioguide ID: {leg.get('bioguide_id')}")
        print(f"Title: {release.get('title', 'N/A')}")
        print(f"URL: {release.get('url', 'N/A')}")
        if release.get('date'):
            print(f"Date: {release.get('date')}")

    # Save to JSON file
    output_file = 'legislators_press_releases.json'
    with open(output_file, 'w') as f:
        json.dump(all_press_releases, f, indent=2, default=str)

    print(f"\n\nResults saved to {output_file}")

if __name__ == '__main__':
    import sys
    local_file = sys.argv[1] if len(sys.argv) > 1 else None
    main(local_file)
