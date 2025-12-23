# Scraper Guide

A practical introduction to building congressional press release scrapers in Python.

## What This Code Does

This library extracts press releases from congressional websites. Some members provide RSS feeds (easy), others require scraping HTML (more work). This guide focuses on HTML scraping.

## Code Structure

Two main classes:

- **Feed**: Handles RSS/Atom feeds - just parse XML and extract data
- **Scraper**: Handles HTML scraping - the focus of this guide

## Two Approaches to Scraping

### 1. Configuration-Driven (Preferred)

If a website matches one of our generic patterns, just add it to `SCRAPER_CONFIG`:

```python
SCRAPER_CONFIG = {
    'lujan': {
        'method': 'jet_listing_elementor', 
        'url_base': 'https://www.lujan.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list'
    },
}
```

Then create a simple wrapper method:

```python
@classmethod
def lujan(cls, page=1):
    """Scrape Senator Luján's press releases."""
    return cls.run_scraper('lujan', page)
```

**That's it!** The generic method handles everything.

### 2. Custom Scraper (When Needed)

For unique website structures, write a custom method. Each member gets their own method like `Scraper.crapo()` or `Scraper.shaheen()`.

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

## Check Generic Scrapers First!

**IMPORTANT:** Before writing a custom scraper, check if the website matches an existing generic pattern. This saves time and reduces code duplication.

### Available Generic Patterns

The library includes these generic scraper methods:

1. **`table_recordlist_date`** - Senate sites with table layout and `td.recordListDate` class
2. **`jet_listing_elementor`** - WordPress sites using Elementor/Jet Engine plugins
3. **`article_block_h2_p_date`** - Senate sites with `div.ArticleBlock` layout
4. **`table_time`** - House sites with simple table layout and `<time>` elements
5. **`element_post_media`** - Custom element layout with post-media-list classes
6. **`media_body`** - House sites with `.media-body` class (230+ members)

### How to Check if a Site Matches

1. Visit the member's press release page
2. Right-click a press release item → Inspect Element
3. Look for these patterns in the HTML:

```html
<!-- Pattern 1: table_recordlist_date -->
<table>
  <tbody>
    <tr>
      <td class="recordListDate">01/15/24</td>
      <td><a href="/press/123">Title</a></td>
    </tr>
  </tbody>
</table>

<!-- Pattern 2: table_time (House sites) -->
<table>
  <tr>
    <td><time datetime="2024-01-15">01/15/24</time></td>
    <td><a href="/press/123">Title</a></td>
  </tr>
</table>

<!-- Pattern 3: article_block_h2_p_date -->
<div class="ArticleBlock">
  <h2><a href="/press/123">Title</a></h2>
  <p>01.15.24</p>
</div>

<!-- Pattern 4: jet_listing_elementor -->
<div class="jet-listing-grid__item">
  <h3><a href="/press/123">Title</a></h3>
  <span class="elementor-icon-list-text">January 15, 2024</span>
</div>
```

### Tour of a Generic Method: table_time (House Sites)

The `table_time` method handles House member sites with a simple table structure. Here's how it works:

**HTML Pattern it expects:**
```html
<table>
  <tr><!-- header row, will be skipped --></tr>
  <tr>
    <td><time datetime="2024-01-15">01/15/24</time></td>
    <td><a href="/media-center/press-releases/123">Title</a></td>
  </tr>
  <!-- more rows... -->
</table>
```

**Example usage:**
```python
@classmethod
def barr(cls, page=1):
    """Scrape Representative Barr's press releases."""
    return cls.table_time(
        urls=['https://barr.house.gov/media-center/press-releases'],
        page=page
    )
```

**What the generic method does:**

1. **Builds the URL with pagination:**
   ```python
   source_url = f"{url}{'&' if '?' in url else '?'}page={page}"
   # Result: https://barr.house.gov/media-center/press-releases?page=1
   ```

2. **Fetches the page:**
   ```python
   doc = cls.open_html(source_url)
   ```

3. **Finds all table rows, skipping the first (header):**
   ```python
   rows = doc.select("table tr")[1:]  # [1:] skips the header row
   ```

4. **For each row, extracts the link and time element:**
   ```python
   link = row.select_one("td a") or row.select_one("a")
   time_elem = row.select_one("time")
   ```

5. **Parses the date from the `datetime` attribute (or text if no attribute):**
   ```python
   date_text = time_elem.get('datetime') or time_elem.text.strip()
   # Tries multiple formats: "%m/%d/%y", "%Y-%m-%d", "%B %d, %Y", etc.
   ```

6. **Handles relative URLs:**
   ```python
   href = link.get('href')
   if not href.startswith('http'):
       href = f"https://{domain}{href}"
   ```

7. **Returns a list of results in the standard format**

**Benefits of using the generic method:**
- Handles edge cases (missing dates, relative URLs, multiple date formats)
- Less code to maintain (3 lines vs. 30+ lines)
- Consistent behavior across similar sites
- Automatic updates when the generic method improves

### When to Write a Custom Scraper

Write a custom scraper only when:
- The site doesn't match any generic pattern
- The site requires special logic (e.g., JavaScript rendering, authentication)
- The generic method doesn't handle a specific edge case for that site

## Building Your First Scraper

### Step 0: Check for Generic Patterns First

Before writing custom code, check if the site matches one of our generic patterns:

1. **table_recordlist_date**: Senate sites with `<table>` and `td.recordListDate`
2. **jet_listing_elementor**: WordPress/Elementor sites with `.jet-listing-grid__item`
3. **article_block_h2_p_date**: Sites with `div.ArticleBlock`
4. **element_post_media**: Sites with `.element` and `.post-media-list`
5. **media_body**: House sites with `.media-body` class

**To test if a site matches a pattern:**

```python
from python_statement import Scraper

# Test the generic method directly
url = 'https://senator.senate.gov/press'
results = Scraper.jet_listing_elementor([url], page=1)
print(f"Found {len(results)} results")
if results:
    print(results[0])  # If this works, add to SCRAPER_CONFIG!
```

**If it matches:** Add to SCRAPER_CONFIG and create a wrapper method (see Configuration-Driven approach above).

**If it doesn't match:** Write a custom scraper (continue to Step 1 below).

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

<<<<<<< HEAD
For common patterns, the library includes generic methods that automatically collect their URLs from `SCRAPER_CONFIG`:
=======
**See the "Check Generic Scrapers First!" section above for a detailed explanation of available patterns and how to use them.**

Quick reference for calling generic methods:
>>>>>>> a5461ff420eeec7c8e8417211108861fb84daf6b

### Available Generic Patterns

**1. table_recordlist_date** - Senate sites with table.recordListDate
```python
# HTML pattern:
# <table><tbody><tr>
#   <td class="recordListDate">01/15/24</td>
#   <td><a href="/press/123">Title</a></td>
# </tr></tbody></table>

# Example sites: moran, boozman, thune, barrasso, graham
```

**2. jet_listing_elementor** - WordPress/Elementor with Jet Engine
```python
# HTML pattern:
# <div class="jet-listing-grid__item">
#   <h3><a href="/press/123">Title</a></h3>
#   <span class="elementor-icon-list-text">January 15, 2024</span>
# </div>

# Example sites: timscott, cassidy, fetterman, lujan, mullin, ossoff
```

**3. article_block_h2_p_date** - Senate sites with ArticleBlock
```python
# HTML pattern:
# <div class="ArticleBlock">
#   <h2><a href="/press/123">Title</a></h2>
#   <p>01.15.24</p>
# </div>

# Example sites: murphy, markey, cotton, durbin, crapo, hassan
```

**4. element_post_media** - Sites with .element class
```python
# HTML pattern:
# <div class="element">
#   <a href="/press/123">
#     <div class="post-media-list-title">Title</div>
#     <div class="post-media-list-date">January 15, 2024</div>
#   </a>
# </div>

# Example sites: tillis, wicker, blackburn
```

**5. media_body** - House sites with media-body
```python
# HTML pattern:
# <div class="media-body">
#   <a href="/press/123">Title</a>
#   <div class="col-auto">01/15/24</div>
# </div>

# Example sites: 230+ House members including issa, pelosi, khanna
```

### How Generic Methods Work

Generic methods automatically pull URLs from `SCRAPER_CONFIG`:

```python
# When you call the generic method without arguments:
results = Scraper.media_body()  # Scrapes ALL 230+ media_body sites!

# Or call with specific URLs:
results = Scraper.media_body(['https://specific-site.house.gov/press'], page=1)
```

### Adding a Site to a Generic Pattern

1. **Add to SCRAPER_CONFIG:**
```python
SCRAPER_CONFIG = {
    'newmember': {
        'method': 'jet_listing_elementor',
        'url_base': 'https://newmember.senate.gov/press/?jsf=jet-engine:press-list'
    },
}
```

2. **Create wrapper method:**
```python
@classmethod
def newmember(cls, page=1):
    """Scrape Senator NewMember's press releases."""
    return cls.run_scraper('newmember', page)
```

3. **Test it:**
```python
results = Scraper.newmember()
print(f"Found {len(results)} results")
```

That's it! The `run_scraper()` method looks up the config, calls the appropriate generic method, and handles pagination.

## Custom Scrapers (When Generic Patterns Don't Fit)

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

## Fixing Broken Scrapers

Websites change! Here's how to identify and fix broken scrapers.

### Common Issues

**1. URL Structure Changed**

Symptoms: 404 errors, no results found

```python
# Test the URL directly
doc = Scraper.open_html('https://member.senate.gov/press')
if not doc:
    print("URL is broken - site may have changed")
```

Fix: Visit the member's website, find the new press releases page, update the URL in SCRAPER_CONFIG or the scraper method.

**2. HTML Structure Changed**

Symptoms: Scraper runs but returns empty results

```python
# Debug: Check what selectors return
doc = Scraper.open_html(url)
old_selector = doc.select('.old-class-name')
print(f"Old selector found: {len(old_selector)} items")

# Try finding new structure
new_selector = doc.select('.new-class-name')
print(f"New selector found: {len(new_selector)} items")
```

Fix: Update the selector in the scraper method to match new HTML structure.

**3. Pagination Pattern Changed**

Symptoms: Page 1 works, page 2+ fail

```python
# Test pagination URLs
for page in [1, 2]:
    url = f"https://site.gov/press?page={page}"
    doc = Scraper.open_html(url)
    items = doc.select('.press-item')
    print(f"Page {page}: {len(items)} items")
```

Fix: Update pagination URL pattern in the scraper.

### Step-by-Step Debugging Process

1. **Test the URL loads:**
```python
url = 'https://member.senate.gov/press'
doc = Scraper.open_html(url)
print("Loaded" if doc else "Failed to load")
```

2. **Inspect what selectors work:**
```python
# Try various selectors
selectors = [
    'div.ArticleBlock',
    'article',
    '.media-body',
    '.jet-listing-grid__item',
    '.post',
]

for selector in selectors:
    items = doc.select(selector)
    if items:
        print(f"{selector}: found {len(items)} items")
```

3. **Check the first item's structure:**
```python
items = doc.select('article')  # Whatever selector worked
if items:
    first = items[0]
    print(first.prettify()[:500])  # Print HTML
    
    # Find title
    title = first.select_one('h1, h2, h3, a')
    print(f"Title: {title.text if title else 'NOT FOUND'}")
    
    # Find date
    date = first.select_one('time, .date, span[class*=date]')
    print(f"Date: {date.text if date else 'NOT FOUND'}")
```

4. **Test the full scraper:**
```python
results = Scraper.member_name()
print(f"Results: {len(results)}")
if results:
    print(results[0])
```

### Suggested Starting Points for Fixes

Here are scrapers that likely need updating based on recent testing:

**High Priority - Known Broken:**

1. **rosen** - Site completely changed structure
   - Old: jet_listing_elementor pattern
   - Current URL returns 404
   - New site uses: `https://www.rosen.senate.gov/category/press_release/`
   - Uses: `article.elementor-post` with different date/title structure
   - **Action:** Remove from SCRAPER_CONFIG, write custom scraper

2. **padilla** - Pagination not working
   - Pattern should work but URL structure changed
   - Test: `https://www.padilla.senate.gov/newsroom/press-releases/`
   - **Action:** Check pagination pattern, update URL in config

3. **mullin** - URL/pagination issue
   - Uses `/page/X/` pagination instead of jsf parameter
   - Config updated but may need verification
   - **Action:** Test with: `Scraper.mullin(page=2)`

**Medium Priority - May Have Issues:**

Sites using deprecated patterns or old URLs. Test these:

```python
# Quick test script
members_to_check = ['hoeven', 'lankford', 'rubio', 'schumer', 'warner']

for member in members_to_check:
    try:
        method = getattr(Scraper, member)
        results = method(page=1)
        status = f"✓ {len(results)} results" if results else "✗ No results"
        print(f"{member}: {status}")
    except Exception as e:
        print(f"{member}: ✗ ERROR - {str(e)[:50]}")
```

**Conversion Opportunities:**

Check if these custom scrapers can be simplified to use SCRAPER_CONFIG:

- Any method with `ArticleBlock` → might use `article_block_h2_p_date`
- Any method with `jet-engine` or `elementor` → might use `jet_listing_elementor`
- Any method with `table tbody tr` → might use `table_recordlist_date`

Test by calling the generic method directly with the site's URL.

## Next Steps

### For New Scrapers

1. Pick a member without a scraper
2. Visit their press release page
3. **Test generic patterns first** (see Step 0 above)
4. If match found: Add to SCRAPER_CONFIG + create wrapper
5. If no match: Write custom scraper following the template
6. Test with multiple pages
7. Add to `member_methods()` list

### For Fixing Broken Scrapers

1. Pick a scraper from the "Suggested Starting Points" list above
2. Run the debugging steps to identify the issue
3. Update URL, selectors, or pagination as needed
4. Consider converting to SCRAPER_CONFIG if it matches a generic pattern
5. Test thoroughly with pages 1, 2, and 3

### Quick Win Opportunities

**Convert existing scrapers to config-driven approach:**

Find scrapers that match generic patterns but aren't using them yet:

```python
# Search for patterns in existing code
# ArticleBlock pattern candidates:
grep -n "ArticleBlock" python_statement/statement.py

# Jet/Elementor pattern candidates:
grep -n "jet-listing\|elementor" python_statement/statement.py

# Table pattern candidates:
grep -n "tbody tr" python_statement/statement.py
```

If you find a match, convert it to use `run_scraper()` - you'll reduce 30+ lines to 2 lines!

## Adding Your Scraper to the Library

Once your scraper works:

1. **If using SCRAPER_CONFIG:**
   - Add entry to `SCRAPER_CONFIG` dict (alphabetically within its pattern section)
   - Add wrapper method to `Scraper` class (alphabetically)
   - Add method to `member_methods()` list

2. **If custom scraper:**
   - Add method to `Scraper` class (alphabetically)
   - Add method to `member_methods()` list
   - Write a clear docstring

3. **Test it:**
```bash
uv run python -c "from python_statement import Scraper; print(len(Scraper.lastname()))"
```

4. **Commit with descriptive message:**
```bash
git add python_statement/statement.py
git commit -m "Add scraper for Senator/Rep Lastname"
```

## Summary

- **Prefer configuration over code**: Use SCRAPER_CONFIG when possible
- **Generic methods are powerful**: They handle 260+ sites with just config entries
- **Test before writing**: Check if a generic pattern works first
- **Websites change**: Fix broken scrapers using the debugging process
- **Keep it simple**: A 2-line wrapper is better than 30 lines of duplicate code

The library prioritizes maintainability through configuration-driven design. Most complexity comes from inconsistent website designs and date formats - the generic methods handle that complexity so you don't have to.
