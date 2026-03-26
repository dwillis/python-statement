# Statement Python

A Python 3 port of the Ruby gem 'Statement' for parsing RSS feeds and HTML pages containing press releases and other official statements from members of Congress.

## Overview

Statement Python provides tools to parse press releases from:
- RSS feeds of members of Congress
- HTML pages using configuration-driven generic scrapers (390+ sites)
- HTML pages requiring custom scraping logic
- Committee websites

The library uses a configuration-driven design with a universal generic scraper dispatcher, reducing code duplication across hundreds of congressional websites.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Required packages: requests, beautifulsoup4, lxml, python-dateutil, pyyaml

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/dwillis/python-statement.git
cd python-statement
uv sync
```

### Using pip

```bash
git clone https://github.com/dwillis/python-statement.git
cd python-statement
pip install -e .
```

## Usage

### Parsing RSS Feeds

```python
from python_statement import Feed

# Parse a single RSS feed
results = Feed.from_rss('https://amo.house.gov/rss.xml')
print(results[0])
# {'source': 'https://amo.house.gov/rss.xml', 'url': 'http://amo.house.gov/node/4251', 'title': '...', 'date': datetime.date(2025, 1, 6), 'domain': 'amo.house.gov'}

# Process multiple RSS feeds in batch
urls = ['https://amo.house.gov/rss.xml', 'https://hageman.house.gov/rss.xml']
results, failures = Feed.batch(urls)
```

### Scraping HTML Pages

```python
from python_statement import Scraper

# Scrape individual members using wrapper methods
results = Scraper.pelosi()     # House member (media_body pattern)
results = Scraper.grassley()   # Senator (ArticleBlock pattern)
results = Scraper.bacon()      # Senator (generic dispatcher)

# Scrape with pagination
page2 = Scraper.pelosi(page=2)

# Batch scrape all configured sites for a pattern
all_media_body = Scraper.media_body()  # Scrapes 230+ House sites

# Scrape all supported members
all_results = Scraper.member_scrapers()
```

### Using with uv

```bash
uv run python your_script.py

# Or use Makefile commands
make test                  # Run tests
make health-quick          # Quick scraper health check
make health                # Full scraper health check
make generate-legislators  # Generate legislators JSON
make help                  # Show all available commands
```

## How It Works

Most scrapers are 2-line wrapper methods that call `run_scraper()`, which looks up the site's configuration and routes to the appropriate generic method. Configuration lives in `SCRAPER_CONFIG` (`python_statement/config.py`).

There are two configuration approaches:

**Batch generic methods** — for sites with identical HTML patterns (e.g., 230+ House sites using `.media-body`):
```python
'pelosi': {
    'method': 'media_body',
    'url_base': 'https://pelosi.house.gov/media/press-releases'
}
```

**Universal generic dispatcher** — for sites needing site-specific CSS selectors:
```python
'bacon': {
    'method': 'generic',
    'url_base': 'https://bacon.house.gov/news/documentquery.aspx',
    'container': 'article',
    'title_sel': 'h2 a',
    'date_sel': 'span.middot',
    'date_from_next_sibling': True,
    'date_fmt': ['%m/%d/%Y'],
    'pagination': '?DocumentTypeID=27&Page={page}',
}
```

## Adding a New Scraper

1. **Run the pattern detection tool:**
   ```bash
   uv run python scripts/detect_pattern.py https://newmember.house.gov/press
   ```
   This tests 14 known HTML patterns and recommends a config entry.

2. **If a pattern matches:** Add a config entry to `python_statement/config.py` and a 2-line wrapper to `python_statement/scraper.py`

3. **If no pattern matches:** Write a custom scraper method

See [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md) for detailed instructions.

## Health Monitoring

The library includes health check tooling to detect broken scrapers:

```bash
# Quick check (~50 representative scrapers)
make health-quick

# Full check (all scrapers)
make health

# With options
uv run python scripts/run_health_check.py --full --save --history --workers 10

# View trends over time
make trend
uv run python scripts/health_trend.py --all       # All runs
uv run python scripts/health_trend.py --failures   # Current failures
```

Health checks test HTTP connectivity, result count, and date parsing for each scraper. Results are saved to `health_results.json`. Use `--history` to also append a summary line to `health_history.jsonl` for trend tracking.

A GitHub Actions workflow (`.github/workflows/scraper-health.yml`) runs weekly, creates an issue when failures are detected, and commits the history file for long-term tracking.

## Data Structure

Each press release is returned as a dictionary:

| Key | Type | Description |
|-----|------|-------------|
| `source` | str | The list page URL |
| `url` | str | Individual press release URL |
| `title` | str | Press release title |
| `date` | datetime.date or None | Publication date |
| `domain` | str | Website domain |

## File Organization

```
python_statement/
  __init__.py        # Exports Feed, Scraper, Utils
  config.py          # SCRAPER_CONFIG dict (390 entries)
  scraper.py         # Scraper class with generic dispatcher + batch methods
  feed.py            # Feed class for RSS/Atom parsing
  utils.py           # Utils class for URL handling
  health.py          # HealthChecker class for monitoring

scripts/
  detect_pattern.py         # Pattern detection for new sites
  run_health_check.py       # Health check CLI
  generate_legislators.py   # Match legislators to scrapers
  comprehensive_compare.py  # Compare with Ruby implementation

tests/
  test_statement.py    # Core functionality tests
  test_media_body.py   # Tests for media_body method
  test_react.py        # Tests for React-based sites
```

## Development Tools

```bash
make test                  # Run all tests
make health-quick          # Quick scraper health check
make health                # Full scraper health check
make generate-legislators  # Generate legislators_with_scrapers.json
make compare              # Compare with Ruby implementation
make clean                # Clean build artifacts
```

## Contributing

When contributing a new scraper:

1. Run `scripts/detect_pattern.py` on the target URL first
2. If it matches a pattern: add config entry + 2-line wrapper
3. If it doesn't match: write a custom scraper (see SCRAPER_GUIDE.md)
4. Add the method name to `member_methods()` list in `scraper.py`
5. Test with pages 1 and 2
6. Run `make health-quick` to verify nothing broke

### Fixing Broken Scrapers

1. Run `make health-quick` to identify failures
2. Run `detect_pattern.py` on the broken URL to see if the HTML structure changed
3. Update config selectors or URLs as needed
4. See [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md) for debugging steps

## License

This project is licensed under the MIT License - see the LICENSE.txt file for details.

## Credits

This Python port is based on the Ruby gem 'statement' originally created by:
- Derek Willis
- Jacob Harris
- Mick O'Brien
- Tyler Pearson
- Sam Sweeney
