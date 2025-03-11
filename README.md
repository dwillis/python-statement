# Statement Python

A Python 3 port of the Ruby gem 'Statement' for parsing RSS feeds and HTML pages containing press releases and other official statements from members of Congress.

## Overview

Statement Python provides tools to parse press releases from:
- RSS feeds of members of Congress
- HTML pages that require scraping (when RSS feeds are unavailable or broken)
- Committee websites
- Special groups like House Republicans

## Requirements

- Python 3.6+
- Required packages:
  - requests
  - beautifulsoup4
  - lxml

## Installation

1. Clone this repository
2. Install required packages:

```bash
pip install requests beautifulsoup4 lxml
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

For websites that require HTML scraping:

```python
from python_statement import Scraper

# Scrape an individual member's website
results = Scraper.crapo()  # Senator Crapo's press releases

# Scrape all supported members
all_results = Scraper.member_scrapers()

# Scrape committee websites
committee_results = Scraper.committee_scrapers()
```

## Supported Scrapers

The module includes scrapers for numerous members of Congress. Some examples:

- `Scraper.crapo()` - Senator Mike Crapo
- `Scraper.bera()` - Congressman Ami Bera
- `Scraper.shaheen()` - Senator Jeanne Shaheen
- `Scraper.timscott()` - Senator Tim Scott
- `Scraper.marshall()` - Senator Roger Marshall
- `Scraper.angusking()` - Senator Angus King
- `Scraper.hawley()` - Senator Josh Hawley
- `Scraper.barrasso()` - Senator John Barrasso
- `Scraper.castor()` - Congresswoman Kathy Castor
- `Scraper.meeks()` - Congressman Gregory Meeks
- `Scraper.steube()` - Congressman Greg Steube

## Bulk Scrapers

The module includes several specialized scrapers for different website layouts:

- `Scraper.recordlist()` - For websites using recordList tables
- `Scraper.media_body()` - For websites using media-body class
- `Scraper.article_block()` - For websites using ArticleBlock class
- `Scraper.react()` - For React-based websites
- `Scraper.elementor_post_date()` - For Elementor-based websites
- `Scraper.article_newsblocker()` - For news blockers
- `Scraper.senate_drupal()` - For Senate Drupal sites

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

## Contributing

When contributing a new scraper:
1. Study the website structure carefully
2. Use BeautifulSoup for parsing
3. Ensure the scraper method follows the same return format
4. Add tests for your new scraper

## License

This project is licensed under the MIT License - see the LICENSE.txt file for details.

## Credits

This Python port is based on the Ruby gem 'statement' originally created by:
- Derek Willis
- Jacob Harris
- Mick O'Brien
- Tyler Pearson
- Sam Sweeney