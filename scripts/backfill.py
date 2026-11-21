#!/usr/bin/env python3
"""
Backfill historical press releases by paging scrapers.

Pages are newest-first: page 1 is the latest, higher pages are older.
Paging a scraper stops at the first of:
  - an empty page (past the end of the listing)
  - a page with no URLs not already seen (listings that ignore the page
    number and keep returning the same items)
  - a page whose dated items are all older than --since
  - --pages pages

Usage:
    # One scraper, pages 1-3
    python scripts/backfill.py --scraper harris --pages 3

    # All media_body member scrapers, pages 1-3, saved to JSON
    python scripts/backfill.py --method media_body --pages 3 --out backfill.json

    # Every member scraper (slow), 5 concurrent workers
    python scripts/backfill.py --all --pages 3 --workers 5 --out backfill.json

    # Every committee scraper back to the start of the 119th Congress
    python scripts/backfill.py --all --collection committees --since 2025-01-03 \\
        --pages 100 --workers 4 --out committee_backfill.json

    # Every side of one committee
    python scripts/backfill.py --committee HSAG --since 2025-01-03 --pages 50
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
from python_statement.committee_config import COMMITTEE_CONFIG


def backfill_one(name, pages, since=None):
    """Page a single scraper from 1..pages.

    Args:
        name: Scraper name (member or committee).
        pages: Maximum number of pages to fetch.
        since: Optional datetime.date. Items dated before it are dropped, and
            paging stops at the first page whose dated items are all older.
            Undated items are kept.

    Returns:
        (name, results, error, stop_reason). error is None on success.
        stop_reason is 'empty', 'repeat', 'since', 'max_pages' or 'error'.
    """
    results = []
    seen = set()
    for page in range(1, pages + 1):
        try:
            page_results = Scraper.run_scraper(name, page)
        except Exception as e:  # noqa: BLE001 - one bad scraper shouldn't kill the run
            return name, results, str(e), 'error'
        if not page_results:
            return name, results, None, 'empty'

        new = [r for r in page_results if r['url'] not in seen]
        if not new:
            return name, results, None, 'repeat'
        seen.update(r['url'] for r in new)

        if since is None:
            results.extend(new)
            continue

        results.extend(r for r in new if r.get('date') is None or r['date'] >= since)
        # Stop only when every dated item is older than the cutoff, so an old
        # pinned/featured item at the top of a page doesn't end paging early.
        dated = [r['date'] for r in new if r.get('date') is not None]
        if dated and max(dated) < since:
            return name, results, None, 'since'
    return name, results, None, 'max_pages'


def select_scrapers(args):
    """Resolve the list of scraper names to run from CLI args."""
    if args.scraper:
        return [args.scraper]
    if args.committee:
        thomas_id = args.committee.upper()
        return sorted(n for n, c in COMMITTEE_CONFIG.items() if c['thomas_id'] == thomas_id)
    config = COMMITTEE_CONFIG if args.collection == 'committees' else SCRAPER_CONFIG
    if args.method:
        return sorted(n for n, c in config.items() if c['method'] == args.method)
    if args.all:
        return sorted(config.keys())
    return []


def main():
    parser = argparse.ArgumentParser(description='Backfill press releases by paging scrapers')
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--scraper', help='Backfill a single scraper by name (e.g. harris, hsag_minority)')
    target.add_argument('--method', help='Backfill all scrapers in the collection using this method')
    target.add_argument('--all', action='store_true', help='Backfill every scraper in the collection')
    target.add_argument('--committee', help='Backfill every side of one committee by thomas_id (e.g. HSAG)')
    parser.add_argument('--collection', choices=['members', 'committees'], default='members',
                        help='Collection for --all/--method (default: members)')
    parser.add_argument('--pages', type=int, default=3,
                        help='Maximum pages to fetch per scraper (default: 3)')
    parser.add_argument('--since', type=datetime.date.fromisoformat,
                        help='Stop paging once releases are older than this date (YYYY-MM-DD)')
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
        since = f', since {args.since}' if args.since else ''
        print(f'Backfilling {len(names)} scraper(s), up to {args.pages} pages{since}, '
              f'{args.workers} worker(s)...')

    all_results = []
    failures = []
    hit_page_limit = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(backfill_one, name, args.pages, args.since): name
                   for name in names}
        for future in as_completed(futures):
            name, results, error, reason = future.result()
            all_results.extend(results)
            if error:
                failures.append({'scraper': name, 'error': error})
                if not args.quiet:
                    print(f'  ✗ {name}: {error} (kept {len(results)} releases)')
                continue
            if reason == 'max_pages':
                hit_page_limit.append(name)
            if not args.quiet:
                print(f'  ✓ {name}: {len(results)} releases (stopped: {reason})')

    # De-dup on URL (pages can overlap if a site posts mid-run)
    deduped = list({r['url']: r for r in all_results}.values())
    deduped.sort(key=lambda r: r['date'] or datetime.date.min, reverse=True)

    print(f'\nDone: {len(deduped)} unique releases from {len(names) - len(failures)} '
          f'scraper(s); {len(failures)} failure(s).')
    if args.since and hit_page_limit:
        print(f'Reached --pages before --since for {len(hit_page_limit)} scraper(s); '
              f'raise --pages to go further back: {", ".join(sorted(hit_page_limit))}')

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
