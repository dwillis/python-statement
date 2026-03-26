#!/usr/bin/env python3
"""
Pattern detection tool for congressional press release pages.

Given a URL, tries each known scraper pattern and recommends a config entry.

Usage:
    python scripts/detect_pattern.py https://newmember.house.gov/press
"""

import argparse
import datetime
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_statement.scraper import Scraper
from urllib.parse import urlparse


# Patterns to try, ordered by likelihood
PATTERNS = [
    {
        'name': 'media_body',
        'container': '.media-body',
        'title_sel': 'a',
        'date_sel': 'time',
        'date_attr': 'datetime',
        'date_fmt': ['%Y-%m-%d'],
    },
    {
        'name': 'ArticleBlock',
        'container': 'div.ArticleBlock',
        'title_sel': 'h2 a',
        'date_sel': 'p',
        'date_fmt': ['%m.%d.%Y', '%m.%d.%y', '%m/%d/%y', '%B %d, %Y'],
    },
    {
        'name': 'jet_listing_grid',
        'container': '.jet-listing-grid__item',
        'title_sel': 'h3 a',
        'date_sel': 'span.elementor-icon-list-text',
        'date_fmt': ['%B %d, %Y'],
    },
    {
        'name': 'et_pb_post',
        'container': 'article.et_pb_post',
        'title_sel': 'h2 a',
        'date_sel': 'p span.published',
        'date_fmt': ['%B %d, %Y'],
    },
    {
        'name': 'table_recordlist',
        'container': 'table.recordList tr',
        'title_sel': 'a',
        'date_sel': 'td.recordListDate',
        'date_fmt': ['%m/%d/%y'],
    },
    {
        'name': 'table_time',
        'container': 'tr',
        'title_sel': 'td a',
        'date_sel': 'time',
        'date_fmt': ['%m/%d/%y', '%B %d, %Y'],
        'skip_first': 1,
    },
    {
        'name': 'documentquery_article',
        'container': 'article',
        'title_sel': 'h2 a',
        'date_sel': 'time',
        'date_fmt': ['%B %d, %Y', '%Y-%m-%d'],
    },
    {
        'name': 'documentquery_middot',
        'container': 'article',
        'title_sel': 'h2 a',
        'date_sel': 'span.middot',
        'date_from_next_sibling': True,
        'date_fmt': ['%m/%d/%Y', '%m/%d/%y'],
    },
    {
        'name': 'news_texthold',
        'container': '.news-texthold',
        'title_sel': 'h2 a',
        'date_sel': 'time',
        'date_fmt': ['%B %d, %Y'],
    },
    {
        'name': 'views_row',
        'container': '.views-row',
        'title_sel': 'a',
        'date_sel': '.evo-card-date',
        'date_fmt': ['%B %d, %Y'],
    },
    {
        'name': 'element_post_media',
        'container': 'div.element',
        'title_sel': 'div.element-title',
        'date_sel': 'span.element-datetime',
        'date_fmt': ['%B %d, %Y'],
    },
    {
        'name': 'elementor_post_card',
        'container': '.elementor-post__card',
        'title_sel': 'h3 a',
        'date_sel': 'span.elementor-post-date',
        'date_fmt': ['%B %d, %Y'],
    },
    {
        'name': 'wordpress_article',
        'container': 'article',
        'title_sel': 'h2 a',
        'date_sel': 'time',
        'date_fmt': ['%B %d, %Y'],
    },
    {
        'name': 'PageList_item',
        'container': 'li.PageList__item',
        'title_sel': 'a',
        'date_sel': 'p',
        'date_fmt': ['%m.%d.%Y', '%m/%d/%y'],
    },
]


def try_pattern(doc, pattern, url, domain):
    """Try a single pattern against the parsed HTML."""
    containers = doc.select(pattern['container'])
    skip = pattern.get('skip_first', 0)
    if skip:
        containers = containers[skip:]

    if not containers:
        return None

    results = []
    for container in containers[:5]:  # Only check first 5
        title_elem = container.select_one(pattern['title_sel'])
        if not title_elem:
            continue

        title = title_elem.text.strip()

        # Get link
        link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
        if link_elem is None:
            link_elem = container.select_one('a')
        if link_elem is None:
            continue

        href = link_elem.get('href', '')
        if not href:
            continue

        # Try date
        date = None
        date_sel = pattern.get('date_sel')
        if date_sel:
            date_elem = container.select_one(date_sel)
            if date_elem:
                date_text = None
                if pattern.get('date_from_next_sibling'):
                    sibling = date_elem.next_sibling
                    if sibling:
                        date_text = str(sibling).strip()
                elif pattern.get('date_attr'):
                    date_text = date_elem.get(pattern['date_attr'])
                if not date_text:
                    date_text = date_elem.text.strip()

                if date_text:
                    normalized = date_text.replace('.', '/')
                    for fmt in pattern.get('date_fmt', []):
                        try:
                            date = datetime.datetime.strptime(normalized, fmt).date()
                            break
                        except ValueError:
                            try:
                                date = datetime.datetime.strptime(date_text, fmt).date()
                                break
                            except ValueError:
                                continue

        results.append({
            'title': title,
            'url': href,
            'date': str(date) if date else None,
        })

    if not results:
        return None

    return {
        'pattern': pattern['name'],
        'matches': len(containers),
        'with_dates': sum(1 for r in results if r['date']),
        'sample': results,
    }


def detect(url, verify=True):
    """Detect which scraper pattern matches a URL."""
    print(f"Fetching {url}...")
    doc = Scraper.open_html(url)
    if not doc:
        print("ERROR: Could not fetch URL")
        return None

    parsed = urlparse(url)
    domain = parsed.netloc

    print(f"Testing {len(PATTERNS)} patterns...\n")

    matches = []
    for pattern in PATTERNS:
        result = try_pattern(doc, pattern, url, domain)
        if result:
            matches.append(result)
            score = result['matches'] + (result['with_dates'] * 2)
            print(f"  MATCH: {pattern['name']} "
                  f"({result['matches']} items, {result['with_dates']}/{min(5, result['matches'])} with dates)")
            for sample in result['sample'][:2]:
                print(f"    - {sample['title'][:60]} [{sample['date']}]")

    if not matches:
        print("No patterns matched this page.")
        return None

    # Pick best match (most items with dates)
    best = max(matches, key=lambda m: m['with_dates'] * 10 + m['matches'])

    print(f"\nRecommended pattern: {best['pattern']}")
    print(f"  Items found: {best['matches']}")
    print(f"  Dates found: {best['with_dates']}/{min(5, best['matches'])}")

    # Generate config entry
    pattern_info = next(p for p in PATTERNS if p['name'] == best['pattern'])
    scraper_name = domain.split('.')[0] if '.house.gov' in domain else domain.split('.')[1] if '.senate.gov' in domain else domain.split('.')[0]

    config = {
        'method': 'generic',
        'url_base': url,
        'container': pattern_info['container'],
        'title_sel': pattern_info['title_sel'],
        'date_sel': pattern_info.get('date_sel', ''),
        'date_fmt': pattern_info.get('date_fmt', ['%B %d, %Y']),
        'pagination': '?page={page}',
    }
    if pattern_info.get('date_attr'):
        config['date_attr'] = pattern_info['date_attr']
    if pattern_info.get('date_from_next_sibling'):
        config['date_from_next_sibling'] = True
    if pattern_info.get('skip_first'):
        config['skip_first'] = pattern_info['skip_first']

    print(f"\nSuggested config entry:")
    print(f"    '{scraper_name}': {{")
    for k, v in config.items():
        print(f"        '{k}': {repr(v)},")
    print(f"    }},")

    if verify:
        verify_config(config)

    return best


def verify_config(config, scraper_name='__detect_temp'):
    """
    Verify a detected config by running it through generic_scraper().

    Temporarily injects the config into SCRAPER_CONFIG, runs the real
    scraper code path, then cleans up. Reports results, date parsing,
    URL quality, and pagination.
    """
    from python_statement.config import SCRAPER_CONFIG

    # Inject temp config
    SCRAPER_CONFIG[scraper_name] = config

    try:
        print("\n--- Verification (dry-run through generic_scraper) ---\n")

        # Page 1
        results = Scraper.generic_scraper(scraper_name, page=1)

        if not results:
            print("FAIL: generic_scraper returned 0 results.")
            print("  The config selectors may not match the actual HTML structure.")
            return False

        total = len(results)
        with_dates = sum(1 for r in results if r.get('date') is not None)
        date_pct = round(with_dates / total * 100) if total else 0
        relative_urls = [r['url'] for r in results if not r['url'].startswith('http')]

        print(f"Page 1: {total} results, {with_dates}/{total} with dates ({date_pct}%)")

        # Show 3 samples
        for r in results[:3]:
            date_str = str(r['date']) if r['date'] else 'None'
            print(f"  {date_str}  {r['title'][:60]}")
            print(f"           {r['url'][:80]}")

        # Warnings
        warnings = []
        if date_pct == 0 and config.get('date_sel'):
            warnings.append("No dates parsed. Check date_sel, date_fmt, and date_attr.")
        if relative_urls:
            warnings.append(
                f"{len(relative_urls)} relative URL(s) found. "
                f"Consider adding url_prefix to the config."
            )

        # Page 2 pagination check
        pagination = config.get('pagination', '')
        if pagination and '{page}' in pagination:
            results_p2 = Scraper.generic_scraper(scraper_name, page=2)
            if not results_p2:
                warnings.append("Page 2 returned 0 results. Pagination may not work.")
            elif results_p2 == results:
                warnings.append("Page 2 returned identical results. Pagination pattern may be wrong.")
            else:
                print(f"Page 2: {len(results_p2)} results (pagination works)")

        # Verdict
        print()
        if warnings:
            print("WARN:")
            for w in warnings:
                print(f"  - {w}")
            return True  # Partial success
        else:
            print("PASS: Config verified successfully.")
            return True

    finally:
        # Clean up temp config
        SCRAPER_CONFIG.pop(scraper_name, None)


def main():
    parser = argparse.ArgumentParser(
        description='Detect scraper pattern for a congressional press page'
    )
    parser.add_argument('url', help='URL of the press releases page to analyze')
    parser.add_argument(
        '--no-verify', action='store_true',
        help='Skip verification through generic_scraper'
    )
    args = parser.parse_args()
    detect(args.url, verify=not args.no_verify)


if __name__ == '__main__':
    main()
