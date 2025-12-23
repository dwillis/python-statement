# Statement Python

A Python 3 port of the Ruby gem 'Statement' for parsing RSS feeds and HTML pages containing press releases and other official statements from members of Congress.

## Overview

Statement Python provides tools to parse press releases from:
- RSS feeds of members of Congress
- HTML pages using configuration-driven generic scrapers (260+ sites)
- HTML pages requiring custom scraping logic
- Committee websites

The library prioritizes maintainability through a configuration-driven design that uses generic scraper methods for common website patterns, reducing code duplication across hundreds of congressional websites.

## Requirements

- Python 3.6+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Required packages:
  - requests
  - beautifulsoup4
  - lxml
  - python-dateutil
  - pyyaml

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

To parse an RSS feed, pass the URL to the Feed class:

```python
from python_statement import Feed

# Parse a single RSS feed
results = Feed.from_rss('https://amo.house.gov/rss.xml')
print(results[0])
# {'source': 'https://amo.house.gov/rss.xml', 'url': 'http://amo.house.gov/node/4251', 'title': '2024 End-Of-Year Report', 'date': datetime.date(2025, 1, 6), 'domain': 'amo.house.gov'}

# Process multiple RSS feeds in batch
urls = ['https://amo.house.gov/rss.xml', 'https://hageman.house.gov/rss.xml']
results, failures = Feed.batch(urls)
```

### Scraping HTML Pages

The library uses a configuration-driven approach for most congressional websites:

```python
from python_statement import Scraper

# Scrape individual members using simple wrapper methods
results = Scraper.lujan()      # Senator Luján (uses generic jet_listing_elementor)
results = Scraper.crapo()      # Senator Crapo (uses generic article_block_h2_p_date)
results = Scraper.issa()       # Representative Issa (uses generic media_body)

# Generic methods automatically scrape all configured sites
all_media_body = Scraper.media_body()  # Scrapes 230+ House sites automatically
all_elementor = Scraper.jet_listing_elementor()  # Scrapes 13 Senate sites

# Scrape all supported members
all_results = Scraper.member_scrapers()

# Scrape committee websites
committee_results = Scraper.committee_scrapers()
```

**How it works:** Most scrapers are just 2-line wrapper methods that call `run_scraper()`, which looks up the configuration and routes to the appropriate generic method. This eliminates code duplication across sites with similar HTML structures.

### Using with uv

Run Python scripts with uv:

```bash
uv run python your_script.py
```

Or use the Makefile commands:

```bash
make generate-legislators  # Generate legislators JSON
make compare               # Compare with Ruby implementation
make test                  # Run tests
make help                  # Show all available commands
```

## Supported Scrapers

The library includes scrapers for 260+ congressional websites using six generic patterns:

### Generic Scraper Patterns

1. **media_body** (230+ House members) - Sites using `.media-body` class
2. **jet_listing_elementor** (13 senators) - WordPress/Elementor sites
3. **article_block_h2_p_date** (16+ senators) - Sites with `div.ArticleBlock`
4. **table_recordlist_date** (5 senators) - Table layouts with `td.recordListDate`
5. **element_post_media** (3 senators) - Custom element layouts
6. **table_time** - House sites with simple table and `<time>` elements

### Example Member Scrapers

Configuration-driven scrapers (using generic patterns):
- `Scraper.lujan()` - Senator Ben Ray Luján (jet_listing_elementor)
- `Scraper.crapo()` - Senator Mike Crapo (article_block_h2_p_date)
- `Scraper.issa()` - Representative Darrell Issa (media_body)
- `Scraper.timscott()` - Senator Tim Scott (jet_listing_elementor)
- `Scraper.tillis()` - Senator Thom Tillis (element_post_media)

Custom scrapers (unique website structures):
- `Scraper.shaheen()` - Senator Jeanne Shaheen
- `Scraper.hawley()` - Senator Josh Hawley
- `Scraper.bera()` - Representative Ami Bera

**See [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md) for detailed documentation on adding new scrapers or fixing broken ones.**

## Generic Scrapers in Detail

The library uses generic scraper methods that automatically collect their target URLs from `SCRAPER_CONFIG`. This configuration-driven approach means:

- **Less code duplication**: One generic method handles 230+ similar sites
- **Easier maintenance**: Fix a bug once, all sites benefit
- **Simple additions**: Add new sites with 2-line wrapper methods

### How to Add a New Scraper

1. **Check if the site matches a generic pattern** (see SCRAPER_GUIDE.md)
2. **If it matches**: Add to `SCRAPER_CONFIG` and create a wrapper:

```python
# In SCRAPER_CONFIG:
'newmember': {
    'method': 'media_body',
    'url_base': 'https://newmember.house.gov/media/press-releases'
}

# Wrapper method:
@classmethod
def newmember(cls, page=1):
    """Scrape Representative NewMember's press releases."""
    return cls.run_scraper('newmember', page)
```

3. **If it doesn't match**: Write a custom scraper (see SCRAPER_GUIDE.md for template)

### Calling Generic Methods Directly

You can call generic methods with or without specific URLs:

```python
# Scrape all media_body sites (230+)
all_results = Scraper.media_body()

# Scrape specific sites only
specific = Scraper.media_body(['https://issa.house.gov/media/press-releases'], page=1)

# Same for other patterns
senate_results = Scraper.jet_listing_elementor()  # All 13 configured sites
craig_only = Scraper.article_block_h2_p_date(['https://craig.house.gov/media/press-releases'])
```

## Data Structure

Each press release is returned as a dictionary with the following keys:

- `source`: The URL from which the press releases were scraped
- `url`: The URL of the individual press release
- `title`: The title of the press release
- `date`: A datetime.date object representing the publication date
- `domain`: The domain of the website
- `party`: (Optional) The party affiliation, present for committee releases

## Example

```python
from python_statement import Feed, Scraper
import json
import datetime

# Helper function for JSON serialization of dates
def json_serial(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    raise TypeError("Type not serializable")

# Get press releases from RSS feed
rss_results = Feed.from_rss('https://hageman.house.gov/rss.xml')
print(json.dumps(rss_results[0], default=json_serial, indent=2))

# Get press releases from a Senator's website
senator_results = Scraper.crapo()
print(json.dumps(senator_results[0], default=json_serial, indent=2))
```

## Generating Legislators Data

To regenerate the `legislators_with_scrapers.json` file that maps current legislators to their scraper methods:

```bash
uv run python scripts/generate_legislators.py
```

This will:
1. Fetch current legislators from the unitedstates/congress-legislators repository
2. Match them with available scraper methods based on their official website URLs
3. Generate `legislators_with_scrapers.json` with scraper assignments
4. Display a summary of matches and coverage statistics

## Development Tools

### Compare Implementation with Ruby Statement

To verify that the Python implementation matches the Ruby gem:

```bash
uv run python scripts/comprehensive_compare.py
```

This compares the member scraper methods between Python and Ruby implementations.

### Run Tests

```bash
uv run pytest tests/
```

Run specific test scripts:
```bash
uv run python tests/test_media_body.py
uv run python tests/test_react.py
```

## Contributing

When contributing a new scraper:

1. **Check generic patterns first**: See if the site matches an existing pattern in [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md)
2. **If it matches**: Add to `SCRAPER_CONFIG` and create a 2-line wrapper method
3. **If it doesn't match**: Write a custom scraper following the template in SCRAPER_GUIDE.md
4. Ensure the scraper follows the standard return format (see Data Structure above)
5. Add the method to `member_methods()` list
6. Test with multiple pages: `Scraper.newmember(page=1)`, `Scraper.newmember(page=2)`
7. Run the comparison script to verify coverage

### Fixing Broken Scrapers

Websites change frequently. To fix a broken scraper:

1. Follow the debugging steps in [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md)
2. Update URLs, selectors, or pagination patterns as needed
3. Consider converting custom scrapers to use generic patterns when possible
4. Test thoroughly before submitting

**Known Issues**: See the "Suggested Starting Points for Fixes" section in SCRAPER_GUIDE.md for scrapers that need attention.

## License

This project is licensed under the MIT License - see the LICENSE.txt file for details.

## Credits

This Python port is based on the Ruby gem 'statement' originally created by:
- Derek Willis
- Jacob Harris
- Mick O'Brien
- Tyler Pearson
- Sam Sweeney