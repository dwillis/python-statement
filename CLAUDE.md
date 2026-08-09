# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Statement is a congressional press release scraper that parses RSS feeds and HTML pages from 390+ congressional websites. It prioritizes maintainability through a configuration-driven design where a universal `generic_scraper()` dispatcher handles most sites via CSS selector configs.

**Core Architecture:**
- **Scraper class** (`python_statement/scraper.py`): HTML scraping with config-driven generic dispatcher + batch generic methods
- **Feed class** (`python_statement/feed.py`): RSS/Atom feed parsing
- **Utils class** (`python_statement/utils.py`): Shared utilities for URL handling and result filtering
- **HealthChecker class** (`python_statement/health.py`): Scraper health monitoring
- **SCRAPER_CONFIG** (`python_statement/config.py`): Configuration dict for all 390 scrapers

## Development Commands

### Environment Setup
```bash
uv sync          # Install dependencies (recommended)
pip install -e . # Or with pip
```

### Running Code
```bash
make test                  # Run all tests with pytest
make health                # Full scraper health check (all scrapers)
make health-quick          # Quick health check (~50 representative scrapers)
make trend                 # View health trends over time
make generate-legislators  # Generate legislators_with_scrapers.json
make clean                # Clean build artifacts
```

### Health Monitoring
```bash
# Quick mode (~50 scrapers, good for routine checks)
uv run python scripts/run_health_check.py --save

# Full mode (all scrapers)
uv run python scripts/run_health_check.py --full --save --workers 10

# Pattern detection with verification (runs config through generic_scraper)
uv run python scripts/detect_pattern.py https://newmember.house.gov/press
uv run python scripts/detect_pattern.py --no-verify https://newmember.house.gov/press

# View health trends over time
uv run python scripts/health_trend.py              # Last 10 runs
uv run python scripts/health_trend.py --failures   # Current failures
```

### Testing
```bash
uv run pytest tests/
uv run python tests/test_media_body.py
uv run python tests/test_react.py
uv run python tests/test_statement.py
```

## Core Architecture

### Configuration-Driven Scraper Pattern

The library's key architectural decision is using **configuration over code**. There are two config approaches:

**1. Batch generic methods** (media_body, article_block_h2_p_date, etc.) — older approach, still used for 330 scrapers with identical HTML patterns:
```python
'member_name': {
    'method': 'media_body',
    'url_base': 'https://member.house.gov/media/press-releases'
}
```

**2. Universal generic dispatcher** (`method: 'generic'`) — newer approach for 60 scrapers with site-specific CSS selectors:
```python
'member_name': {
    'method': 'generic',
    'url_base': 'https://member.senate.gov/news',
    'container': 'article',
    'title_sel': 'h2 a',
    'date_sel': 'time',
    'date_fmt': ['%B %d, %Y'],
    'pagination': '?page={page}',
}
```

Wrapper methods are 2 lines that call `run_scraper()`:
```python
@classmethod
def member_name(cls, page=1):
    """Scrape Member's press releases."""
    return cls.run_scraper('member_name', page)
```

`run_scraper()` (scraper.py:26) looks up the config, routes to the appropriate method, and handles pagination.

### Generic Dispatcher Config Keys

For `'method': 'generic'` entries, these config keys are available:

| Key | Required | Description |
|-----|----------|-------------|
| `url_base` | Yes | Base URL of the press page |
| `container` | Yes | CSS selector for each press release container |
| `title_sel` | Yes | CSS selector for title element within container |
| `date_sel` | No | CSS selector for date element within container |
| `date_fmt` | No | List of strptime format strings to try |
| `date_attr` | No | HTML attribute to read date from (e.g., `'datetime'`) |
| `date_from_next_sibling` | No | If `True`, read date from text node after the date_sel element |
| `pagination` | No | Pagination pattern with `{page}` placeholder |
| `url_prefix` | No | Path prefix for relative URLs (e.g., `'/news/'`) |
| `skip_first` | No | Number of container elements to skip (e.g., header rows) |
| `link_sel` | No | CSS selector for link if different from title element |
| `link_attr` | No | Attribute for URL if not `href` |
| `base_domain` | No | Override domain for URL construction |
| `max_results` | No | Limit number of results returned |

### Batch Generic Methods

These handle sites with identical HTML patterns. Each collects target URLs from `SCRAPER_CONFIG`:

1. **media_body** (scraper.py:407) — 230+ House sites with `.media-body` class
2. **article_block_h2_p_date** (scraper.py:1399) — 16+ Senate sites with `div.ArticleBlock`
3. **jet_listing_elementor** (scraper.py:1294) — 13 Senate sites using WordPress/Elementor
4. **table_recordlist_date** (scraper.py:1208) — 5 Senate sites with table/`td.recordListDate`
5. **element_post_media** (scraper.py:1581) — 3 Senate sites with custom element layout

### Data Flow

**RSS Feeds:**
1. `Feed.from_rss(url)` → `Feed.open_rss(url)` fetches feed
2. BeautifulSoup parses XML with 'xml' parser
3. Returns list of standardized dictionaries

**HTML Scraping:**
1. Wrapper method calls `run_scraper(scraper_name, page)`
2. `run_scraper()` looks up config, routes to `generic_scraper()` or a batch generic method
3. Method builds paginated URL, fetches HTML via `open_html()`
4. BeautifulSoup parses HTML with 'lxml' parser, extracts title/link/date
5. Returns list of standardized dictionaries

**Standard Return Format:**
```python
{
    'source': 'https://site.gov/press',
    'url': 'https://site.gov/press/123',
    'title': 'Press Release Title',
    'date': datetime.date(2024, 1, 15),
    'domain': 'site.gov'
}
```

### Key Methods

**Feed class (feed.py):**
- `open_rss(url)` — Fetches and parses RSS feed
- `from_rss(url)` — Main entry point, returns parsed results
- `batch(urls)` — Process multiple RSS feeds, returns (results, failures)

**Scraper class (scraper.py):**
- `open_html(url)` — Fetches HTML with retries and user-agent headers
- `run_scraper(scraper_name, page)` — Routes config-driven scrapers to appropriate method
- `generic_scraper(scraper_name, page)` — Universal dispatcher for `method: 'generic'` configs
- `member_scrapers()` / `committee_scrapers()` — Run all scrapers
- `member_methods()` — Returns sorted list of all scraper names (strings) from SCRAPER_CONFIG

**HealthChecker class (health.py):**
- `check_scraper(name)` — Test a single scraper, returns status dict including `latest_date` (ISO string of the most recent release, or `None`)
- `run(mode, max_workers, verbose)` — Run health checks (quick or full)
- `save_report(report, path)` — Save results to JSON

## Adding or Fixing Scrapers

**CRITICAL: Use the pattern detection tool first** — See SCRAPER_GUIDE.md for detailed instructions.

### Adding a New Scraper

1. **Run pattern detection:**
   ```bash
   uv run python scripts/detect_pattern.py https://newmember.house.gov/press
   ```
   This tries 14 known HTML patterns and recommends a config entry.

2. **If a pattern matches:** Add to `SCRAPER_CONFIG` in `python_statement/config.py`. That's it — the wrapper method is auto-generated at import time:
   ```python
   # In config.py — SCRAPER_CONFIG dict (alphabetically)
   'newmember': {
       'method': 'generic',
       'url_base': 'https://newmember.house.gov/press',
       'container': '.media-body',
       'title_sel': 'a',
       'date_sel': 'time',
       'date_attr': 'datetime',
       'date_fmt': ['%Y-%m-%d'],
       'pagination': '?page={page}',
   },
   ```
   No need to edit `scraper.py` or `member_methods()`.

3. **If no pattern matches:** Write a custom scraper method in `scraper.py` following the template in SCRAPER_GUIDE.md

### Fixing Broken Scrapers

1. Run `make health-quick` or test individually: `Scraper.run_scraper('name', 1)`
2. Test if URL loads: `Scraper.open_html(url)`
3. Use browser DevTools to inspect current HTML structure
4. Run `detect_pattern.py` on the URL to see if it now matches a different pattern
5. Update config in `config.py` or selectors as needed

### Date Parsing

Use `Utils.parse_date(text, formats)` for all date parsing. It tries strptime formats first (with dot→slash normalization), then falls back to `dateutil.parser.parse(fuzzy=True)`. Never write raw strptime try/except blocks.

Common formats for the `date_fmt` config key:
- `%m/%d/%y`, `%m/%d/%Y` (01/15/24, 01/15/2024)
- `%m.%d.%y` (01.15.24)
- `%B %d, %Y`, `%b %d, %Y` (January 15, 2024)
- `%Y-%m-%d` (2024-01-15, from HTML5 datetime attributes)

Always check `<time datetime="">` attributes first — they're in ISO format.

## File Organization

```
python_statement/
  __init__.py        # Exports Feed, Scraper, Utils
  config.py          # SCRAPER_CONFIG dict (390 entries)
  scraper.py         # Scraper class with generic dispatcher + batch methods
  feed.py            # Feed class for RSS/Atom parsing
  utils.py           # Utils class for URL handling and date parsing
  health.py          # HealthChecker class for monitoring

scripts/
  detect_pattern.py         # Pattern detection for new sites
  run_health_check.py       # Health check CLI entry point
  generate_legislators.py   # Match legislators to scrapers

tests/
  test_statement.py    # Core functionality tests
  test_media_body.py   # Tests for media_body generic method
  test_react.py        # Tests for React-based sites

.github/workflows/
  scraper-health.yml   # Weekly health check CI (creates issues on failure)
```

## Important Implementation Notes

### BeautifulSoup Usage
- RSS feeds: `'xml'` parser
- HTML: `'lxml'` parser
- Prefer `select()` / `select_one()` (CSS selectors) over `find()` / `find_all()`
- Access attributes: `element.get('href')` not `element['href']` (avoids KeyError)

### HTTP Requests
`open_html()` includes User-Agent header, 30-second timeout. Returns None on failure.

### Rate Limiting
`open_html()` sleeps 0.5s before every HTTP request. Cache hits bypass this delay.

### Disk Cache
`Scraper.enable_cache(ttl=3600)` enables file-based caching in `~/.cache/python-statement/`. Useful during development to avoid repeated HTTP requests. Off by default. Use `Scraper.clear_cache()` to reset.

### Pagination Patterns
Common patterns handled by config `pagination` field:
- `?page={page}` — query param
- `?PageNum_rs={page}` — named param
- `{page}/?et_blog` — path segment
- `?jsf=jet-engine:list&pagenum={page}` — complex query

## Testing Strategy

When testing scrapers:
1. **Test page 1**: Should return results
2. **Test page 2**: Verifies pagination works
3. **Check dates**: Ensure dates parse correctly (not all None)
4. **Verify URLs**: Check for relative vs absolute URLs

## Common Pitfalls

1. **Writing custom code for generic patterns**: Run `detect_pattern.py` first
2. **Not checking for None**: Always check if `doc`, `link`, `date_elem` exist
3. **Relative URLs**: Many sites use relative URLs — use `url_prefix` config key
4. **Date parsing failures**: Always wrap in try/except, date can be None
5. **Editing scraper.py for new config scrapers**: Just add to `config.py` — wrapper methods are auto-generated
6. **Config typos**: Caught at import time by `validate_config()` — unknown keys, missing required fields, wrong types all raise `ValueError`

## Dependencies

Core dependencies (see pyproject.toml):
- **requests**, **beautifulsoup4**, **lxml**, **python-dateutil**, **pyyaml**, **pytest**

Requires Python 3.12+

## Maintenance Priorities

1. **Configuration over code**: Prefer `generic` config entries over custom scrapers
2. **Pattern detection first**: Use `detect_pattern.py` before manual inspection
3. **Fix generic methods**: Bug fixes to generic methods benefit many sites
4. **Health monitoring**: Run `make health-quick` regularly to catch broken scrapers
