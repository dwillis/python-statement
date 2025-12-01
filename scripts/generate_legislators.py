#!/usr/bin/env python
"""
Utilities for processing congressional legislators data and matching with scrapers.
"""

import yaml
import requests
from datetime import datetime
from urllib.parse import urlparse
import re


def fetch_legislators():
    """
    Fetch current legislators from the unitedstates/congress-legislators repository.
    
    Returns:
        list: List of legislator dictionaries from the YAML file
    """
    url = "https://raw.githubusercontent.com/unitedstates/congress-legislators/refs/heads/main/legislators-current.yaml"
    response = requests.get(url)
    response.raise_for_status()
    return yaml.safe_load(response.content)


def get_current_term(legislator):
    """
    Get the current term for a legislator (where end_date > today).
    
    Args:
        legislator (dict): Legislator data from YAML
        
    Returns:
        dict: Current term or None if no active term
    """
    today = datetime.now().date()
    
    for term in reversed(legislator.get('terms', [])):
        end_date_str = term.get('end')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if end_date > today:
                return term
    
    return None


def process_legislators():
    """
    Process legislators data and extract relevant information.
    
    Returns:
        list: List of dictionaries with legislator information including:
              - bioguide: Bioguide ID
              - official_full: Official full name
              - gender: Gender
              - state: State abbreviation
              - district: District number (House only, None for Senate)
              - party: Party affiliation
              - url: Official website URL
              - type: 'rep' or 'sen'
    """
    legislators_data = fetch_legislators()
    processed = []
    
    for legislator in legislators_data:
        current_term = get_current_term(legislator)
        
        if not current_term:
            continue
        
        bioguide = legislator['id']['bioguide']
        
        # Get official full name
        name = legislator.get('name', {})
        official_full = name.get('official_full', '')
        if not official_full:
            # Construct from first, middle, last
            first = name.get('first', '')
            middle = name.get('middle', '')
            last = name.get('last', '')
            suffix = name.get('suffix', '')
            
            parts = [first]
            if middle:
                parts.append(middle)
            parts.append(last)
            if suffix:
                parts.append(suffix)
            official_full = ' '.join(parts)
        
        gender = legislator['bio'].get('gender', '')
        
        # Term information
        state = current_term.get('state', '')
        district = current_term.get('district', None)
        party = current_term.get('party', '')
        url = current_term.get('url', '')
        term_type = current_term.get('type', '')
        
        legislator_info = {
            'bioguide': bioguide,
            'official_full': official_full,
            'gender': gender,
            'state': state,
            'district': district,
            'party': party,
            'url': url,
            'type': term_type
        }
        
        processed.append(legislator_info)
    
    return processed


def normalize_url(url):
    """
    Normalize a URL for comparison by extracting the domain.
    
    Args:
        url (str): URL to normalize
        
    Returns:
        str: Normalized domain (e.g., 'pelosi.house.gov')
    """
    if not url:
        return ''
    
    # Parse the URL and get the domain
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Remove 'www.' prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return domain


def extract_scraper_urls():
    """
    Extract URLs from all scraper methods in statement.py.
    
    Returns:
        dict: Dictionary mapping normalized domains to scraper method names
    """
    from python_statement.statement import Scraper
    from inspect import getmembers, ismethod
    
    scraper_urls = {}
    
    # Get all class methods
    methods = getmembers(Scraper, predicate=lambda x: callable(x))
    
    for method_name, method_obj in methods:
        # Skip private methods and non-scraper methods
        if method_name.startswith('_') or method_name in ['open_html', 'current_year', 
                                                            'current_month', 'member_methods', 
                                                            'committee_methods', 'member_scrapers']:
            continue
        
        try:
            # Get the source code of the method
            from inspect import getsource
            source = getsource(method_obj)
            
            # Extract URLs using regex
            url_pattern = r'https?://([a-zA-Z0-9\-\.]+(?:house|senate)\.gov)'
            matches = re.findall(url_pattern, source)
            
            for domain in matches:
                normalized = normalize_url(f"https://{domain}")
                if normalized and normalized not in scraper_urls:
                    scraper_urls[normalized] = method_name
        except (TypeError, OSError):
            # Some methods might not have source available
            continue
    
    return scraper_urls


def match_legislators_to_scrapers():
    """
    Match legislators to their corresponding scraper methods.
    
    Returns:
        list: List of legislator dictionaries with added 'scraper_method' field
    """
    legislators = process_legislators()
    scraper_urls = extract_scraper_urls()
    
    matched_count = 0
    
    for legislator in legislators:
        url = legislator.get('url', '')
        normalized_url = normalize_url(url)
        
        if normalized_url in scraper_urls:
            legislator['scraper_method'] = scraper_urls[normalized_url]
            matched_count += 1
        else:
            legislator['scraper_method'] = None
    
    print(f"Matched {matched_count} out of {len(legislators)} legislators to scrapers")
    
    return legislators


def get_legislators_by_scraper(scraper_method_name):
    """
    Get all legislators that use a specific scraper method.
    
    Args:
        scraper_method_name (str): Name of the scraper method
        
    Returns:
        list: List of legislator dictionaries using that scraper
    """
    legislators = match_legislators_to_scrapers()
    return [leg for leg in legislators if leg.get('scraper_method') == scraper_method_name]


def get_unmatched_legislators():
    """
    Get legislators that don't have a matching scraper method.
    
    Returns:
        list: List of legislator dictionaries without scrapers
    """
    legislators = match_legislators_to_scrapers()
    return [leg for leg in legislators if leg.get('scraper_method') is None]


def print_legislator_summary():
    """
    Print a summary of legislators and their scraper matches.
    """
    legislators = match_legislators_to_scrapers()
    
    print("\n" + "=" * 80)
    print("LEGISLATOR SUMMARY")
    print("=" * 80)
    
    # Count by chamber
    house = [leg for leg in legislators if leg['type'] == 'rep']
    senate = [leg for leg in legislators if leg['type'] == 'sen']
    
    print(f"\nTotal Legislators: {len(legislators)}")
    print(f"  House: {len(house)}")
    print(f"  Senate: {len(senate)}")
    
    # Count by party
    parties = {}
    for leg in legislators:
        party = leg['party']
        parties[party] = parties.get(party, 0) + 1
    
    print(f"\nBy Party:")
    for party, count in sorted(parties.items()):
        print(f"  {party}: {count}")
    
    # Scraper matches
    matched = [leg for leg in legislators if leg.get('scraper_method')]
    unmatched = [leg for leg in legislators if not leg.get('scraper_method')]
    
    print(f"\nScraper Matches:")
    print(f"  Matched: {len(matched)}")
    print(f"  Unmatched: {len(unmatched)}")
    print(f"  Match Rate: {len(matched)/len(legislators)*100:.1f}%")
    
    # Show some unmatched examples
    if unmatched:
        print(f"\nSample Unmatched Legislators (first 10):")
        for leg in unmatched[:10]:
            print(f"  {leg['official_full']} ({leg['type'].upper()}-{leg['state']})")
            print(f"    URL: {leg['url']}")
    
    # Count by scraper method
    scraper_counts = {}
    for leg in matched:
        method = leg['scraper_method']
        scraper_counts[method] = scraper_counts.get(method, 0) + 1
    
    print(f"\nTop Scraper Methods:")
    for method, count in sorted(scraper_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {method}: {count} legislators")


if __name__ == "__main__":
    # Run summary when executed directly
    print_legislator_summary()
    
    # Optionally save to file
    import json
    legislators = match_legislators_to_scrapers()
    
    output_file = "legislators_with_scrapers.json"
    with open(output_file, 'w') as f:
        json.dump(legislators, f, indent=2)
    
    print(f"\n✓ Saved {len(legislators)} legislators to {output_file}")
