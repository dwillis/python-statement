#!/usr/bin/env python3
"""
Find missing congressional scrapers by detecting patterns on unmatched legislators' websites.

Loads the unmatched legislators from legislators_with_scrapers.json, tries common press
page URL paths, and runs pattern detection on each. Outputs recommended config entries.

Usage:
    uv run python scripts/find_missing_scrapers.py
    uv run python scripts/find_missing_scrapers.py --senate-only
    uv run python scripts/find_missing_scrapers.py --house-only
    uv run python scripts/find_missing_scrapers.py --verify
"""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_statement.scraper import Scraper
from scripts.detect_pattern import PATTERNS, try_pattern
from urllib.parse import urlparse


# Common press page paths to try, ordered by likelihood
HOUSE_PATHS = [
    '/media/press-releases',
    '/media-center/press-releases',
    '/news/press-releases',
    '/press-releases',
    '/news/documentquery.aspx?DocumentTypeID=27',
    '/media',
    '/press',
    '/news',
]

SENATE_PATHS = [
    '/newsroom/press-releases',
    '/news/press-releases',
    '/newsroom/press',
    '/media/press-releases',
    '/press-releases',
    '/public/index.cfm/press-releases',
    '/public/index.cfm/news-releases',
    '/news/releases',
    '/news/press',
    '/news',
]


def load_unmatched():
    """Load unmatched legislators from legislators_with_scrapers.json."""
    with open('legislators_with_scrapers.json') as f:
        data = json.load(f)
    return [l for l in data if l['scraper_method'] is None]


def derive_scraper_name(legislator):
    """Derive a config key name from the legislator's URL domain."""
    url = legislator.get('url', '')
    if not url:
        return None
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace('www.', '')
    # Extract the subdomain part (e.g., 'pelosi' from 'pelosi.house.gov')
    parts = domain.split('.')
    return parts[0] if parts else None


def detect_for_legislator(legislator, verify=False):
    """Try to detect a scraper pattern for a single legislator."""
    url = legislator.get('url', '')
    if not url:
        return None

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc.lower().replace('www.', '')
    is_senate = '.senate.gov' in domain

    paths = SENATE_PATHS if is_senate else HOUSE_PATHS
    scraper_name = derive_scraper_name(legislator)

    for path in paths:
        test_url = base + path
        doc = Scraper.open_html(test_url)
        if not doc:
            continue

        # Check for React/Next.js sites
        next_data = doc.select_one('[id="__NEXT_DATA__"]')
        if next_data:
            return {
                'legislator': legislator['official_full'],
                'state': legislator['state'],
                'type': legislator['type'],
                'scraper_name': scraper_name,
                'url': test_url,
                'pattern': 'react',
                'method': 'react',
                'note': 'Add domain to react() method domain list',
                'config': None,
            }

        # Try each HTML pattern
        best_result = None
        best_pattern = None
        for pattern in PATTERNS:
            result = try_pattern(doc, pattern, test_url, domain)
            if result:
                if best_result is None or (result['with_dates'] * 10 + result['matches']) > (best_result['with_dates'] * 10 + best_result['matches']):
                    best_result = result
                    best_pattern = pattern

        if best_result and best_result['matches'] >= 2:
            # Check if this matches a known batch method
            batch_methods = {
                'media_body': 'media_body',
                'ArticleBlock': 'article_block_h2_p_date',
                'jet_listing_grid': 'jet_listing_elementor',
                'table_recordlist': 'table_recordlist_date',
                'table_time': 'table_time',
                'element_post_media': 'element_post_media',
            }

            if best_pattern['name'] in batch_methods:
                method = batch_methods[best_pattern['name']]
                config = {
                    'method': method,
                    'url_base': test_url,
                }
            else:
                config = {
                    'method': 'generic',
                    'url_base': test_url,
                    'container': best_pattern['container'],
                    'title_sel': best_pattern['title_sel'],
                    'date_fmt': best_pattern.get('date_fmt', ['%B %d, %Y']),
                    'pagination': '?page={page}',
                }
                if best_pattern.get('date_sel'):
                    config['date_sel'] = best_pattern['date_sel']
                if best_pattern.get('date_attr'):
                    config['date_attr'] = best_pattern['date_attr']
                if best_pattern.get('date_from_next_sibling'):
                    config['date_from_next_sibling'] = True
                if best_pattern.get('skip_first'):
                    config['skip_first'] = best_pattern['skip_first']

            return {
                'legislator': legislator['official_full'],
                'state': legislator['state'],
                'type': legislator['type'],
                'scraper_name': scraper_name,
                'url': test_url,
                'pattern': best_pattern['name'],
                'method': config['method'],
                'matches': best_result['matches'],
                'with_dates': best_result['with_dates'],
                'config': config,
            }

    return {
        'legislator': legislator['official_full'],
        'state': legislator['state'],
        'type': legislator['type'],
        'scraper_name': scraper_name,
        'url': url,
        'pattern': None,
        'method': None,
        'note': 'No pattern matched any candidate URL',
        'config': None,
    }


def main():
    parser = argparse.ArgumentParser(description='Find missing congressional scrapers')
    parser.add_argument('--senate-only', action='store_true', help='Only check senators')
    parser.add_argument('--house-only', action='store_true', help='Only check House members')
    parser.add_argument('--verify', action='store_true', help='Verify detected configs through generic_scraper')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of legislators to check')
    parser.add_argument('--output', default='missing_scrapers_report.json', help='Output file')
    args = parser.parse_args()

    Scraper.enable_cache(ttl=3600)

    unmatched = load_unmatched()
    if args.senate_only:
        unmatched = [l for l in unmatched if l['type'] == 'sen']
    elif args.house_only:
        unmatched = [l for l in unmatched if l['type'] == 'rep']

    if args.limit:
        unmatched = unmatched[:args.limit]

    print(f"Checking {len(unmatched)} unmatched legislators...\n")

    results = {'detected': [], 'react': [], 'unmatched': []}

    for i, leg in enumerate(unmatched, 1):
        chamber = 'Sen' if leg['type'] == 'sen' else 'Rep'
        print(f"[{i}/{len(unmatched)}] {chamber}-{leg['state']} {leg['official_full']}...")

        result = detect_for_legislator(leg, verify=args.verify)
        if result is None:
            print(f"  SKIP: No URL")
            continue

        if result['pattern'] == 'react':
            results['react'].append(result)
            print(f"  REACT: {result['url']}")
        elif result['pattern']:
            results['detected'].append(result)
            print(f"  FOUND: {result['pattern']} ({result.get('matches', '?')} items, "
                  f"{result.get('with_dates', '?')} dates) -> {result['url']}")
        else:
            results['unmatched'].append(result)
            print(f"  NONE: No pattern matched")

    # Summary
    print(f"\n{'='*70}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"  Pattern detected: {len(results['detected'])}")
    print(f"  React sites:      {len(results['react'])}")
    print(f"  No match:         {len(results['unmatched'])}")
    print(f"  Total checked:    {len(unmatched)}")

    if results['detected']:
        print(f"\n--- Detected Configs ---")
        for r in results['detected']:
            name = r['scraper_name']
            config = r['config']
            print(f"\n    '{name}': {json.dumps(config)},")

    if results['react']:
        print(f"\n--- React Sites (add to react() domain list) ---")
        for r in results['react']:
            domain = urlparse(r['url']).netloc
            print(f"    '{domain}',  # {r['legislator']} ({r['state']})")

    if results['unmatched']:
        print(f"\n--- No Pattern Matched ---")
        for r in results['unmatched']:
            print(f"    {r['legislator']} ({r['type'].upper()}-{r['state']}) {r['url']}")

    # Save full report
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull report saved to {args.output}")


if __name__ == '__main__':
    main()
