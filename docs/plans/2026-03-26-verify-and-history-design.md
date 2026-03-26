# Design: detect_pattern Verification + Health History Tracking

**Date:** 2026-03-26

## Feature 1: detect_pattern.py Self-Verification

### Problem
`detect_pattern.py` recommends a config entry but doesn't verify the config works through the actual `generic_scraper()` code path. Date parsing, relative URLs, and pagination can be subtly wrong.

### Approach
Dry-run the recommended config through `generic_scraper()` after detection.

### Behavior
After `detect()` finds the best pattern and builds the config dict:

1. Inject the config into `SCRAPER_CONFIG` under a temp key (`__detect_temp`)
2. Call `Scraper.generic_scraper('__detect_temp', page=1)`
3. Report verification summary:
   - Results count — compare to raw detection
   - Dates parsed — count and percentage; flag if 0%
   - URLs absolute — flag any not starting with `http`, suggest `url_prefix`
   - Print 3 sample results in standard dict format
4. If `pagination` is set, try page 2:
   - Report whether it returned results
   - Flag if page 2 results are identical to page 1
5. Print PASS/WARN/FAIL verdict with actionable suggestions

### CLI Interface
- Verification runs by default
- `--no-verify` flag to skip (for quick scanning)

### Files Modified
- `scripts/detect_pattern.py` — add `verify_config()` function, update `detect()` and CLI

---

## Feature 2: Health History Tracking

### Problem
Each health run produces a standalone JSON file. No trend data, no way to see patterns over time.

### Approach
Append-only JSONL file + trend viewer script.

### Storage Format
`health_history.jsonl` in project root. One JSON line per run (~150 bytes each):

```json
{"timestamp": "2026-03-26T14:30:00", "mode": "quick", "total": 47, "ok": 42, "empty": 3, "no_dates": 1, "errors": 1, "failures": ["broken1", "broken2"]}
```

Summary + failure names only. Full per-scraper results stay in `health_results.json`.

### Appending
`HealthChecker.save_report()` appends to `health_history.jsonl` after writing `health_results.json`. Controlled by `--history` flag on `run_health_check.py`.

### Trend Viewer
New script `scripts/health_trend.py`:

- Reads `health_history.jsonl`, prints tabular summary
- Shows last N runs (default 10, `--all` for everything)
- Diffs failures between consecutive runs: `+` = newly working, `-` = newly broken
- `--failures` flag to list all currently failing scrapers

Output format:
```
Date        Mode   OK  Empty NoDates Errors  Changes
2026-03-10  quick  44    2      1      0
2026-03-17  quick  42    3      1      1      - pelosi, - bacon
2026-03-24  quick  44    2      1      0      + pelosi, + bacon
```

### CI Integration
Update `.github/workflows/scraper-health.yml` to pass `--history`. Commit `health_history.jsonl` back to the repo for persistence across runs.

### Gitignore
- Add `health_results.json` (transient, per-run)
- Do NOT ignore `health_history.jsonl` (persistent history)

### Files Modified
- `python_statement/health.py` — add `append_history()` method
- `scripts/run_health_check.py` — add `--history` flag
- `scripts/health_trend.py` — new file
- `.github/workflows/scraper-health.yml` — add `--history` and commit step
- `.gitignore` — add `health_results.json`

### Size Estimate
~150 bytes/line. Weekly runs = ~8KB/year. No concern for git or disk.
