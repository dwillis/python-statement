# Stale Scraper Tracking — Design

## Problem

The health check currently reports whether a scraper works (returns results with
dates), but not whether the member is actually still publishing. A scraper can be
"ok" while the underlying office hasn't posted a release in months. We want to
surface that staleness on the dashboard.

## Changes

### `python_statement/health.py`

`HealthChecker.check_scraper()` gains a `latest_date` field on its result dict:
the maximum non-null `date` among the page-1 results, serialized as an ISO date
string (`YYYY-MM-DD`), or `None` if there are no dates. Computed only when
`data` is non-empty and comes from the same fetch already done for the
`ok`/`no_dates` status check — no extra requests.

### `scripts/build_dashboard.py`

- `enrich_results()` computes `days_since` (int or `None`) from `latest_date`
  vs. today's date, and a boolean `is_stale` (`status == 'ok' and days_since is
  not None and days_since >= 30`).
- Scraper Health table gains two columns: **Latest Release** and **Days Since**,
  sortable like the existing numeric/text columns.
- When `is_stale`, an additional `badge-stale` badge ("stale") is appended next
  to the existing status badge in the Status cell.
- The status filter `<select>` gains a `Stale` option; filtering matches on the
  `is_stale` flag rather than the literal status text (existing statuses
  unaffected).
- Summary stat cards gain a **Stale** count alongside OK/Empty/No Dates/Errors.

No new tab, no new files, no changes to `health_history.jsonl` schema or CLI
scripts.

## Out of scope

- Changing the 30-day threshold (hardcoded, matches the ask).
- Stale tracking for `empty`/`error`/`no_dates` scrapers (already visible via
  their status).
