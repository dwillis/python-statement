# Scraper Guide

A practical introduction to building congressional press release scrapers in Python.

## What This Code Does

This library extracts press releases from congressional websites. Some members provide RSS feeds (easy), others require scraping HTML (more work). This guide focuses on HTML scraping.

## Code Structure

Two main classes:

- **Feed**: Handles RSS/Atom feeds - just parse XML and extract data
- **Scraper**: Handles HTML scraping - the focus of this guide

Each member gets their own method like `Scraper.crapo()` or `Scraper.shaheen()`. You'll add new methods for members not yet covered.

## Anatomy of a Scraper Method

Every scraper follows the same pattern. Here's `Scraper.crapo()` broken down:

```python
@classmethod
def crapo(cls, page=1):
    """Scrape Senator Crapo's press releases."""
    results = []
    url = f"https://www.crapo.senate.gov/media/newsreleases/?PageNum_rs={page}&"
    doc = cls.open_html(url)
    if not doc:
        return []

    article_blocks = doc.find_all('div', {'class': 'ArticleBlock'})
    for block in article_blocks:
        link = block.find('a')
        if not link:
            continue

        href = link.get('href')
        title = link.text.strip()
        date_text = block.find('p').text if block.find('p') else None
        date = None
        if date_text:
            try:
                date = datetime.datetime.strptime(date_text, "%m.%d.%y").date()
            except ValueError:
                try:
                    date = datetime.datetime.strptime(date_text, "%B %d, %Y").date()
                except ValueError:
                    date = None

        result = {
            'source': url,
            'url': href,
            'title': title,
            'date': date,
            'domain': 'www.crapo.senate.gov'
        }
        results.append(result)

    return results
```

**The pattern:**

1. Build URL (with pagination parameter)
2. Fetch HTML using `cls.open_html(url)`
3. Find container elements (the repeating blocks that hold each press release)
4. Loop through containers, extract: link, title, date
5. Parse date (try multiple formats - websites aren't consistent)
6. Build result dictionary with required keys
7. Return list of results

## Building Your First Scraper

### Step 1: Inspect the Website

Open the member's press release page in a browser. Right-click an item → Inspect Element.

Look for:
- The container element that wraps each press release
- Where the title/link is
- Where the date is
- How dates are formatted

Example HTML pattern (Senator Crapo):
```html
<div class="ArticleBlock">
    <h2><a href="/path/to/release">Title Here</a></h2>
    <p>01.15.24</p>
</div>
```

### Step 2: Write the Method

Use this template:

```python
@classmethod
def lastname(cls, page=1):
    """Scrape Representative/Senator Lastname's press releases."""
    results = []
    domain = 'lastname.house.gov'  # or lastname.senate.gov
    url = f"https://{domain}/news/press-releases?page={page}"

    doc = cls.open_html(url)
    if not doc:
        return []

    # Find all press release containers
    containers = doc.find_all('div', {'class': 'container-class-name'})

    for container in containers:
        link = container.find('a')
        if not link:
            continue

        # Extract data
        title = link.text.strip()
        href = link.get('href')

        # Handle relative URLs
        if not href.startswith('http'):
            href = f"https://{domain}{href}"

        # Extract date
        date_elem = container.find('span', {'class': 'date-class'})
        date = None
        if date_elem:
            date_text = date_elem.text.strip()
            try:
                date = datetime.datetime.strptime(date_text, "%B %d, %Y").date()
            except ValueError:
                pass  # Date parsing failed, leave as None

        result = {
            'source': url,
            'url': href,
            'title': title,
            'date': date,
            'domain': domain
        }
        results.append(result)

    return results
```

### Step 3: Test It

```python
from python_statement import Scraper

results = Scraper.lastname()
for r in results[:3]:  # Show first 3
    print(r)
```

## Common BeautifulSoup Patterns

### Finding Elements

```python
# By tag name
doc.find('div')                     # First div
doc.find_all('div')                 # All divs

# By class
doc.find('div', {'class': 'ArticleBlock'})
doc.find_all('div', {'class': 'ArticleBlock'})

# By CSS selector (more powerful)
doc.select_one('div.ArticleBlock')  # First match
doc.select('div.ArticleBlock')      # All matches
doc.select('table tbody tr')        # Nested selection

# Find within an element
container = doc.find('div', {'class': 'ArticleBlock'})
link = container.find('a')
date = container.find('time')
```

### Extracting Data

```python
# Text content
link.text                    # Returns: "  Title Here  "
link.text.strip()            # Returns: "Title Here"

# Attributes
link.get('href')             # Returns: "/news/releases/123"
time_elem.get('datetime')    # Returns: "2024-01-15"
```

### Handling URLs

```python
href = link.get('href')

# Relative URL
if not href.startswith('http'):
    href = f"https://{domain}{href}"

# Already absolute
# Just use it as-is
```

## Date Parsing Patterns

Dates are inconsistent across sites. Try multiple formats:

```python
date = None
date_text = date_elem.text.strip()

# Common formats
date_formats = [
    "%m/%d/%y",      # 01/15/24
    "%m/%d/%Y",      # 01/15/2024
    "%m.%d.%y",      # 01.15.24
    "%B %d, %Y",     # January 15, 2024
    "%b %d, %Y",     # Jan 15, 2024
    "%Y-%m-%d",      # 2024-01-15 (from datetime attributes)
]

for fmt in date_formats:
    try:
        date = datetime.datetime.strptime(date_text, fmt).date()
        break  # Got it, stop trying
    except ValueError:
        continue  # Try next format

# If all fail, date remains None
```

**Tip:** Check `<time>` elements for a `datetime` attribute - it's usually in ISO format:
```python
time_elem = container.find('time')
if time_elem:
    date_attr = time_elem.get('datetime')  # "2024-01-15"
    if date_attr:
        date = datetime.datetime.strptime(date_attr, "%Y-%m-%d").date()
```

## Common HTML Patterns

### Pattern 1: ArticleBlock (Senate sites)
```python
article_blocks = doc.find_all('div', {'class': 'ArticleBlock'})
for block in article_blocks:
    link = block.find('a')
    date_elem = block.find('time') or block.find('p')
    # ...
```

### Pattern 2: Table with Rows (Senate sites)
```python
rows = doc.select('table tbody tr')
for row in rows:
    link = row.select_one('a')
    date_cell = row.select_one('td.recordListDate')
    # ...
```

### Pattern 3: Article Tags (House sites)
```python
articles = doc.find_all('article')
for article in articles:
    link = article.find('a')
    time_elem = article.find('time')
    # ...
```

### Pattern 4: Elementor/WordPress (Modern sites)
```python
items = doc.select('.jet-listing-grid__item')
for item in items:
    link = item.select_one('h3 a')
    date_elem = item.select_one('span.elementor-icon-list-text')
    # ...
```

## Pagination

Most scrapers accept a `page` parameter. URL patterns vary:

```python
# Style 1: Query parameter
url = f"https://site.gov/press?page={page}"

# Style 2: Named parameter
url = f"https://site.gov/press?PageNum_rs={page}"

# Style 3: Path segment
url = f"https://site.gov/press/pagenum/{page}/"

# Style 4: Complex query string
url = f"https://site.gov/press?jsf=jet-engine:press-list&pagenum={page}"
```

Check the site's pagination links to see which pattern they use.

## Generic Scraper Methods

For common patterns, use existing generic methods in `generic_scrapers.py`:

```python
# Table with recordListDate class
Scraper.table_recordlist_date(urls=['https://senator.senate.gov/press'])

# Elementor/Jet Engine sites
Scraper.jet_listing_elementor(urls=['https://senator.senate.gov/press'])

# ArticleBlock pattern
Scraper.article_block_h2_p_date(urls=['https://senator.senate.gov/press'])
```

If a site matches one of these patterns, you can create a simple wrapper:

```python
@classmethod
def lastname(cls, page=1):
    """Scrape Senator Lastname's press releases."""
    return cls.table_recordlist_date(
        urls=['https://lastname.senate.gov/press'],
        page=page
    )
```

## Required Return Format

Every scraper must return a list of dictionaries with these keys:

```python
{
    'source': 'https://site.gov/press',      # The list page URL
    'url': 'https://site.gov/press/123',     # Individual release URL
    'title': 'Press Release Title',          # Release title
    'date': datetime.date(2024, 1, 15),      # Python date object (or None)
    'domain': 'site.gov'                     # Domain name
}
```

## Debugging Tips

**Website not loading?**
```python
doc = cls.open_html(url)
if not doc:
    print("Failed to load page")  # Check URL, network, or site blocking
```

**Can't find elements?**
```python
containers = doc.find_all('div', {'class': 'ArticleBlock'})
print(f"Found {len(containers)} containers")  # Should be > 0

# Print HTML to inspect
print(doc.prettify()[:1000])  # First 1000 chars
```

**Date parsing failing?**
```python
print(f"Date text: '{date_text}'")  # Check exact format
# Add the format you see to the formats list
```

**Check your results:**
```python
results = Scraper.lastname()
print(f"Found {len(results)} releases")
if results:
    print(results[0])  # Inspect first result
```

## Next Steps

1. Pick a member without a scraper (check the website)
2. Inspect their press release page HTML
3. Identify the pattern (ArticleBlock, table, article tags, etc.)
4. Write the method following the template
5. Test with a few pages
6. Check if it matches an existing generic pattern

## Adding Your Scraper to the Library

Once your scraper works:

1. Add the method to the `Scraper` class in `statement.py`
2. Add it alphabetically (keep things organized)
3. Write a docstring: `"""Scrape Senator/Representative Name's press releases."""`
4. Test it: `uv run python -c "from python_statement import Scraper; print(Scraper.lastname())"`

The library is straightforward: fetch HTML, parse with BeautifulSoup, extract data, return a list. Most complexity comes from inconsistent website designs and date formats.
