# Legislators Press Release Fetcher

A comprehensive Python script that fetches current U.S. legislators and discovers their press releases from either RSS feeds or by scraping their official websites.

## Features

- **Fetches Current Legislators**: Automatically downloads the latest legislator data from the unitedstates project
- **RSS Feed Discovery**: Intelligently discovers RSS feeds from legislator websites
  - Checks HTML `<link>` tags for RSS/Atom feeds
  - Searches for common feed links in page content
  - Tests common RSS feed URL patterns
- **Press Release Scraping**: Falls back to HTML scraping when RSS feeds aren't available
  - Uses pre-built scrapers for known legislators
  - Generic pattern-based scraping for unknown sites
  - Supports multiple website layouts and patterns
- **Comprehensive Output**: Returns bioguide ID, name, state, party, and press release details

## Installation

```bash
pip install requests beautifulsoup4 lxml python-dateutil pyyaml
```

## Usage

### Fetch from Remote Source

```bash
python3 fetch_legislators.py
```

This will:
1. Fetch legislators from `https://unitedstates.github.io/congress-legislators/legislators-current.json`
2. Process the first 10 legislators (configurable in code)
3. Discover RSS feeds or scrape press releases
4. Save results to `legislators_press_releases.json`

### Use Local Legislators File

```bash
python3 fetch_legislators.py sample_legislators.json
```

This is useful for:
- Testing without network access
- Working with a subset of legislators
- Using cached legislator data

## How It Works

### 1. Legislator Discovery

The script fetches or loads legislator data containing:
- Bioguide ID
- Name (first, last, full)
- Current state and party
- Official website URLs

### 2. RSS Feed Discovery

For each legislator's website, the script:
- Parses HTML to find `<link>` tags with RSS/Atom feed types
- Searches for links containing 'rss', 'feed', or 'atom' keywords
- Tests common RSS feed URL patterns:
  - `/rss.xml`
  - `/feed`
  - `/feeds/press.xml`
  - `/media/rss.xml`
  - And more...

### 3. Press Release Scraping

If no RSS feed is found, the script:
- Checks if there's a known scraper for this legislator
- Discovers press release pages on their website
- Uses generic pattern-based scraping including:
  - `ArticleBlock` elements
  - `media-body` divs
  - `<article>` tags
  - Common press release list patterns

### 4. Output Generation

Each press release includes:
```json
{
  "legislator": {
    "bioguide_id": "S001181",
    "name": "Jeanne Shaheen",
    "state": "NH",
    "party": "Democrat"
  },
  "source": "https://www.shaheen.senate.gov/rss.xml",
  "url": "https://www.shaheen.senate.gov/news/press/shaheen-statement-...",
  "title": "Shaheen Statement on...",
  "date": "2025-01-15",
  "domain": "www.shaheen.senate.gov"
}
```

## Configuration

### Process All Legislators

Edit `fetch_legislators.py` and change:

```python
for legislator in legislators[:10]:  # Process first 10
```

To:

```python
for legislator in legislators:  # Process all
```

### Adjust Delays

The script includes polite delays to avoid overwhelming servers:

```python
time.sleep(1)  # Between legislators
time.sleep(0.5)  # Between URL attempts
```

Adjust these values based on your needs and ethical scraping practices.

### Limit Results Per Legislator

Change the slice limits in the code:

```python
for result in feed_results[:5]:  # Get 5 most recent
```

## Built-in Scrapers

The script includes pre-built scrapers for many legislators including:

**Senators:**
- Mike Crapo (ID)
- Jeanne Shaheen (NH)
- Tim Scott (SC)
- Angus King (ME)
- Josh Hawley (MO)
- Roger Marshall (KS)
- John Barrasso (WY)

**Representatives:**
- Ami Bera (CA)
- Gregory Meeks (NY)
- Greg Steube (FL)
- Nanette Barragán (CA)
- Kathy Castor (FL)
- Emilia Sykes (OH)

And many more in the `python_statement.statement` module.

## Example Output

When run successfully, you'll see output like:

```
Fetching current legislators...
Found 542 current legislators

Processing: Jeanne Shaheen (Democrat-NH)
  Using known scraper for Jeanne Shaheen
  Successfully scraped 10 press releases

Processing: Mike Crapo (Republican-ID)
  Found 1 potential RSS feed(s)
  Trying RSS feed: https://www.crapo.senate.gov/rss.xml
  Successfully parsed RSS feed with 20 items

================================================================================
SUMMARY: Found 30 total press releases from 2 legislators
================================================================================

Legislator: Jeanne Shaheen (Democrat-NH)
Bioguide ID: S001181
Title: Shaheen Statement on Bipartisan Budget Agreement
URL: https://www.shaheen.senate.gov/news/press/shaheen-statement-on-bipartisan-budget-agreement
Date: 2025-01-15

[... more results ...]

Results saved to legislators_press_releases.json
```

## Output Format

Results are saved to `legislators_press_releases.json` in the following format:

```json
[
  {
    "legislator": {
      "bioguide_id": "S001181",
      "name": "Jeanne Shaheen",
      "state": "NH",
      "party": "Democrat"
    },
    "source": "https://www.shaheen.senate.gov/news/press",
    "url": "https://www.shaheen.senate.gov/news/press/shaheen-announces-funding",
    "title": "Shaheen Announces Federal Funding for...",
    "date": "2025-01-15",
    "domain": "www.shaheen.senate.gov"
  }
]
```

## Technical Details

### RSS Feed Parsing

The script uses the `Feed` class from `python_statement.statement`:
- Supports both RSS and Atom feeds
- Parses publication dates
- Handles various date formats
- Extracts titles and links

### Web Scraping

The script uses BeautifulSoup and supports:
- Multiple HTML patterns (ArticleBlock, media-body, articles, etc.)
- Date extraction from various elements
- Relative and absolute URL handling
- User-Agent headers to avoid blocking

### Error Handling

- Timeouts prevent hanging on slow websites
- Try-except blocks handle parsing errors
- Graceful degradation when RSS feeds fail
- Retry logic with delays for rate limiting

## Ethical Considerations

This script is designed for ethical use:
- Respects robots.txt (when using libraries that support it)
- Includes polite delays between requests
- Uses reasonable timeouts
- Limits number of results per legislator
- Identifies itself with a User-Agent header

## Troubleshooting

### 403 Forbidden Errors

Some congressional websites block requests without proper headers or from certain IP ranges. The script includes User-Agent headers to help with this, but some sites may still block automated requests.

**Solutions:**
- Run from a different network/IP
- Increase delays between requests
- Use a proxy service
- Contact the website administrator for API access

### No RSS Feeds Found

If the script can't find RSS feeds:
- Check if the legislator's website actually has an RSS feed
- Try visiting the website manually to find the feed URL
- Add the feed URL manually to the code
- Use the scraping fallback (automatic)

### Scraping Failures

If generic scraping fails:
- The website may have a unique layout
- Create a custom scraper function
- Submit a pull request to add it to the main library

## Contributing

To add support for additional legislators:

1. Study their website structure
2. Create a scraper function following existing patterns
3. Test thoroughly
4. Add to the scraper map in `scrape_with_known_scrapers()`

## License

This script builds on the Statement Python library which is MIT licensed.

## Credits

- Built using the Statement Python library (port of Ruby Statement gem)
- Legislator data from the unitedstates/congress-legislators project
- Created to help track congressional communications
