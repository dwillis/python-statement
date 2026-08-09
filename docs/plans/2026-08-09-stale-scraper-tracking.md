# Stale Scraper Tracking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface, in the existing health check and dashboard, which working scrapers haven't found a new release in 30+ days.

**Architecture:** `HealthChecker.check_scraper()` already fetches page-1 results to determine status/has_dates; reuse that same data to compute `latest_date` (max release date, ISO string or `None`) with no extra HTTP requests. `build_dashboard.py`'s existing `enrich_results()` then derives `days_since` and `is_stale` from `latest_date`, and the existing HTML/JS table gains two columns, a "stale" badge, a status-filter option, and a summary stat card — no new tab, no new files besides tests.

**Tech Stack:** Python 3.12, `unittest` + `unittest.mock`, BeautifulSoup (already in use), no new dependencies.

---

### Task 1: Add `latest_date` to `HealthChecker.check_scraper()`

**Files:**
- Modify: `python_statement/health.py:60-98` (the `check_scraper` classmethod)
- Test: `tests/test_health.py` (new file)

**Step 1: Write the failing tests**

Create `tests/test_health.py`:

```python
#!/usr/bin/env python3
"""Unit tests for HealthChecker."""

import datetime
import unittest
from unittest.mock import patch

from python_statement.health import HealthChecker


class TestCheckScraperLatestDate(unittest.TestCase):
    """Tests for the latest_date field added to check_scraper()."""

    @patch('python_statement.health.Scraper.run_scraper')
    def test_latest_date_is_max_date_as_iso_string(self, mock_run):
        mock_run.return_value = [
            {'title': 'Older', 'date': datetime.date(2026, 6, 1)},
            {'title': 'Newest', 'date': datetime.date(2026, 7, 15)},
            {'title': 'Middle', 'date': datetime.date(2026, 6, 20)},
        ]
        result = HealthChecker.check_scraper('somemember')
        self.assertEqual(result['latest_date'], '2026-07-15')

    @patch('python_statement.health.Scraper.run_scraper')
    def test_latest_date_is_none_when_no_dates(self, mock_run):
        mock_run.return_value = [
            {'title': 'No date', 'date': None},
        ]
        result = HealthChecker.check_scraper('somemember')
        self.assertIsNone(result['latest_date'])

    @patch('python_statement.health.Scraper.run_scraper')
    def test_latest_date_is_none_when_empty(self, mock_run):
        mock_run.return_value = []
        result = HealthChecker.check_scraper('somemember')
        self.assertIsNone(result['latest_date'])


if __name__ == '__main__':
    unittest.main()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_health.py -v`
Expected: FAIL — `KeyError: 'latest_date'` (the key doesn't exist yet).

**Step 3: Write minimal implementation**

In `python_statement/health.py`, inside `check_scraper`, add `'latest_date': None` to the initial `result` dict (near the other keys), then compute it right after `result['has_dates']` is set:

```python
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
            result['has_dates'] = any(
                item.get('date') is not None for item in data
            )

            dates = [item['date'] for item in data if item.get('date') is not None]
            if dates:
                result['latest_date'] = max(dates).isoformat()

            if not result['has_dates']:
                result['status'] = 'no_dates'
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_health.py -v`
Expected: PASS (3 tests).

**Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest tests/ -q`
Expected: all existing tests still PASS.

**Step 6: Commit**

```bash
git add python_statement/health.py tests/test_health.py
git commit -m "Add latest_date to health check results"
```

---

### Task 2: Compute `days_since` / `is_stale` in `build_dashboard.py`

**Files:**
- Modify: `scripts/build_dashboard.py:1-15` (imports) and `:60-66` (`enrich_results`)
- Test: `tests/test_build_dashboard.py` (new file)

**Step 1: Write the failing tests**

Create `tests/test_build_dashboard.py`:

```python
#!/usr/bin/env python3
"""Unit tests for the dashboard's stale-scraper enrichment."""

import datetime
import unittest
from unittest.mock import patch

from scripts.build_dashboard import enrich_results


class TestEnrichResultsStaleness(unittest.TestCase):
    """Tests for days_since / is_stale added to enrich_results()."""

    @patch('scripts.build_dashboard.datetime')
    def test_marks_ok_scraper_stale_at_30_days(self, mock_datetime):
        mock_datetime.date.today.return_value = datetime.date(2026, 8, 9)
        mock_datetime.date.fromisoformat = datetime.date.fromisoformat
        results = [
            {'name': 'stale_member', 'status': 'ok', 'latest_date': '2026-07-10'},
        ]
        enrich_results(results)
        self.assertEqual(results[0]['days_since'], 30)
        self.assertTrue(results[0]['is_stale'])

    @patch('scripts.build_dashboard.datetime')
    def test_does_not_mark_recent_ok_scraper_stale(self, mock_datetime):
        mock_datetime.date.today.return_value = datetime.date(2026, 8, 9)
        mock_datetime.date.fromisoformat = datetime.date.fromisoformat
        results = [
            {'name': 'fresh_member', 'status': 'ok', 'latest_date': '2026-08-01'},
        ]
        enrich_results(results)
        self.assertEqual(results[0]['days_since'], 8)
        self.assertFalse(results[0]['is_stale'])

    def test_error_status_is_never_stale(self):
        results = [
            {'name': 'broken_member', 'status': 'error', 'latest_date': None},
        ]
        enrich_results(results)
        self.assertIsNone(results[0]['days_since'])
        self.assertFalse(results[0]['is_stale'])


if __name__ == '__main__':
    unittest.main()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build_dashboard.py -v`
Expected: FAIL — `KeyError: 'days_since'` (import of `enrich_results` succeeds, since it already exists, but new fields are missing).

**Step 3: Write minimal implementation**

`scripts/build_dashboard.py` already does `import datetime`? Check — currently it does not. Add `import datetime` near the top with the other stdlib imports (`html`, `json`, `os`, `sys`, `urllib.parse`).

Update `enrich_results`:

```python
def enrich_results(results):
    """Add url_base/method from config, plus staleness fields, to each result."""
    today = datetime.date.today()
    for r in results:
        name = r["name"]
        cfg = SCRAPER_CONFIG.get(name, {})
        r["url_base"] = cfg.get("url_base", "")
        r["config_method"] = cfg.get("method", "custom")

        latest_date = r.get("latest_date")
        days_since = None
        if latest_date:
            days_since = (today - datetime.date.fromisoformat(latest_date)).days
        r["days_since"] = days_since
        r["is_stale"] = r.get("status") == "ok" and days_since is not None and days_since >= 30
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_build_dashboard.py -v`
Expected: PASS (3 tests).

**Step 5: Commit**

```bash
git add scripts/build_dashboard.py tests/test_build_dashboard.py
git commit -m "Compute days-since-release and staleness in dashboard build"
```

---

### Task 3: Render staleness in the health table (columns, badge, filter, stat card)

**Files:**
- Modify: `scripts/build_dashboard.py` (`build_html`, the row-building loop around `:130-165`, the `<table>` header around `:250-260`, the status `<select>` around `:230-238`, the summary stat cards around `:210-216`, and the JS `applyFilters()` function around `:400-415`)

No new automated test for this task — it's HTML/JS string generation. Verify manually per Step 3 below (this project has no existing tests that assert on generated HTML strings; follow that convention).

**Step 1: Add columns to each table row**

In the row-building loop in `build_html`, after `error = r.get("error", "")`, add:

```python
        latest_date = r.get("latest_date") or ""
        days_since = r.get("days_since")
        days_since_cell = str(days_since) if days_since is not None else ""
        stale_badge = (
            ' <span class="badge badge-stale">stale</span>' if r.get("is_stale") else ""
        )
```

Update the row template to insert `latest_date`, `days_since_cell` cells, and append `stale_badge` to the status cell:

```python
        rows_html.append(
            f"<tr>"
            f"<td>{name}</td>"
            f'<td><span class="badge {badge_cls}"{error_attr}>{status}</span>{stale_badge}</td>'
            f"<td>{count}</td>"
            f"<td>{duration}</td>"
            f"<td>{html.escape(latest_date)}</td>"
            f"<td>{days_since_cell}</td>"
            f"<td>{method}</td>"
            f'<td class="url-cell">{url_cell}</td>'
            f"<td>{action_cell}</td>"
            f"</tr>"
        )
```

**Step 2: Add matching `<th>` headers**

In the `<table id="scraperTable">` header, insert two new `<th>` between "Duration (ms)" and "Method", renumbering the `data-col` indices for every subsequent header (Method/URL/Actions don't currently have `data-col` beyond index 4, so only "Method"'s column shifts — check current markup and renumber consistently):

```html
<th data-col="0">Name</th>
<th data-col="1">Status</th>
<th data-col="2">Count</th>
<th data-col="3">Duration (ms)</th>
<th data-col="4">Latest Release</th>
<th data-col="5">Days Since</th>
<th data-col="6">Method</th>
<th>URL</th>
<th>Actions</th>
```

**Step 3: Manually verify sort behavior for the new numeric column**

The existing sort JS special-cases numeric columns with `if (col >= 2 && col <= 3)`. Extend this range to include the new "Days Since" column (index 5): change to `if ((col >= 2 && col <= 3) || col === 5)`. Leave "Latest Release" (index 4) as string-sorted — ISO dates sort correctly as strings.

**Step 4: Add the `badge-stale` CSS class**

In the `<style>` block, alongside the other `.badge-*` rules, add:

```css
  .badge-stale { background: #fdcb6e22; color: #e09a00; margin-left: 4px; }
```

**Step 5: Add "Stale" to the status filter and update `applyFilters()`**

In the `<select id="statusFilter">`, add an option:

```html
<option value="stale">Stale (30+ days)</option>
```

The existing `applyFilters()` JS matches `rowStatus` against the literal status-cell text. Since the status cell now may contain "ok stale" (badge text included), matching a plain `status` value would break. Give the `<tr>` a `data-status` and `data-stale` attribute instead, set from Python when building each row:

```python
        rows_html.append(
            f'<tr data-status="{status}" data-stale="{"1" if r.get("is_stale") else "0"}">'
            ...
        )
```

Update `applyFilters()`:

```js
function applyFilters() {
  const search = searchInput.value.toLowerCase();
  const status = statusFilter.value;
  const rows = tbody.querySelectorAll('tr');
  let visible = 0;
  rows.forEach(row => {
    const name = row.children[0].textContent.toLowerCase();
    const rowStatus = row.dataset.status;
    const rowStale = row.dataset.stale === '1';
    const matchName = !search || name.includes(search);
    const matchStatus = !status || (status === 'stale' ? rowStale : rowStatus === status);
    row.classList.toggle('hidden', !(matchName && matchStatus));
    if (matchName && matchStatus) visible++;
  });
  countDisplay.textContent = visible + ' of ' + rows.length + ' scrapers';
}
```

**Step 6: Add a Stale summary stat card**

Compute the count in `build_html` near where `summary` is unpacked:

```python
    stale_count = sum(1 for r in results if r.get("is_stale"))
```

Add a stat card in the `.summary` div, after the existing `rate` card:

```html
<div class="stat-card stale"><div class="label">Stale</div><div class="value">{stale_count}</div></div>
```

Add its color in `<style>`:

```css
  .stat-card.stale .value { color: #e09a00; }
```

**Step 7: Manually verify**

Since `health_results.json` won't have `latest_date` for old entries until a fresh check runs, generate a small fixture and eyeball the output:

```bash
uv run python -c "
import json, datetime
report = {
    'timestamp': datetime.datetime.now().isoformat(),
    'mode': 'quick',
    'summary': {'total': 2, 'ok': 2, 'empty': 0, 'no_dates': 0, 'errors': 0, 'success_rate': 100.0},
    'results': [
        {'name': 'freshmember', 'status': 'ok', 'count': 5, 'has_dates': True, 'latest_date': str(datetime.date.today()), 'duration_ms': 100, 'error': None},
        {'name': 'stalemember', 'status': 'ok', 'count': 5, 'has_dates': True, 'latest_date': str(datetime.date.today() - datetime.timedelta(days=45)), 'duration_ms': 100, 'error': None},
    ],
}
json.dump(report, open('/tmp/health_results_test.json', 'w'))
"
cp health_results.json /tmp/health_results_backup.json 2>/dev/null || true
cp /tmp/health_results_test.json health_results.json
uv run python scripts/build_dashboard.py
open docs/index.html   # or: python -m http.server --directory docs, then visit in a browser
```

Confirm: `stalemember` shows a "stale" badge and appears when the status filter is set to "Stale (30+ days)"; `freshmember` does not. Then restore the real results file:

```bash
mv /tmp/health_results_backup.json health_results.json 2>/dev/null || git checkout -- health_results.json
uv run python scripts/build_dashboard.py
```

**Step 8: Run the full test suite**

Run: `uv run pytest tests/ -q`
Expected: all tests PASS (no test asserts on `build_html` output, so this just guards against import/syntax errors).

**Step 9: Commit**

```bash
git add scripts/build_dashboard.py
git commit -m "Show latest release date and stale badge in health dashboard table"
```

---

### Task 4: Update `CLAUDE.md` health-check documentation (optional, do last)

**Files:**
- Modify: `CLAUDE.md` (the "Health Monitoring" / `HealthChecker` sections)

**Step 1:** Add a one-line note under `check_scraper(name)` in the `HealthChecker class` bullet list: mention it now also returns `latest_date`.

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Document latest_date field in health check docs"
```
