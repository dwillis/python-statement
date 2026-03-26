# detect_pattern Verification + Health History Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make detect_pattern.py verify its recommendations through the real generic_scraper code path, and add append-only JSONL health history with a trend viewer.

**Architecture:** Feature 1 injects a temp config entry and calls generic_scraper() to validate the detection output. Feature 2 adds a one-line-per-run JSONL append to health checks and a standalone trend script that diffs failures between runs.

**Tech Stack:** Python 3.12+, json, argparse, datetime (no new dependencies)

---

### Task 1: Add verification to detect_pattern.py

**Files:**
- Modify: `scripts/detect_pattern.py`

**Step 1: Write the `verify_config` function**

Add this function after the existing `try_pattern` and `detect` functions, before `main()`:

```python
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
```

**Step 2: Update `detect()` to call `verify_config`**

At the end of the `detect()` function, after printing the suggested config entry, add:

```python
    if verify:
        verify_config(config)

    return best
```

Update the `detect` function signature to accept `verify=True`:

```python
def detect(url, verify=True):
```

**Step 3: Update `main()` to add `--no-verify` flag**

```python
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
```

**Step 4: Test manually**

Run against a known working site:
```bash
uv run python scripts/detect_pattern.py https://bacon.house.gov/news/documentquery.aspx
```
Expected: pattern detection output followed by verification showing results, dates, and PASS.

Run with `--no-verify`:
```bash
uv run python scripts/detect_pattern.py --no-verify https://bacon.house.gov/news/documentquery.aspx
```
Expected: pattern detection output only, no verification section.

**Step 5: Commit**

```bash
git add scripts/detect_pattern.py
git commit -m "Add dry-run verification to detect_pattern.py

After detecting a pattern, injects the config into SCRAPER_CONFIG and
runs it through generic_scraper() to verify results, date parsing,
URL construction, and pagination. Use --no-verify to skip."
```

---

### Task 2: Add `append_history` to HealthChecker

**Files:**
- Modify: `python_statement/health.py`

**Step 1: Write `append_history` method**

Add this method to the `HealthChecker` class after `save_report`:

```python
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
```

**Step 2: Test manually**

```python
from python_statement.health import HealthChecker
import json

# Create a fake report
report = {
    'timestamp': '2026-03-26T14:30:00',
    'mode': 'quick',
    'summary': {'total': 3, 'ok': 2, 'empty': 1, 'no_dates': 0, 'errors': 0},
    'results': [
        {'name': 'pelosi', 'status': 'ok'},
        {'name': 'bacon', 'status': 'ok'},
        {'name': 'broken', 'status': 'empty'},
    ]
}
HealthChecker.append_history(report, '/tmp/test_history.jsonl')

# Verify
with open('/tmp/test_history.jsonl') as f:
    line = json.loads(f.readline())
    assert line['failures'] == ['broken']
    assert line['ok'] == 2
print("OK")
```

**Step 3: Commit**

```bash
git add python_statement/health.py
git commit -m "Add append_history method to HealthChecker

Appends one JSON line per health run to health_history.jsonl with
summary counts and failure names."
```

---

### Task 3: Add `--history` flag to run_health_check.py

**Files:**
- Modify: `scripts/run_health_check.py`

**Step 1: Add the flag and call append_history**

Add argument:
```python
    parser.add_argument(
        '--history', action='store_true',
        help='Append summary to health_history.jsonl'
    )
```

After `if args.save:`, add:
```python
    if args.history:
        HealthChecker.append_history(report)
```

**Step 2: Test manually**

```bash
# Run quick check with history
uv run python scripts/run_health_check.py --save --history

# Verify JSONL was created
cat health_history.jsonl
```

**Step 3: Commit**

```bash
git add scripts/run_health_check.py
git commit -m "Add --history flag to run_health_check.py"
```

---

### Task 4: Create health_trend.py

**Files:**
- Create: `scripts/health_trend.py`

**Step 1: Write the script**

```python
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
```

**Step 2: Test with synthetic data**

```bash
# Create test data
echo '{"timestamp":"2026-03-10T09:00:00","mode":"quick","total":47,"ok":44,"empty":2,"no_dates":1,"errors":0,"failures":["broken1","broken2"]}' > /tmp/test_trend.jsonl
echo '{"timestamp":"2026-03-17T09:00:00","mode":"quick","total":47,"ok":42,"empty":3,"no_dates":1,"errors":1,"failures":["broken1","broken2","pelosi"]}' >> /tmp/test_trend.jsonl
echo '{"timestamp":"2026-03-24T09:00:00","mode":"quick","total":47,"ok":44,"empty":2,"no_dates":1,"errors":0,"failures":["broken1"]}' >> /tmp/test_trend.jsonl

# Test trend view
uv run python scripts/health_trend.py --path /tmp/test_trend.jsonl

# Test failures view
uv run python scripts/health_trend.py --failures --path /tmp/test_trend.jsonl
```

Expected trend output should show `-pelosi` on 03-17 and `+broken2, +pelosi` on 03-24.

**Step 3: Commit**

```bash
git add scripts/health_trend.py
git commit -m "Add health trend viewer script

Reads health_history.jsonl and displays trends with failure diffs
between consecutive runs."
```

---

### Task 5: Update .gitignore and CI workflow

**Files:**
- Modify: `.gitignore`
- Modify: `.github/workflows/scraper-health.yml`

**Step 1: Add health_results.json to .gitignore**

Append to `.gitignore`:
```
# Health check transient output
health_results.json
health_output.txt
```

**Step 2: Update CI workflow to use --history and commit the JSONL**

In `.github/workflows/scraper-health.yml`, update the "Run health check" step to add `--history`:

```yaml
      - name: Run health check
        id: health
        run: |
          MODE="${{ github.event.inputs.mode || 'quick' }}"
          if [ "$MODE" = "full" ]; then
            uv run python scripts/run_health_check.py --full --save --history --workers 3 2>&1 | tee health_output.txt
          else
            uv run python scripts/run_health_check.py --save --history --workers 3 2>&1 | tee health_output.txt
          fi
        continue-on-error: true
```

Add a new step after "Upload health results" to commit the history file:

```yaml
      - name: Commit health history
        if: always()
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add health_history.jsonl
          git diff --cached --quiet || git commit -m "Update health history [skip ci]"
          git push
```

**Step 3: Update Makefile**

Add a `trend` target:
```makefile
trend:
	uv run python scripts/health_trend.py
```

**Step 4: Commit**

```bash
git add .gitignore .github/workflows/scraper-health.yml Makefile
git commit -m "Wire up health history in CI and gitignore

CI now appends to health_history.jsonl and commits it back.
health_results.json added to gitignore (transient).
Added make trend target."
```

---

### Task 6: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `SCRAPER_GUIDE.md`

**Step 1: Update CLAUDE.md**

In the "Health Monitoring" section under Development Commands, add:
```bash
# View health trends
make trend

# Pattern detection with verification
uv run python scripts/detect_pattern.py https://newmember.house.gov/press
uv run python scripts/detect_pattern.py --no-verify https://newmember.house.gov/press
```

**Step 2: Update README.md**

In the "Health Monitoring" section, add after the existing commands:
```bash
# View trends over time
make trend
uv run python scripts/health_trend.py --all       # All runs
uv run python scripts/health_trend.py --failures   # Current failures
```

**Step 3: Update SCRAPER_GUIDE.md**

In the "Step 1: Run Pattern Detection" section, add a note:
```
The tool verifies its recommendation by running it through `generic_scraper()`.
Use `--no-verify` to skip verification for faster scanning.
```

**Step 4: Commit**

```bash
git add CLAUDE.md README.md SCRAPER_GUIDE.md
git commit -m "Document health trends and detect_pattern verification"
```
