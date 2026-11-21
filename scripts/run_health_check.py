#!/usr/bin/env python3
"""
Run scraper health checks.

Usage:
    python scripts/run_health_check.py          # Quick mode (50 member scrapers)
    python scripts/run_health_check.py --full   # Full mode (all member scrapers)
    python scripts/run_health_check.py --save   # Save results to JSON
    python scripts/run_health_check.py --workers 10  # More concurrent workers
    python scripts/run_health_check.py --collection committees --save --history
        # All committee scrapers; writes committee_health_results.json and
        # committee_health_history.jsonl
"""

import argparse
import sys
import os

# Add parent dir to path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_statement.health import HealthChecker


def main():
    parser = argparse.ArgumentParser(description='Run scraper health checks')
    parser.add_argument(
        '--collection', choices=sorted(HealthChecker.COLLECTION_PATHS), default='members',
        help='Which scrapers to check (default: members). Committees always run in full.'
    )
    parser.add_argument(
        '--full', action='store_true',
        help='Run full health check on all member scrapers (default: quick mode)'
    )
    parser.add_argument(
        '--save', action='store_true',
        help="Save results to the collection's results file "
             "(health_results.json or committee_health_results.json)"
    )
    parser.add_argument(
        '--workers', type=int, default=5,
        help='Number of concurrent workers (default: 5)'
    )
    parser.add_argument(
        '--history', action='store_true',
        help="Append summary to the collection's history file "
             "(health_history.jsonl or committee_health_history.jsonl)"
    )
    parser.add_argument(
        '--quiet', action='store_true',
        help='Suppress progress output'
    )
    parser.add_argument(
        '--failures-only', action='store_true',
        help='Re-check only scrapers that failed last run (empty/no_dates/error)'
    )
    args = parser.parse_args()

    results_path, history_path = HealthChecker.paths_for(args.collection)

    if args.failures_only:
        report = HealthChecker.run_failures_only(
            path=results_path,
            max_workers=args.workers,
            verbose=not args.quiet,
            collection=args.collection,
        )
    else:
        mode = 'full' if args.full else 'quick'
        report = HealthChecker.run(
            mode=mode,
            max_workers=args.workers,
            verbose=not args.quiet,
            collection=args.collection,
        )

    if args.save:
        HealthChecker.save_report(report, results_path)

    if args.history:
        HealthChecker.append_history(report, history_path)

    # Exit with non-zero if there are errors
    if report['summary']['errors'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
