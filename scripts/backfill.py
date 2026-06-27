#!/usr/bin/env python3
"""
Backfill historical press releases by paging scrapers.

Pages are newest-first: page 1 is the latest, higher pages are older.
Paging a scraper stops early once a page returns no results.

Usage:
    # One scraper, pages 1-3
    python scripts/backfill.py --scraper harris --pages 3

    # All media_body scrapers, pages 1-3, saved to JSON
    python scripts/backfill.py --method media_body --pages 3 --out backfill.json

    # Every scraper in SCRAPER_CONFIG (slow), 5 concurrent workers
    python scripts/backfill.py --all --pages 3 --workers 5 --out backfill.json
"""

import argparse
import datetime
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent dir to path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_statement.scraper import Scraper
from python_statement.config import SCRAPER_CONFIG


def backfill_one(name, pages):
    """Page a single scraper from 1..pages, stopping at the first empty page.

    Returns (name, results, error). error is None on success.
    """
    results = []
    for page in range(1, pages + 1):
        try:
            page_results = Scraper.run_scraper(name, page)
        except Exception as e:  # noqa: BLE001 - one bad scraper shouldn't kill the run
            return name, results, str(e)
        if not page_results:
            break
        results.extend(page_results)
    return name, results, None


def select_scrapers(args):
    """Resolve the list of scraper names to run from CLI args."""
    if args.scraper:
        return [args.scraper]
    if args.method:
        return [n for n, c in SCRAPER_CONFIG.items() if c['method'] == args.method]
    if args.all:
        return sorted(SCRAPER_CONFIG.keys())
    return []


def main():
    parser = argparse.ArgumentParser(description='Backfill press releases by paging scrapers')
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--scraper', help='Backfill a single scraper by name (e.g. harris)')
    target.add_argument('--method', help='Backfill all scrapers using this method (e.g. media_body)')
    target.add_argument('--all', action='store_true', help='Backfill every scraper in SCRAPER_CONFIG')
    parser.add_argument('--pages', type=int, default=3, help='Number of pages to fetch (default: 3)')
    parser.add_argument('--workers', type=int, default=1,
                        help='Concurrent scrapers to page at once (default: 1)')
    parser.add_argument('--out', help='Write combined results to this JSON file')
    parser.add_argument('--cache', action='store_true',
                        help='Enable the 24h disk cache (useful for repeated runs)')
    parser.add_argument('--quiet', action='store_true', help='Suppress per-scraper progress output')
    args = parser.parse_args()

    if args.cache:
        Scraper.enable_cache(ttl=86400)

    names = select_scrapers(args)
    if not names:
        print('No scrapers matched the given criteria.', file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f'Backfilling {len(names)} scraper(s), pages 1-{args.pages}, '
              f'{args.workers} worker(s)...')

    all_results = []
    failures = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(backfill_one, name, args.pages): name for name in names}
        for future in as_completed(futures):
            name, results, error = future.result()
            if error:
                failures.append({'scraper': name, 'error': error})
                if not args.quiet:
                    print(f'  ✗ {name}: {error}')
            else:
                all_results.extend(results)
                if not args.quiet:
                    print(f'  ✓ {name}: {len(results)} releases')

    # De-dup on URL (pages can overlap if a member posts mid-run)
    deduped = list({r['url']: r for r in all_results}.values())
    deduped.sort(key=lambda r: r['date'] or datetime.date.min, reverse=True)

    print(f'\nDone: {len(deduped)} unique releases from {len(names) - len(failures)} '
          f'scraper(s); {len(failures)} failure(s).')

    if args.out:
        with open(args.out, 'w') as f:
            json.dump(
                {'results': deduped, 'failures': failures},
                f,
                indent=2,
                default=str,  # serialize datetime.date
            )
        print(f'Wrote {args.out}')


if __name__ == '__main__':
    main()
