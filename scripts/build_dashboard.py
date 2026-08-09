#!/usr/bin/env python3
"""
Generate a static HTML health dashboard from health_results.json.

Reads health check data and scraper config, produces docs/index.html
for deployment on GitHub Pages.
"""

import datetime
import html
import json
import os
import sys
import urllib.parse
from pathlib import Path

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from python_statement.config import SCRAPER_CONFIG

REPO = "dwillis/python-statement"
RESULTS_FILE = "health_results.json"
HISTORY_FILE = "health_history.jsonl"
LEGISLATORS_FILE = "legislators_with_scrapers.json"
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")


def load_results(path):
    with open(path) as f:
        return json.load(f)


def load_history(path):
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_legislators(path):
    """Load legislators and split into matched/unmatched."""
    if not os.path.exists(path):
        return [], []
    with open(path) as f:
        data = json.load(f)
    matched = [l for l in data if l.get("scraper_method")]
    unmatched = [l for l in data if not l.get("scraper_method")]
    return matched, unmatched


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


def issue_url(name, status, url_base, error):
    """Build a GitHub new-issue URL with pre-filled fields."""
    title = f"Scraper failing: {name}"
    lines = [
        f"**Scraper:** `{name}`",
        f"**Status:** {status}",
        f"**URL:** {url_base}" if url_base else "",
        f"**Error:** {error}" if error else "",
        "",
        "---",
        "*Created from the health dashboard*",
    ]
    body = "\n".join(l for l in lines if l or l == "")
    params = urllib.parse.urlencode(
        {"title": title, "body": body, "labels": "scraper-health"}
    )
    return f"https://github.com/{REPO}/issues/new?{params}"


def build_html(report, history, matched_legislators=None, unmatched_legislators=None):
    summary = report["summary"]
    timestamp = report["timestamp"]
    results = report["results"]
    matched_legislators = matched_legislators or []
    unmatched_legislators = unmatched_legislators or []

    enrich_results(results)

    # Build missing members table rows
    missing_rows_html = []
    for leg in sorted(unmatched_legislators, key=lambda l: (l["type"], l["state"], l["official_full"])):
        name = html.escape(leg["official_full"])
        state = html.escape(leg["state"])
        chamber = "Senate" if leg["type"] == "sen" else "House"
        party = html.escape(leg.get("party", ""))
        url = leg.get("url", "")
        url_cell = (
            f'<a href="{html.escape(url)}" target="_blank" rel="noopener">'
            f"{html.escape(url)}</a>"
            if url
            else ""
        )
        missing_rows_html.append(
            f"<tr>"
            f"<td>{name}</td>"
            f"<td>{chamber}</td>"
            f"<td>{state}</td>"
            f"<td>{party}</td>"
            f'<td class="url-cell">{url_cell}</td>'
            f"</tr>"
        )
    missing_table_rows = "\n".join(missing_rows_html)

    total_legislators = len(matched_legislators) + len(unmatched_legislators)
    coverage_pct = (
        round(len(matched_legislators) / total_legislators * 100)
        if total_legislators
        else 0
    )

    # Build table rows
    rows_html = []
    for r in results:
        name = html.escape(r["name"])
        status = r["status"]
        badge_cls = {
            "ok": "badge-ok",
            "empty": "badge-empty",
            "no_dates": "badge-nodates",
            "error": "badge-error",
        }.get(status, "")
        count = r["count"]
        duration = r["duration_ms"]
        method = html.escape(r["config_method"])
        url_base = r["url_base"]
        error = r.get("error", "")

        url_cell = (
            f'<a href="{html.escape(url_base)}" target="_blank" rel="noopener">'
            f"{html.escape(url_base)}</a>"
            if url_base
            else ""
        )

        if status != "ok":
            issue_link = issue_url(r["name"], status, url_base, error)
            action_cell = (
                f'<a href="{html.escape(issue_link)}" target="_blank" '
                f'rel="noopener" class="btn-issue">Report Issue</a>'
            )
        else:
            action_cell = ""

        error_attr = f' title="{html.escape(error)}"' if error else ""

        rows_html.append(
            f"<tr>"
            f"<td>{name}</td>"
            f'<td><span class="badge {badge_cls}"{error_attr}>{status}</span></td>'
            f"<td>{count}</td>"
            f"<td>{duration}</td>"
            f"<td>{method}</td>"
            f'<td class="url-cell">{url_cell}</td>'
            f"<td>{action_cell}</td>"
            f"</tr>"
        )

    table_rows = "\n".join(rows_html)

    # Trend data for Chart.js
    trend_labels = json.dumps([e.get("timestamp", "")[:10] for e in history])
    trend_ok = json.dumps([e.get("ok", 0) for e in history])
    trend_empty = json.dumps([e.get("empty", 0) for e in history])
    trend_errors = json.dumps([e.get("errors", 0) for e in history])

    has_history = len(history) > 1

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scraper Health Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f6fa; color: #2d3436; padding: 24px; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .subtitle {{ color: #636e72; font-size: 0.9rem; margin-bottom: 24px; }}
  .tabs {{ display: flex; gap: 0; margin-bottom: 24px; border-bottom: 2px solid #dfe6e9; }}
  .tab {{ padding: 10px 24px; cursor: pointer; font-size: 0.95rem; font-weight: 600; color: #636e72; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.2s; }}
  .tab:hover {{ color: #2d3436; }}
  .tab.active {{ color: #0984e3; border-bottom-color: #0984e3; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .summary {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
  .stat-card {{ background: #fff; border-radius: 8px; padding: 16px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 120px; }}
  .stat-card .label {{ font-size: 0.8rem; color: #636e72; text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-card .value {{ font-size: 1.8rem; font-weight: 700; }}
  .stat-card.ok .value {{ color: #00b894; }}
  .stat-card.empty .value {{ color: #fdcb6e; }}
  .stat-card.nodates .value {{ color: #e17055; }}
  .stat-card.error .value {{ color: #d63031; }}
  .stat-card.rate .value {{ color: #0984e3; }}
  .stat-card.missing .value {{ color: #6c5ce7; }}
  .chart-container {{ background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 24px; max-width: 800px; }}
  .controls {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }}
  .controls input {{ padding: 8px 12px; border: 1px solid #dfe6e9; border-radius: 6px; font-size: 0.9rem; width: 250px; }}
  .controls select {{ padding: 8px 12px; border: 1px solid #dfe6e9; border-radius: 6px; font-size: 0.9rem; background: #fff; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  th {{ background: #dfe6e9; padding: 10px 12px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer; user-select: none; white-space: nowrap; }}
  th:hover {{ background: #c8d6e5; }}
  td {{ padding: 8px 12px; border-top: 1px solid #f1f2f6; font-size: 0.9rem; }}
  tr:hover {{ background: #f8f9fa; }}
  .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }}
  .badge-ok {{ background: #00b89422; color: #00b894; }}
  .badge-empty {{ background: #fdcb6e22; color: #e09a00; }}
  .badge-nodates {{ background: #e1705522; color: #e17055; }}
  .badge-error {{ background: #d6303122; color: #d63031; }}
  .badge-senate {{ background: #6c5ce722; color: #6c5ce7; }}
  .badge-house {{ background: #0984e322; color: #0984e3; }}
  .btn-issue {{ display: inline-block; padding: 4px 10px; background: #0984e3; color: #fff; border-radius: 4px; font-size: 0.8rem; text-decoration: none; white-space: nowrap; }}
  .btn-issue:hover {{ background: #0773c5; }}
  .url-cell {{ max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .url-cell a {{ color: #0984e3; text-decoration: none; }}
  .url-cell a:hover {{ text-decoration: underline; }}
  .hidden {{ display: none; }}
  .count-display {{ color: #636e72; font-size: 0.9rem; }}
</style>
</head>
<body>

<h1>Scraper Health Dashboard</h1>
<p class="subtitle">Last updated: {html.escape(timestamp)} &middot; Mode: {html.escape(report["mode"])}</p>

<div class="tabs">
  <div class="tab active" data-tab="health">Scraper Health</div>
  <div class="tab" data-tab="missing">Missing Members <span class="badge badge-error">{len(unmatched_legislators)}</span></div>
</div>

<!-- Health Tab -->
<div id="tab-health" class="tab-panel active">

<div class="summary">
  <div class="stat-card ok"><div class="label">OK</div><div class="value">{summary["ok"]}</div></div>
  <div class="stat-card empty"><div class="label">Empty</div><div class="value">{summary["empty"]}</div></div>
  <div class="stat-card nodates"><div class="label">No Dates</div><div class="value">{summary["no_dates"]}</div></div>
  <div class="stat-card error"><div class="label">Errors</div><div class="value">{summary["errors"]}</div></div>
  <div class="stat-card rate"><div class="label">Success Rate</div><div class="value">{summary["success_rate"]}%</div></div>
</div>

{"" if not has_history else '''
<div class="chart-container">
  <canvas id="trendChart" height="80"></canvas>
</div>
'''}

<div class="controls">
  <input type="text" id="searchInput" placeholder="Search by name...">
  <select id="statusFilter">
    <option value="">All statuses</option>
    <option value="ok">OK</option>
    <option value="empty">Empty</option>
    <option value="no_dates">No Dates</option>
    <option value="error">Error</option>
  </select>
  <span class="count-display" id="countDisplay"></span>
</div>

<table id="scraperTable">
  <thead>
    <tr>
      <th data-col="0">Name</th>
      <th data-col="1">Status</th>
      <th data-col="2">Count</th>
      <th data-col="3">Duration (ms)</th>
      <th data-col="4">Method</th>
      <th>URL</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>

</div>

<!-- Missing Members Tab -->
<div id="tab-missing" class="tab-panel">

<div class="summary">
  <div class="stat-card ok"><div class="label">Covered</div><div class="value">{len(matched_legislators)}</div></div>
  <div class="stat-card missing"><div class="label">Missing</div><div class="value">{len(unmatched_legislators)}</div></div>
  <div class="stat-card rate"><div class="label">Coverage</div><div class="value">{coverage_pct}%</div></div>
</div>

<p style="color: #636e72; margin-bottom: 16px; font-size: 0.9rem;">
  Current members of Congress without a working scraper.
  Coverage: {len(matched_legislators)} of {total_legislators} legislators matched.
</p>

<div class="controls">
  <input type="text" id="missingSearchInput" placeholder="Search by name or state...">
  <select id="chamberFilter">
    <option value="">All chambers</option>
    <option value="Senate">Senate</option>
    <option value="House">House</option>
  </select>
  <select id="partyFilter">
    <option value="">All parties</option>
    <option value="Democrat">Democrat</option>
    <option value="Republican">Republican</option>
    <option value="Independent">Independent</option>
  </select>
  <span class="count-display" id="missingCountDisplay"></span>
</div>

<table id="missingTable">
  <thead>
    <tr>
      <th data-col="0">Name</th>
      <th data-col="1">Chamber</th>
      <th data-col="2">State</th>
      <th data-col="3">Party</th>
      <th>Website</th>
    </tr>
  </thead>
  <tbody>
    {missing_table_rows}
  </tbody>
</table>

</div>

<script>
// Tab switching
document.querySelectorAll('.tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  }});
}});

// Health table sorting
const table = document.getElementById('scraperTable');
const tbody = table.querySelector('tbody');
let sortCol = -1, sortAsc = true;

table.querySelectorAll('th[data-col]').forEach(th => {{
  th.addEventListener('click', () => {{
    const col = parseInt(th.dataset.col);
    if (sortCol === col) sortAsc = !sortAsc;
    else {{ sortCol = col; sortAsc = true; }}
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {{
      let va = a.children[col].textContent.trim();
      let vb = b.children[col].textContent.trim();
      if (col >= 2 && col <= 3) {{ va = parseInt(va) || 0; vb = parseInt(vb) || 0; return sortAsc ? va - vb : vb - va; }}
      return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    }});
    rows.forEach(r => tbody.appendChild(r));
  }});
}});

// Health table filtering
const searchInput = document.getElementById('searchInput');
const statusFilter = document.getElementById('statusFilter');
const countDisplay = document.getElementById('countDisplay');

function applyFilters() {{
  const search = searchInput.value.toLowerCase();
  const status = statusFilter.value;
  const rows = tbody.querySelectorAll('tr');
  let visible = 0;
  rows.forEach(row => {{
    const name = row.children[0].textContent.toLowerCase();
    const rowStatus = row.children[1].textContent.trim();
    const matchName = !search || name.includes(search);
    const matchStatus = !status || rowStatus === status;
    row.classList.toggle('hidden', !(matchName && matchStatus));
    if (matchName && matchStatus) visible++;
  }});
  countDisplay.textContent = visible + ' of ' + rows.length + ' scrapers';
}}

searchInput.addEventListener('input', applyFilters);
statusFilter.addEventListener('change', applyFilters);
applyFilters();

// Missing table sorting
const missingTable = document.getElementById('missingTable');
const missingTbody = missingTable.querySelector('tbody');
let missingSortCol = -1, missingSortAsc = true;

missingTable.querySelectorAll('th[data-col]').forEach(th => {{
  th.addEventListener('click', () => {{
    const col = parseInt(th.dataset.col);
    if (missingSortCol === col) missingSortAsc = !missingSortAsc;
    else {{ missingSortCol = col; missingSortAsc = true; }}
    const rows = Array.from(missingTbody.querySelectorAll('tr'));
    rows.sort((a, b) => {{
      let va = a.children[col].textContent.trim();
      let vb = b.children[col].textContent.trim();
      return missingSortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    }});
    rows.forEach(r => missingTbody.appendChild(r));
  }});
}});

// Missing table filtering
const missingSearchInput = document.getElementById('missingSearchInput');
const chamberFilter = document.getElementById('chamberFilter');
const partyFilter = document.getElementById('partyFilter');
const missingCountDisplay = document.getElementById('missingCountDisplay');

function applyMissingFilters() {{
  const search = missingSearchInput.value.toLowerCase();
  const chamber = chamberFilter.value;
  const party = partyFilter.value;
  const rows = missingTbody.querySelectorAll('tr');
  let visible = 0;
  rows.forEach(row => {{
    const name = row.children[0].textContent.toLowerCase();
    const rowChamber = row.children[1].textContent.trim();
    const state = row.children[2].textContent.toLowerCase();
    const rowParty = row.children[3].textContent.trim();
    const matchSearch = !search || name.includes(search) || state.includes(search);
    const matchChamber = !chamber || rowChamber === chamber;
    const matchParty = !party || rowParty === party;
    row.classList.toggle('hidden', !(matchSearch && matchChamber && matchParty));
    if (matchSearch && matchChamber && matchParty) visible++;
  }});
  missingCountDisplay.textContent = visible + ' of ' + rows.length + ' missing members';
}}

missingSearchInput.addEventListener('input', applyMissingFilters);
chamberFilter.addEventListener('change', applyMissingFilters);
partyFilter.addEventListener('change', applyMissingFilters);
applyMissingFilters();
</script>

{"" if not has_history else f'''
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>
new Chart(document.getElementById("trendChart"), {{
  type: "line",
  data: {{
    labels: {trend_labels},
    datasets: [
      {{ label: "OK", data: {trend_ok}, borderColor: "#00b894", backgroundColor: "#00b89422", fill: true, tension: 0.3 }},
      {{ label: "Empty", data: {trend_empty}, borderColor: "#fdcb6e", backgroundColor: "#fdcb6e22", fill: true, tension: 0.3 }},
      {{ label: "Errors", data: {trend_errors}, borderColor: "#d63031", backgroundColor: "#d6303122", fill: true, tension: 0.3 }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{ title: {{ display: true, text: "Health Trend" }} }},
    scales: {{ y: {{ beginAtZero: true }} }}
  }}
}});
</script>
'''}

</body>
</html>"""


def main():
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)

    if not os.path.exists(RESULTS_FILE):
        print(f"Error: {RESULTS_FILE} not found. Run a health check first.")
        sys.exit(1)

    report = load_results(RESULTS_FILE)
    history = load_history(HISTORY_FILE)
    matched_legislators, unmatched_legislators = load_legislators(LEGISLATORS_FILE)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    page_html = build_html(report, history, matched_legislators, unmatched_legislators)
    with open(OUTPUT_FILE, "w") as f:
        f.write(page_html)

    print(f"Dashboard generated: {OUTPUT_FILE}")
    print(f"  {report['summary']['total']} scrapers, "
          f"{len(history)} history entries")
    if matched_legislators or unmatched_legislators:
        total = len(matched_legislators) + len(unmatched_legislators)
        print(f"  {len(matched_legislators)}/{total} legislators covered, "
              f"{len(unmatched_legislators)} missing")


if __name__ == "__main__":
    main()
