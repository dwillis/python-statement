# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Statement is a congressional press release scraper that parses RSS feeds and HTML pages from 260+ congressional websites. It prioritizes maintainability through a configuration-driven design that uses generic scraper methods for common website patterns.

**Core Architecture:**
- **Feed class**: Parses RSS/Atom feeds using BeautifulSoup XML parsing
- **Scraper class**: Scrapes HTML pages using configuration-driven generic methods
- **Utils class**: Shared utilities for URL handling and result filtering

## Development Commands

### Environment Setup
```bash
# Install dependencies (recommended)
uv sync

# Or with pip
pip install -e .
```

### Running Code
```bash
# Execute Python scripts with uv
uv run python your_script.py

# Or use make commands
make test                  # Run all tests with pytest
make generate-legislators  # Generate legislators_with_scrapers.json
make compare              # Compare with Ruby implementation
make clean                # Clean build artifacts
```

### Testing
```bash
# Run all tests
uv run pytest tests/

# Run specific test files
uv run python tests/test_media_body.py
uv run python tests/test_react.py
uv run python tests/test_statement.py
```

## Core Architecture

### Configuration-Driven Scraper Pattern

The library's key architectural decision is using **configuration over code**. Instead of writing custom scrapers for each similar website, most scrapers use generic methods configured via `SCRAPER_CONFIG`:

```python
SCRAPER_CONFIG = {
    'member_name': {
        'method': 'jet_listing_elementor',  # Which generic pattern to use
        'url_base': 'https://member.senate.gov/press'  # Base URL
    }
}
```

Wrapper methods are just 2 lines that call `run_scraper()`:
```python
@classmethod
def member_name(cls, page=1):
    """Scrape Member's press releases."""
    return cls.run_scraper('member_name', page)
```

The `run_scraper()` method (python_statement/statement.py:500) looks up the config, calls the appropriate generic method, and handles pagination automatically.

### Generic Scraper Methods

Six generic methods handle 260+ congressional sites. Each automatically collects target URLs from `SCRAPER_CONFIG`:

1. **media_body** (python_statement/statement.py:839) - 230+ House sites with `.media-body` class
2. **jet_listing_elementor** (python_statement/statement.py:1948) - 13 Senate sites using WordPress/Elementor
3. **article_block_h2_p_date** (python_statement/statement.py:2052) - 16+ Senate sites with `div.ArticleBlock`
4. **table_recordlist_date** (python_statement/statement.py:1861) - 5 Senate sites with table/`td.recordListDate`
5. **element_post_media** (python_statement/statement.py:2231) - 3 Senate sites with custom element layout
6. **table_time** - House sites with table and `<time>` elements

Each generic method can be called directly:
```python
# Scrape all configured sites for this pattern
Scraper.media_body()  # Scrapes 230+ sites

# Or scrape specific URLs
Scraper.jet_listing_elementor(['https://specific.senate.gov/press'], page=1)
```

### Data Flow

**RSS Feeds:**
1. `Feed.from_rss(url)` → `Feed.open_rss(url)` fetches feed
2. BeautifulSoup parses XML with 'xml' parser
3. `Feed.date_from_rss_item()` handles various date formats
4. Returns list of standardized dictionaries

**HTML Scraping:**
1. Wrapper method calls `run_scraper(scraper_name, page)`
2. `run_scraper()` looks up config, routes to generic method
3. Generic method builds paginated URL, fetches HTML via `open_html()`
4. BeautifulSoup parses HTML with 'lxml' parser
5. Method finds containers, extracts title/link/date
6. Returns list of standardized dictionaries

**Standard Return Format:**
```python
{
    'source': 'https://site.gov/press',      # List page URL
    'url': 'https://site.gov/press/123',     # Individual release URL
    'title': 'Press Release Title',          # Release title
    'date': datetime.date(2024, 1, 15),      # Python date object or None
    'domain': 'site.gov'                     # Domain name
}
```

### Key Methods

**Feed class (python_statement/statement.py:60):**
- `open_rss(url)` - Fetches and parses RSS feed
- `from_rss(url)` - Main entry point, returns parsed results
- `batch(urls)` - Process multiple RSS feeds, returns (results, failures)
- `date_from_rss_item(item)` - Extracts date from RSS item with multiple format handling

**Scraper class (python_statement/statement.py:199):**
- `open_html(url)` - Fetches HTML with retries and user-agent headers
- `run_scraper(scraper_name, page)` - Routes config-driven scrapers to generic methods
- `member_scrapers()` / `committee_scrapers()` - Run all scrapers
- Generic methods: `media_body()`, `jet_listing_elementor()`, `article_block_h2_p_date()`, etc.
- `member_methods()` - Returns list of all member scraper method names

## Adding or Fixing Scrapers

**CRITICAL: Always check generic patterns first** - See SCRAPER_GUIDE.md for detailed instructions.

### Adding a New Scraper

1. **Test if site matches a generic pattern:**
   ```python
   # Try each generic method with the site's URL
   results = Scraper.media_body(['https://newmember.house.gov/press'], page=1)
   ```

2. **If it matches:** Add to `SCRAPER_CONFIG` (python_statement/statement.py:204) and create wrapper:
   ```python
   # In SCRAPER_CONFIG (alphabetically within pattern section)
   'newmember': {
       'method': 'media_body',
       'url_base': 'https://newmember.house.gov/press'
   }

   # Wrapper method (alphabetically in Scraper class)
   @classmethod
   def newmember(cls, page=1):
       """Scrape Representative NewMember's press releases."""
       return cls.run_scraper('newmember', page)
   ```

3. **If it doesn't match:** Write custom scraper following template in SCRAPER_GUIDE.md

4. **Add to member list:** Add method name to `member_methods()` list

### Fixing Broken Scrapers

Websites change frequently. Debug process:

1. Test if URL loads: `Scraper.open_html(url)`
2. Inspect HTML structure with browser DevTools
3. Test selectors: `doc.select('selector')` to verify what matches
4. Update URL/selectors/pagination as needed
5. Consider converting custom scrapers to use generic patterns

Common issues:
- URL structure changed (404 errors)
- HTML class/structure changed (no results)
- Pagination pattern changed (page 1 works, page 2+ fail)

### Date Parsing

Date formats vary widely across sites. The code handles multiple formats:

**RSS feeds** use dateutil parser for flexible parsing (python_statement/statement.py:74)

**HTML scraping** tries multiple strptime formats in order:
- `%m/%d/%y`, `%m/%d/%Y` (01/15/24, 01/15/2024)
- `%m.%d.%y` (01.15.24)
- `%B %d, %Y`, `%b %d, %Y` (January 15, 2024, Jan 15, 2024)
- `%Y-%m-%d` (2024-01-15, from HTML5 datetime attributes)

Always check `<time datetime="">` attributes first - they're in ISO format.

## File Organization

```
python_statement/
  __init__.py           # Exports Statement, Feed, Scraper, Utils
  statement.py          # Main module (2000+ lines, contains all classes)

tests/
  test_statement.py     # Core functionality tests
  test_media_body.py    # Tests for media_body generic method
  test_react.py         # Tests for React-based sites

scripts/
  generate_legislators.py      # Matches legislators to scrapers
  comprehensive_compare.py     # Compares with Ruby implementation
  compare_ruby_python.py       # Legacy comparison script
```

## Important Implementation Notes

### BeautifulSoup Usage

- RSS feeds: Use `'xml'` parser for feed parsing
- HTML: Use `'lxml'` parser for speed and reliability
- Key methods: `find()`, `find_all()`, `select()`, `select_one()`
- Access attributes: `element.get('href')` not `element['href']` (avoids KeyError)

### HTTP Requests

`open_html()` includes:
- User-Agent header to avoid bot blocking
- 10-second timeout
- Retry logic for transient failures
- Returns None on failure (check before processing)

### URL Handling

- Use `Utils.absolute_link(base_url, relative_url)` for relative URLs
- Or manually: Check if `href.startswith('http')`, if not prepend domain
- Extract domain: `urlparse(url).netloc`

### Pagination Patterns

Common patterns in congressional sites:
- Query param: `?page={page}`
- Named param: `?PageNum_rs={page}`
- Path segment: `/pagenum/{page}/`
- Complex: `?jsf=jet-engine:list&pagenum={page}`

Generic methods handle these automatically based on URL structure in config.

## Testing Strategy

When testing scrapers:

1. **Test page 1**: Should return results
2. **Test page 2**: Verifies pagination works
3. **Check dates**: Ensure dates parse correctly (not all None)
4. **Verify URLs**: Check for relative vs absolute URLs
5. **Check result count**: Compare against what's visible on the page

Example test:
```python
results_p1 = Scraper.member_name(page=1)
results_p2 = Scraper.member_name(page=2)

assert len(results_p1) > 0, "Page 1 returned no results"
assert len(results_p2) > 0, "Page 2 returned no results"
assert results_p1[0]['url'] != results_p2[0]['url'], "Pages returned same results"
```

## Common Pitfalls

1. **Selecting parent instead of children**: `doc.find_all('div', {'class': 'container'})` when you should select `.container .item`
2. **Not checking for None**: Always check if `doc`, `link`, `date_elem` exist before accessing
3. **Relative URLs**: Many sites use relative URLs - must convert to absolute
4. **Date parsing failures**: Always wrap in try/except, date can be None
5. **Writing custom code for generic patterns**: Check SCRAPER_GUIDE.md patterns first

## Dependencies

Core dependencies (see pyproject.toml):
- **requests**: HTTP requests
- **beautifulsoup4**: HTML/XML parsing
- **lxml**: Fast XML/HTML parser for BeautifulSoup
- **python-dateutil**: Flexible date parsing
- **pyyaml**: YAML configuration support
- **pytest**: Testing framework

Requires Python 3.12+

## Maintenance Priorities

1. **Configuration over code**: Prefer adding to SCRAPER_CONFIG over custom scrapers
2. **Generic methods first**: Test if a site matches existing patterns before writing custom code
3. **Fix generic methods**: Bug fixes to generic methods benefit 260+ sites
4. **Convert custom to generic**: Look for opportunities to simplify custom scrapers

When a generic method doesn't work for a configured site, investigate why - it may reveal a bug that affects many sites.
