"""
Health check runner for congressional press release scrapers.

Two collections, each with its own results and history files:
- members (SCRAPER_CONFIG): quick mode tests ~50 representative scrapers,
  full mode tests all of them
- committees (COMMITTEE_CONFIG): always tests every committee scraper

Checks: HTTP connectivity, results > 0, dates not all None
"""

import datetime
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .scraper import Scraper
from .feed import Feed
from .config import SCRAPER_CONFIG


class HealthChecker:
    """Run health checks on configured scrapers."""

    # Representative scrapers for quick mode (mix of patterns)
    QUICK_SCRAPERS = [
        # media_body (248 scrapers)
        'pelosi', 'scalise', 'jordan', 'neguse', 'waters',
        # generic — article container (82)
        'bacon', 'gosar', 'slotkin', 'welch',
        # generic — div.ArticleBlock (23)
        'baldwin', 'schumer', 'cotton', 'hirono', 'cassidy',
        # generic — article.et_pb_post (12)
        'budd', 'hagerty', 'lummis', 'bennet',
        # generic — .jet-listing-grid__item (7)
        'britt', 'tuberville',
        # generic — article.elementor-post (7)
        'murray', 'fetterman',
        # generic — article.newsblocker (7)
        'foxx', 'scanlon',
        # generic — .views-row (6)
        'meeks', 'crawford',
        # generic — other containers
        'grassley', 'hawley', 'angusking', 'sykes', 'rickscott', 'warner',
        # table_recordlist_date (32)
        'moran', 'thune', 'barr',
        # senate_drupal_newscontent (25)
        'durbin', 'wyden', 'takano',
        # react (16)
        'lucas', 'gottheimer',
        # jet_listing_elementor (3)
        'timscott',
        # element_post_media (3)
        'tillis', 'wicker',
        # Custom methods
        'tokuda', 'joyce', 'cornyn',
    ]

    @classmethod
    def check_scraper(cls, name, timeout=30):
        """
        Run a health check on a single scraper.

        Returns dict with: name, status ('ok'|'error'|'empty'|'no_dates'),
        count, has_dates, latest_date, duration_ms, error
        """
        start = time.time()
        result = {
            'name': name,
            'status': 'ok',
            'count': 0,
            'has_dates': False,
            'latest_date': None,
            'duration_ms': 0,
            'error': None,
        }

        try:
            data = Scraper.run_scraper(name, page=1)
            duration = (time.time() - start) * 1000
            result['duration_ms'] = round(duration)

            if not data:
                result['status'] = 'empty'
                result['count'] = 0
                return result

            result['count'] = len(data)
            dates = [item['date'] for item in data if item.get('date') is not None]
            result['has_dates'] = bool(dates)
            if dates:
                result['latest_date'] = max(dates).isoformat()

            if not result['has_dates']:
                result['status'] = 'no_dates'

        except Exception as e:
            duration = (time.time() - start) * 1000
            result['duration_ms'] = round(duration)
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    # Report and history files per collection
    COLLECTION_PATHS = {
        'members': ('health_results.json', 'health_history.jsonl'),
        'committees': ('committee_health_results.json', 'committee_health_history.jsonl'),
    }

    @classmethod
    def paths_for(cls, collection):
        """Return (results_path, history_path) for a collection."""
        if collection not in cls.COLLECTION_PATHS:
            raise ValueError(
                f"Unknown collection '{collection}'. Valid: {sorted(cls.COLLECTION_PATHS)}"
            )
        return cls.COLLECTION_PATHS[collection]

    @classmethod
    def run(cls, mode='quick', max_workers=5, verbose=True, collection='members',
            scrapers=None):
        """
        Run health checks.

        Args:
            mode: 'quick' for representative sample, 'full' for all scrapers.
                Ignored for committees, which always run in full.
            max_workers: Number of concurrent workers
            verbose: Print progress to stdout
            collection: 'members' (SCRAPER_CONFIG) or 'committees' (COMMITTEE_CONFIG)
            scrapers: Explicit list of scraper names to check (overrides mode)

        Returns:
            dict with keys: results, summary, timestamp, mode, collection
        """
        cls.paths_for(collection)  # validates the collection name
        if scrapers is None:
            if collection == 'committees':
                mode = 'full'
                scrapers = Scraper.committee_methods()
            elif mode == 'quick':
                scrapers = cls.QUICK_SCRAPERS
            else:
                scrapers = Scraper.member_methods()

        total = len(scrapers)
        results = []
        completed = 0

        if verbose:
            print(f"Running {mode} {collection} health check on {total} scrapers...")
            print(f"Workers: {max_workers}")
            print()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(cls.check_scraper, name): name
                for name in scrapers
            }

            for future in as_completed(futures):
                name = futures[future]
                completed += 1
                try:
                    result = future.result(timeout=60)
                except Exception as e:
                    result = {
                        'name': name,
                        'status': 'error',
                        'count': 0,
                        'has_dates': False,
                        'duration_ms': 0,
                        'error': str(e),
                    }

                results.append(result)

                if verbose:
                    status_icon = {
                        'ok': '+',
                        'empty': '-',
                        'no_dates': '?',
                        'error': 'X',
                    }.get(result['status'], '?')
                    print(
                        f"  [{status_icon}] {completed}/{total} "
                        f"{name}: {result['status']} "
                        f"({result['count']} results, {result['duration_ms']}ms)"
                    )

        # Sort by name
        results.sort(key=lambda r: r['name'])

        # Build summary
        ok = sum(1 for r in results if r['status'] == 'ok')
        empty = sum(1 for r in results if r['status'] == 'empty')
        no_dates = sum(1 for r in results if r['status'] == 'no_dates')
        errors = sum(1 for r in results if r['status'] == 'error')

        summary = {
            'total': total,
            'ok': ok,
            'empty': empty,
            'no_dates': no_dates,
            'errors': errors,
            'success_rate': round(ok / total * 100, 1) if total > 0 else 0,
        }

        report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'mode': mode,
            'collection': collection,
            'summary': summary,
            'results': results,
        }

        if verbose:
            print()
            print("=" * 60)
            print(f"Health Check Summary ({collection}, {mode} mode)")
            print("=" * 60)
            print(f"  Total:     {total}")
            print(f"  OK:        {ok}")
            print(f"  Empty:     {empty}")
            print(f"  No dates:  {no_dates}")
            print(f"  Errors:    {errors}")
            print(f"  Success:   {summary['success_rate']}%")
            print()

            if errors > 0 or empty > 0:
                print("Failed scrapers:")
                for r in results:
                    if r['status'] in ('error', 'empty'):
                        err = f" - {r['error']}" if r['error'] else ""
                        print(f"  [{r['status']}] {r['name']}{err}")
                print()

        return report

    @classmethod
    def failures_from_report(cls, path='health_results.json'):
        """Return list of scraper names that failed in the last saved report."""
        with open(path) as f:
            report = json.load(f)
        return [
            r['name'] for r in report.get('results', [])
            if r['status'] in ('error', 'empty', 'no_dates')
        ]

    @classmethod
    def run_failures_only(cls, path=None, max_workers=5, verbose=True, collection='members'):
        """
        Re-run health checks only for scrapers that failed in the last report.

        Args:
            path: Path to the previous report (defaults to the collection's results file)
            max_workers: Number of concurrent workers
            verbose: Print progress to stdout
            collection: 'members' or 'committees'

        Returns:
            dict with keys: results, summary, timestamp, mode, collection
        """
        if path is None:
            path = cls.paths_for(collection)[0]
        try:
            scrapers = cls.failures_from_report(path)
        except FileNotFoundError:
            print(f"No previous report found at {path}. Run a full check first.")
            sys.exit(1)

        if not scrapers:
            if verbose:
                print("No failures found in previous report. All scrapers OK!")
            return {
                'timestamp': datetime.datetime.now().isoformat(),
                'mode': 'failures-only',
                'collection': collection,
                'summary': {'total': 0, 'ok': 0, 'empty': 0, 'no_dates': 0, 'errors': 0, 'success_rate': 100.0},
                'results': [],
            }

        if verbose:
            print(f"Re-checking {len(scrapers)} previously failed scrapers...")

        report = cls.run(max_workers=max_workers, verbose=verbose,
                         collection=collection, scrapers=scrapers)
        report['mode'] = 'failures-only'
        return report

    @classmethod
    def save_report(cls, report, path='health_results.json'):
        """Save health check report to JSON file."""
        # Convert any non-serializable objects
        def default(obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
            return str(obj)

        with open(path, 'w') as f:
            json.dump(report, f, indent=2, default=default)
        print(f"Report saved to {path}")

    @classmethod
    def append_history(cls, report, path='health_history.jsonl'):
        """Append a summary line to the health history JSONL file."""
        summary = report.get('summary', {})
        failures = [
            r['name'] for r in report.get('results', [])
            if r['status'] in ('error', 'empty')
        ]

        entry = {
            'timestamp': report.get('timestamp', datetime.datetime.now().isoformat()),
            'mode': report.get('mode', 'unknown'),
            'collection': report.get('collection', 'members'),
            'total': summary.get('total', 0),
            'ok': summary.get('ok', 0),
            'empty': summary.get('empty', 0),
            'no_dates': summary.get('no_dates', 0),
            'errors': summary.get('errors', 0),
            'failures': sorted(failures),
        }

        with open(path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        print(f"History appended to {path}")
