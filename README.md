# Statement Python

A Python 3 port of the Ruby gem 'Statement' for parsing RSS feeds and HTML pages containing press releases and other official statements from members of Congress and congressional committees.

## Overview

Statement Python provides tools to parse press releases from:
- RSS feeds of members of Congress
- HTML pages using configuration-driven generic scrapers (530+ sites)
- HTML pages requiring custom scraping logic
- Committee websites (every House, Senate and joint committee, majority and minority newsrooms: 84 scrapers)

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

### Scraping HTML Pages

```python
from python_statement import Scraper

# Scrape individual members by name
results = Scraper.run_scraper('pelosi')     # House member (media_body pattern)
results = Scraper.run_scraper('grassley')   # Senator (generic dispatcher)
results = Scraper.run_scraper('bacon')      # House member (generic dispatcher)

# Scrape with pagination
page2 = Scraper.run_scraper('pelosi', page=2)

# Auto-generated wrapper methods also work
results = Scraper.pelosi()
results = Scraper.pelosi(page=2)

# Batch scrape all configured sites for a pattern
all_media_body = Scraper.media_body()  # Scrapes 240+ House sites

# Scrape all supported members
all_results = Scraper.member_scrapers()
```

### Scraping Committees

Committees are a separate collection, keyed to [`committees-current.yaml`](https://github.com/unitedstates/congress-legislators/blob/main/committees-current.yaml). Scraper names are `<thomas_id>_<side>`, where side is `majority`, `minority`, or `full` for a committee with one shared newsroom.

```python
from python_statement import Scraper

results = Scraper.run_scraper('hsag_minority')   # House Agriculture, minority
results = Scraper.ssfi_majority(page=2)           # Senate Finance, chair's news
print(results[0]['committee'], results[0]['side'])  # 'SSFI' 'majority'

Scraper.committee_methods()        # ['hlig_majority', 'hlig_minority', ...]
all_committees = Scraper.committee_scrapers()
```

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

### Using with uv

```bash
uv run python your_script.py

# Or use Makefile commands
make test                  # Run tests
make health-quick          # Quick scraper health check
make health                # Full scraper health check
make health-committees     # Committee scraper health check
make generate-legislators  # Generate legislators JSON
make generate-committees   # Generate committees JSON
make help                  # Show all available commands
```

## How It Works

Most scrapers are configuration entries in `SCRAPER_CONFIG` (`python_statement/config.py`). At import time, each config entry gets an auto-generated wrapper method on the `Scraper` class, so `Scraper.pelosi()` and `Scraper.run_scraper('pelosi')` both work. The `run_scraper()` dispatcher looks up the configuration and routes to the appropriate generic method.

There are two configuration approaches:

**Batch generic methods** — for sites with identical HTML patterns (e.g., 240+ House sites using `.media-body`):
```python
'pelosi': {
    'method': 'media_body',
    'url_base': 'https://pelosi.house.gov/media/press-releases'
}
```

**Universal generic dispatcher** — for sites needing site-specific CSS selectors (190+ sites):
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

2. **If a pattern matches:** Add a config entry to `python_statement/config.py` — that's it, the wrapper method is auto-generated at import time

3. **If no pattern matches:** Write a custom scraper method

See [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md) for detailed instructions.

### Adding a Committee Scraper

Committee entries live in `COMMITTEE_CONFIG` (`python_statement/committee_config.py`) and need `thomas_id` and `side` in addition to the usual keys. To draft and verify entries:

```bash
uv run python scripts/discover_committee_press.py --only HSAG --cache
make generate-committees   # committees_without_scrapers.json lists what's still missing
```

See the committee section of [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md).

## Health Monitoring

The library includes health check tooling to detect broken scrapers:

```bash
# Quick check (~50 representative scrapers)
make health-quick

# Full check (all scrapers)
make health

# With options
uv run python scripts/run_health_check.py --full --save --history --workers 10

# Committees (always checks all of them)
make health-committees
uv run python scripts/run_health_check.py --collection committees --save --history

# View trends over time
make trend
uv run python scripts/health_trend.py --all       # All runs
uv run python scripts/health_trend.py --failures   # Current failures
```

Health checks test HTTP connectivity, result count, and date parsing for each scraper. Results are saved to `health_results.json`. Use `--history` to also append a summary line to `health_history.jsonl` for trend tracking. Committee checks use their own files, `committee_health_results.json` and `committee_health_history.jsonl`; view their trend with `uv run python scripts/health_trend.py --path committee_health_history.jsonl`.

### Dashboard

A static HTML dashboard at `docs/index.html` visualizes health check results, showing scraper status, method distribution, and trend history. A Committees tab shows the committee health check by committee and side. Build it locally:

```bash
make dashboard
```

The dashboard is also built and deployed automatically by the GitHub Actions workflow. A weekly CI run (`.github/workflows/scraper-health.yml`) executes member and committee health checks, builds the dashboard, creates an issue when failures are detected, and commits updated results for long-term tracking.

## Data Structure

Each press release is returned as a dictionary:

| Key | Type | Description |
|-----|------|-------------|
| `source` | str | The list page URL |
| `url` | str | Individual press release URL |
| `title` | str | Press release title |
| `date` | datetime.date or None | Publication date |
| `domain` | str | Website domain |
| `committee` | str | Committee results only: `thomas_id` (e.g. `HSAG`) |
| `side` | str | Committee results only: `majority`, `minority` or `full` |

## File Organization

```
python_statement/
  __init__.py        # Exports Feed, Scraper, Utils
  config.py          # SCRAPER_CONFIG dict (530+ entries) + validation
  committee_config.py  # COMMITTEE_CONFIG (84 committee scrapers) + COMMITTEE_SKIP
  scraper.py         # Scraper class with generic dispatcher + auto-generated wrappers
  feed.py            # Feed class for RSS/Atom parsing
  utils.py           # Utils class for URL handling and date parsing
  health.py          # HealthChecker class for monitoring

scripts/
  detect_pattern.py         # Pattern detection for new sites
  run_health_check.py       # Health check CLI
  build_dashboard.py        # Generate static HTML dashboard
  generate_legislators.py   # Match legislators to scrapers
  generate_committees.py    # Match committees-current.yaml to committee scrapers
  discover_committee_press.py  # Find and verify committee press listings
  health_trend.py           # View health trends over time

tests/
  test_statement.py    # Core functionality tests
  test_committees.py   # Committee config and scraping tests
  test_media_body.py   # Tests for media_body method
  test_react.py        # Tests for React-based sites

docs/
  index.html           # Health dashboard (generated)
```

## Development Tools

```bash
make test                  # Run all tests
make health-quick          # Quick scraper health check
make health                # Full scraper health check
make health-committees     # Committee scraper health check
make dashboard             # Build static health dashboard
make trend                 # View health trends over time
make generate-legislators  # Generate legislators_with_scrapers.json
make generate-committees   # Generate committees_with_scrapers.json
make clean                # Clean build artifacts
```

## Contributing

When contributing a new scraper:

1. Run `scripts/detect_pattern.py` on the target URL first
2. If it matches a pattern: add a config entry to `config.py` (wrapper is auto-generated)
3. If it doesn't match: write a custom scraper method in `scraper.py` (see SCRAPER_GUIDE.md)
4. Test with pages 1 and 2
6. Run `make health-quick` to verify nothing broke

### Fixing Broken Scrapers

1. Run `make health-quick` to identify failures
2. Run `detect_pattern.py` on the broken URL to see if the HTML structure changed
3. Update config selectors or URLs as needed
4. See [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md) for debugging steps

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

This Python port is based on the Ruby gem 'statement' originally created by:
- Derek Willis
- Jacob Harris
- Mick O'Brien
- Tyler Pearson
- Sam Sweeney
