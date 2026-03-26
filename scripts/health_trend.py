#!/usr/bin/env python3
"""
Health trend viewer. Reads health_history.jsonl and shows trends over time.

Usage:
    python scripts/health_trend.py              # Last 10 runs
    python scripts/health_trend.py --all        # All runs
    python scripts/health_trend.py --failures   # Show current failures
"""

import argparse
import json
import sys


def load_history(path='health_history.jsonl'):
    """Load all entries from the JSONL file."""
    entries = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except FileNotFoundError:
        print(f"No history file found at {path}")
        sys.exit(1)
    return entries


def diff_failures(prev_failures, curr_failures):
    """Compute newly broken (-) and newly fixed (+) scrapers."""
    prev = set(prev_failures)
    curr = set(curr_failures)
    fixed = sorted(prev - curr)
    broken = sorted(curr - prev)
    changes = []
    for name in fixed:
        changes.append(f"+{name}")
    for name in broken:
        changes.append(f"-{name}")
    return changes


def show_trend(entries, show_all=False):
    """Print a table of health check trends."""
    if not entries:
        print("No history entries found.")
        return

    if not show_all:
        entries = entries[-10:]

    # Header
    print(f"{'Date':<12} {'Mode':<6} {'OK':>4} {'Empty':>6} {'NoDt':>5} "
          f"{'Err':>4} {'Rate':>6}  Changes")
    print("-" * 80)

    prev_failures = None
    for entry in entries:
        date = entry['timestamp'][:10]
        mode = entry.get('mode', '?')[:5]
        ok = entry.get('ok', 0)
        empty = entry.get('empty', 0)
        no_dates = entry.get('no_dates', 0)
        errors = entry.get('errors', 0)
        total = entry.get('total', 0)
        rate = f"{round(ok / total * 100)}%" if total else "?"
        failures = entry.get('failures', [])

        changes_str = ""
        if prev_failures is not None:
            changes = diff_failures(prev_failures, failures)
            if changes:
                changes_str = ", ".join(changes)

        print(f"{date:<12} {mode:<6} {ok:>4} {empty:>6} {no_dates:>5} "
              f"{errors:>4} {rate:>6}  {changes_str}")

        prev_failures = failures


def show_failures(entries):
    """Show all currently failing scrapers from the most recent run."""
    if not entries:
        print("No history entries found.")
        return

    latest = entries[-1]
    failures = latest.get('failures', [])
    date = latest['timestamp'][:10]

    if not failures:
        print(f"No failures in most recent run ({date}).")
        return

    print(f"Failing scrapers as of {date}:")
    for name in failures:
        print(f"  - {name}")
    print(f"\nTotal: {len(failures)} failures")


def main():
    parser = argparse.ArgumentParser(description='View health check trends')
    parser.add_argument(
        '--all', action='store_true',
        help='Show all runs (default: last 10)'
    )
    parser.add_argument(
        '--failures', action='store_true',
        help='Show currently failing scrapers'
    )
    parser.add_argument(
        '--path', default='health_history.jsonl',
        help='Path to history JSONL file'
    )
    args = parser.parse_args()

    entries = load_history(args.path)

    if args.failures:
        show_failures(entries)
    else:
        show_trend(entries, show_all=args.all)


if __name__ == '__main__':
    main()
