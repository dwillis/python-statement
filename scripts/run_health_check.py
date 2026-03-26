#!/usr/bin/env python3
"""
Run scraper health checks.

Usage:
    python scripts/run_health_check.py          # Quick mode (50 scrapers)
    python scripts/run_health_check.py --full   # Full mode (all scrapers)
    python scripts/run_health_check.py --save   # Save results to JSON
    python scripts/run_health_check.py --workers 10  # More concurrent workers
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
        '--full', action='store_true',
        help='Run full health check on all scrapers (default: quick mode)'
    )
    parser.add_argument(
        '--save', action='store_true',
        help='Save results to health_results.json'
    )
    parser.add_argument(
        '--workers', type=int, default=5,
        help='Number of concurrent workers (default: 5)'
    )
    parser.add_argument(
        '--history', action='store_true',
        help='Append summary to health_history.jsonl'
    )
    parser.add_argument(
        '--quiet', action='store_true',
        help='Suppress progress output'
    )
    args = parser.parse_args()

    mode = 'full' if args.full else 'quick'
    report = HealthChecker.run(
        mode=mode,
        max_workers=args.workers,
        verbose=not args.quiet,
    )

    if args.save:
        HealthChecker.save_report(report)

    if args.history:
        HealthChecker.append_history(report)

    # Exit with non-zero if there are errors
    if report['summary']['errors'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
