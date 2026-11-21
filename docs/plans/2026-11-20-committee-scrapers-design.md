# Plan: Committee press release collection

> **Status (2026-11-21): implemented.** Final state, and where it differs from the plan below:
> - `COMMITTEE_CONFIG` has 84 verified entries covering 45 of the 49 committees in the YAML. `COMMITTEE_SKIP` holds the other 4 (HSQJ, JSLC, JSPR, JSTX). A live health check passed on all 84.
> - HSZS (Select Committee on the CCP) has no URL in the YAML but is covered (both sides).
> - Discovery assigns `side` from the final host's party label and a configurable majority party; the YAML's `minority_url` values were stale. It also flags listings whose newest item is 90+ days old (likely archives) and reports listing URLs where no pattern matched.
> - Two entries can't paginate: `hsif_majority` (Next.js, latest 9 only) and `slet_full` (whole archive on one page).
> - The four legacy `senate_approps_*`/`senate_banking_*` methods were replaced by `ssap_*`/`ssbk_*` entries and deleted. `house_gop` (leadership, not a committee) remains.
> - `committee_methods()` now returns names, and `committee_scrapers()` exists.
> - The health check, CLI (`--collection committees`), weekly CI, nightly coverage JSON and the dashboard Committees tab are all in place. The issue body now has member and committee sections.

## Context

python-statement scrapes ~538 member sites through one dict, `SCRAPER_CONFIG`, and everything downstream (health checks, dashboard, legislators JSON, backfill) reads that dict and assumes "scraper = member". Committee coverage today is five hand-written methods in `scraper.py` (`senate_approps_*`, `senate_banking_*`, `house_gop`) that are in no config, no health check and no test; `committee_scrapers()` is documented in CLAUDE.md but does not exist.

Goal: a committee collection that is separate from members end to end (config, enumeration, health, output), covers majority **and** minority sites, and is anchored to `committees-current.yaml` from unitedstates/congress-legislators the same way members are anchored to `legislators-current.yaml`.

### What the canonical YAML gives us (checked 2026-11-20)

- 49 committees: 23 House, 21 Senate, 5 joint. Stable key: `thomas_id` (e.g. `HSAG`, `SSFI`).
- 47 have `url`; 20 have `minority_url` (House only). Senate minority press pages live on the majority domain and are not in the YAML.
- 13 `rss_url` / 10 `minority_rss_url`, mostly old ColdFusion URLs; assume dead until proven live.
- Known staleness to design around: Senate URLs are `http://www.`; some House `minority_url` values still point at `republicans-*` hosts even though the party labels have flipped; `HSZS` and `HSQJ` have no URL; `JSLC`/`JSPR` are sub-pages of cha.house.gov.

So the YAML is canonical for **which committees exist and their identity**; press-page URLs and majority/minority assignment must be resolved live and stored in our config.

## Design

### 1. Separate config, shared engine

New file `python_statement/committee_config.py` with `COMMITTEE_CONFIG`, same entry shape as `SCRAPER_CONFIG` plus two required metadata keys:

```python
'hsag_majority': {
    'thomas_id': 'HSAG',
    'side': 'majority',          # majority | minority | full (one shared/nonpartisan newsroom)
    'method': 'generic',
    'url_base': 'https://agriculture.house.gov/news/documentquery.aspx?DocumentTypeID=1',
    'container': ..., 'title_sel': ..., 'date_sel': ..., 'pagination': ...,
},
```

- Key convention: `<thomas_id lowercase>_<side>`. Guarantees no collision with member names.
- `COMMITTEE_SKIP = {'JSPR': 'no press releases; sub-page of cha.house.gov', ...}` for committees deliberately not scraped.
- Prefer `method: 'generic'` (or `rss` only when a feed is verified live and no HTML listing matches). HTML is preferred because pagination allows backfill.

Engine changes in `python_statement/scraper.py` (small, no behaviour change for members):
- Add `Scraper.COMMITTEE_CONFIG` and a `_get_config(name)` helper that checks both dicts; use it at the two lookups in `run_scraper` (~line 73) and `generic_scraper` (~line 142).
- Extend the wrapper auto-generation loop (~line 1687) to committee keys.
- `committee_methods()` returns `sorted(COMMITTEE_CONFIG)` (names, matching `member_methods()`); add the missing `committee_scrapers(page=1)` that runs them all.
- In `run_scraper`, when the config has `thomas_id`, tag each result with `committee` (thomas_id) and `side`. Member results are unchanged.
- Batch methods need no change: `run_scraper` already passes `[url_base]` explicitly.

Validation in `python_statement/config.py`: refactor `validate_config()` to take a config dict plus extra allowed/required keys; call it for both dicts at import. Committee-specific checks: `thomas_id` and `side` present, `side` valid, key equals `<thomas_id>_<side>`, no key shared with `SCRAPER_CONFIG`.

### 2. Sync with the canonical YAML

New `scripts/generate_committees.py`, modelled on `scripts/generate_legislators.py` (reuse its fetch/`yaml.safe_load` approach):
- Fetches `committees-current.yaml`, joins on `thomas_id`.
- Writes `committees_with_scrapers.json` (thomas_id, name, type/chamber, url, minority_url, list of `{scraper_method, side, url_base}`) and `committees_without_scrapers.json` (in YAML, not in config, not in `COMMITTEE_SKIP`).
- Flags config entries whose `thomas_id` is no longer in the YAML (committee dissolved/renamed).
- Subcommittees (181) are out of scope: they almost never have their own newsroom.

### 3. Discovery tooling

New `scripts/discover_committee_press.py` to produce draft configs instead of hand-inspecting ~90 sites:
- For each YAML `url` / `minority_url`: follow redirects to the live host, read the host prefix (`democrats-`, `republicans-`, `gop-`) to assign `side`, rather than trusting the YAML field name.
- Probe candidate press paths, reusing `HOUSE_PATHS` / `SENATE_PATHS` from `scripts/find_missing_scrapers.py` plus committee ones (`/news/majority`, `/news/minority`, `/newsroom/majority-press-releases`, `/chairman/newsroom`, `/ranking-member/...`).
- Run `PATTERNS` / `try_pattern` and `verify_config` from `scripts/detect_pattern.py` on each hit; test any `rss_url` with `Feed.from_rss`.
- Output: a report of ready-to-paste entries, plus a list of sites needing manual selectors.

### 4. Populate configs in batches

Each entry verified per CLAUDE.md: page 1 returns results, page 2 differs, dates parse, URLs absolute.
1. Senate Appropriations and Banking: port the four legacy custom methods to config entries, then delete the custom methods.
2. House majority (21) — expect a few shared templates.
3. House minority (20).
4. Senate (21 committees; majority + minority listings, or `full` where the newsroom is shared).
5. Joint (JEC, CSCE, JCT) and decide `COMMITTEE_SKIP` entries (JSLC, JSPR, HSZS, HSQJ, likely Ethics).

Sites matching no pattern get custom selectors in a `generic` entry; a custom method only as a last resort. `house_gop` is leadership, not a committee: leave it alone.

### 5. Health monitoring as a separate collection

- `python_statement/health.py`: `HealthChecker.run(..., collection='members')`; `collection='committees'` enumerates `committee_methods()` and always runs all (~90, no quick sample).
- `scripts/run_health_check.py`: `--collection committees`, writing `committee_health_results.json` / `committee_health_history.jsonl` so member history stays clean.
- `Makefile`: `health-committees`, `generate-committees`.
- `.github/workflows/scraper-health.yml`: add a committee run + commit of the new files; nightly `generate-committees` alongside the legislators job.
- `scripts/build_dashboard.py`: add a "Committees" tab (health by committee and side, uncovered committees). Do this last; it is the only optional piece.

### 6. Docs

Save this design as `docs/plans/2026-11-20-committee-scrapers-design.md`; update CLAUDE.md, README.md and SCRAPER_GUIDE.md (committee section, key convention, corrected `committee_scrapers()` docs).

## Order of work

1. Engine + validation + offline tests (sections 1).
2. `generate_committees.py` (section 2) — gives the coverage to-do list.
3. Discovery script (section 3).
4. Config batches (section 4), committing per batch.
5. Health/CI/Makefile, then dashboard tab (section 5).
6. Docs and removal of legacy methods (section 6).

## Files

- New: `python_statement/committee_config.py`, `scripts/generate_committees.py`, `scripts/discover_committee_press.py`, `tests/test_committees.py`
- Modified: `python_statement/scraper.py`, `python_statement/config.py`, `python_statement/health.py`, `scripts/run_health_check.py`, `scripts/build_dashboard.py`, `scripts/generate_legislators.py` (skip set), `Makefile`, `.github/workflows/*.yml`, docs

## Verification

- `uv run pytest tests/` — new offline tests: validation rejects bad `side`/missing `thomas_id`/key mismatch/name collision; `run_scraper` on a committee entry with patched `open_html` returns results tagged `committee` and `side`; member results carry no new keys; `committee_methods()` lists only committee keys.
- Per entry: `Scraper.run_scraper('hsag_majority', 1)` and page 2, checking dates and absolute URLs.
- `uv run python scripts/generate_committees.py` — `committees_without_scrapers.json` is empty once batches are done (everything is configured or in `COMMITTEE_SKIP`).
- `uv run python scripts/run_health_check.py --collection committees --save` — all ok; `make health-quick` unchanged for members.
