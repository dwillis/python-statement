# Scraper Consolidation & Health Monitoring Design

**Date:** 2026-03-25
**Status:** Proposed

## Problem

python-statement has ~125 custom scraper methods with duplicated logic alongside 312 config-driven scrapers. The custom scrapers account for most of the 6,265-line statement.py and are the primary maintenance burden. There's no automated way to detect when scrapers break, and adding new scrapers requires understanding which pattern to use.

## Goals

1. Consolidate ~100-110 custom scrapers into config-driven entries using a universal dispatcher
2. Add health monitoring (CLI + GitHub Actions) to detect broken scrapers
3. Build a pattern detection tool to streamline adding new scrapers
4. Split the monolithic file into manageable modules

## Design

### 1. Universal Dispatcher + Rich Config Schema

A single `generic_scraper()` method reads config and extracts data using CSS selectors:

```python
'member_name': {
    'method': 'generic',
    'url_base': 'https://member.senate.gov/press',
    'container': 'div.ArticleBlock',       # Container for each press release
    'title_sel': 'h2 a',                   # Title + link selector
    'date_sel': '.ArticleBlock__date',     # Date selector
    'date_fmt': ['%B %d, %Y'],            # Date format(s) to try
    'pagination': '?pagenum_rs={page}',   # Pagination pattern
    'link_attr': 'href',                   # Optional: URL attribute (default: href)
    'date_attr': None,                     # Optional: date attribute (e.g., 'datetime')
    'link_sel': None,                      # Optional: separate link selector
    'base_domain': None,                   # Optional: domain override for relative URLs
}
```

The dispatcher:
1. Builds paginated URL from `url_base` + `pagination`
2. Fetches HTML via `open_html()`
3. Finds containers via `container` selector
4. Extracts title/URL from `title_sel` (or `link_sel`), date from `date_sel`
5. Parses date using `date_fmt` list with fallbacks
6. Returns standard result dicts

Existing generic methods (`media_body`, `jet_listing_elementor`, etc.) remain for backward compatibility. New consolidations use `'method': 'generic'`.

### 2. Scraper Groups to Consolidate

| Group | Pattern | Count | Priority |
|-------|---------|-------|----------|
| ArticleBlock | `div.ArticleBlock` | 44 | High |
| JetEngine grid | `.jet-listing-grid__item` | 9-11 | High |
| et_pb_post | `article.et_pb_post` | 7 | High |
| Table patterns | `table.recordList`, `#browser_table` | 12+ | Medium |
| Drupal newscontent | `#newscontent h2` | 4-5 | Medium |
| Article variants | `article`, `article.item` | 15-20 | Medium |
| Post containers | `.post`, `.news-texthold` | 5 | Medium |
| Views row | `.views-row` | 2 | Low |
| Elementor variants | `.elementor-post__text` | 5-6 | Low |

~5-7 truly unique scrapers (React, special AJAX) stay as custom methods.

### 3. Health Monitoring

**CLI (`make health` / `make health-quick`):**
- Quick mode: tests ~50 representative scrapers (mix of generic + custom)
- Full mode: tests all scrapers
- Checks: HTTP success, results > 0, dates not all None
- Output: summary table + `health_results.json`

**GitHub Actions (`scraper-health.yml`):**
- Weekly full run
- Creates/updates GitHub issue on failures
- Configurable webhook for notifications

### 4. Pattern Detection Tool

`scripts/detect_pattern.py <url>` fetches a page, tries each known pattern's selectors, and recommends a config entry. Outputs ready-to-paste SCRAPER_CONFIG.

### 5. Module Structure

```
python_statement/
  __init__.py     # Re-exports (public API unchanged)
  feed.py         # Feed class
  scraper.py      # Scraper class + generic methods + universal dispatcher
  config.py       # SCRAPER_CONFIG dict
  utils.py        # Utils class
  health.py       # Health check runner
```

### 6. Migration Strategy

Each phase is independently shippable:

1. Build universal dispatcher + module split. Test with 5 ArticleBlock scrapers.
2. Migrate ArticleBlock group (44 methods).
3. Migrate et_pb_post (7), JetEngine (9-11), table patterns (12+).
4. Migrate remaining convertible custom scrapers (~25-30).
5. Build health monitoring + pattern detection tooling.
6. Set up GitHub Actions CI.

### 7. What Stays Custom

- `react` method (parses Next.js `__NEXT_DATA__` JSON)
- AJAX-only methods with non-HTML responses
- Any scraper requiring multi-step navigation
- Committee scrapers with unique structures

## Non-Goals

- Changing the standard return format (dict with source/url/title/date/domain)
- Adding async/concurrent scraping (separate concern)
- Full test coverage of all 400+ scrapers (health monitoring covers this)
