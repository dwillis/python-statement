#!/usr/bin/env python3
"""
Test unassigned legislators against generic scraper patterns to find matches.
"""

import json
from python_statement import Scraper
import sys

def test_legislator(leg_data, verbose=False):
    """Test a legislator's website against all generic patterns."""
    name = leg_data['name']
    base_url = leg_data['url']
    method_name = leg_data['method_name']

    if verbose:
        print(f"Testing {name}...", end='', flush=True)

    # Try common press release paths
    test_urls = [
        f"{base_url}/media/press-releases",
        f"{base_url}/news/press-releases",
        f"{base_url}/newsroom/press-releases",
        f"{base_url}/media-center/press-releases",
        f"{base_url}/press-releases",
        f"{base_url}/news",
        f"{base_url}/media",
    ]

    # Generic patterns to test
    generic_patterns = [
        'media_body',
        'jet_listing_elementor',
        'article_block_h2_p_date',
        'table_recordlist_date',
        'element_post_media',
        'table_time'
    ]

    for pattern in generic_patterns:
        for test_url in test_urls:
            try:
                method = getattr(Scraper, pattern)
                results = method([test_url], page=1)
                if results and len(results) > 0:
                    if verbose:
                        print(f" ✓ {pattern}")
                    return {
                        'method_name': method_name,
                        'pattern': pattern,
                        'url': test_url,
                        'legislator': name,
                        'result_count': len(results)
                    }
            except Exception:
                pass

    if verbose:
        print(" ✗")
    return None

def main():
    # Load legislators
    with open('legislators_with_scrapers.json', 'r') as f:
        legislators = json.load(f)

    # Find legislators with no scraper assigned
    no_scraper = []
    for leg in legislators:
        if not leg.get('scraper_method') and leg.get('url'):
            url = leg.get('url', '')
            parts = url.replace('https://', '').replace('www.', '').split('.')[0]
            no_scraper.append({
                'name': leg.get('official_full', ''),
                'url': url,
                'state': leg.get('state', ''),
                'chamber': leg.get('type', ''),
                'bioguide': leg.get('bioguide', ''),
                'method_name': parts
            })

    print(f"Testing {len(no_scraper)} legislators against generic patterns...")
    print("(This may take a few minutes)\n")

    matches = []
    failures = []

    for i, leg in enumerate(no_scraper, 1):
        sys.stdout.write(f"\r{i}/{len(no_scraper)}")
        sys.stdout.flush()

        result = test_legislator(leg, verbose=False)
        if result:
            matches.append(result)
        else:
            failures.append(leg)

    print(f"\n\nResults: {len(matches)} matched, {len(failures)} failed\n")

    if matches:
        print("=" * 80)
        print("MATCHES - Add these to SCRAPER_CONFIG:")
        print("=" * 80)

        # Group by pattern
        by_pattern = {}
        for m in matches:
            pattern = m['pattern']
            if pattern not in by_pattern:
                by_pattern[pattern] = []
            by_pattern[pattern].append(m)

        for pattern, items in sorted(by_pattern.items()):
            print(f"\n# {pattern} pattern ({len(items)} sites)")
            for m in items:
                print(f"'{m['method_name']}': {{'method': '{pattern}', 'url_base': '{m['url']}'}},")
                print(f"  # {m['legislator']} - {m['result_count']} results")

    if failures:
        print("\n" + "=" * 80)
        print("FAILED - Need custom scrapers:")
        print("=" * 80)
        for f in failures[:20]:
            print(f"  {f['method_name']}: {f['name']} - {f['url']}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")

    # Save results
    with open('scraper_test_results.json', 'w') as f:
        json.dump({
            'matches': matches,
            'failures': failures
        }, f, indent=2)
    print(f"\n\nDetailed results saved to scraper_test_results.json")

if __name__ == '__main__':
    main()
