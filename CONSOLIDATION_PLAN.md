# Scraper Method Consolidation Plan

## Executive Summary

This document identifies member-specific scraper methods that can be consolidated into generic ones, reducing code duplication from ~2,000+ lines to ~200 lines while maintaining functionality.

## Identified Consolidation Opportunities

### 1. Table with recordListDate Pattern (10+ methods)

**Pattern**: `table tbody tr` with `td.recordListDate`

**Member-specific methods using this pattern**:
- `moran()` - https://www.moran.senate.gov/public/index.cfm/news-releases
- `boozman()` - https://www.boozman.senate.gov/public/index.cfm/press-releases
- `thune()` - https://www.thune.senate.gov/public/index.cfm/press-releases
- `barrasso()` - https://www.barrasso.senate.gov/public/index.cfm/news-releases
- `graham()` - https://www.lgraham.senate.gov/public/index.cfm/press-releases
- `ernst()` - Similar pattern
- `risch()` - Similar pattern

**Current code duplication**: Each method has ~30 lines of identical code

**Consolidation**: Create `table_recordlist_date(urls, page)` generic method

---

### 2. Jet Listing Grid with Elementor (15+ methods)

**Pattern**: `.jet-listing-grid__item` with `h3 a` and `span.elementor-icon-list-text`

**Member-specific methods using this pattern**:
- `timscott()` - https://www.scott.senate.gov/media-center/press-releases
- `fetterman()` - https://www.fetterman.senate.gov/press-releases
- `tester()` - https://www.tester.senate.gov/newsroom/press-releases
- `hawley()` - Similar pattern
- `marshall()` - Similar pattern
- `britt()` - Similar pattern
- `toddyoung()` - Similar pattern
- `markkelly()` - Similar pattern
- `hagerty()` - Similar pattern
- `jayapal()` - Similar pattern
- `lujan()` - Similar pattern
- `ossoff()` - Similar pattern
- `padilla()` - Similar pattern
- `mullin()` - Similar pattern
- `rosen()` - Similar pattern

**Current code duplication**: Each method has ~30 lines of identical code

**Consolidation**: Create `jet_listing_elementor(urls, page)` generic method

---

### 3. ArticleBlock with h2 and p date - Flexible date formats (40+ methods)

**Pattern**: `div.ArticleBlock` with `h2 a` and `p` containing date

**Member-specific methods using this pattern**:
- `crapo()` - Date format: `%m.%d.%y`
- `sherrod_brown()` - Date format: `%m.%d.%Y`
- `durbin()` - Date format: `%m.%d.%Y`
- `bennet()` - Similar pattern
- `cardin()` - Similar pattern
- `carper()` - Similar pattern
- `casey()` - Similar pattern
- `coons()` - Similar pattern
- `hirono()` - Similar pattern
- `lankford()` - Similar pattern
- `manchin()` - Similar pattern
- `menendez()` - Similar pattern
- `merkley()` - Similar pattern
- `stabenow()` - Similar pattern

Plus many House members:
- `kennedy()`, `garypeters()`, `jackreed()`, `rounds()`, `kaine()`, `blackburn()`, `gillibrand()`, `heinrich()`, `aguilar()`, `bergman()`, `brownley()`, `cantwell()`, `capito()`, `carey()`, `clarke()`, `cortezmasto()`, `crawford()`, `cruz()`, `daines()`, `duckworth()`, `ellzey()`, `foxx()`, `gimenez()`, `gosar()`, `hassan()`, `houlahan()`, `huizenga()`, `hydesmith()`, `jasonsmith()`, `mikelee()`, `mooney()`, `mullin()`, `murray()`, `paul()`, `porter()`, `pressley()`, `reschenthaler()`, `rickscott()`, `ronjohnson()`, `schatz()`, `schumer()`, `takano()`, `tinasmith()`, `titus()`, `tlaib()`, `tuberville()`, `warner()`, `whitehouse()`, `wyden()`

**Current code duplication**: Each method has ~30 lines of identical code

**Note**: The existing `article_block_h2_date()` method exists but only handles `%B %d, %Y` format. Need a more flexible version.

**Consolidation**: Enhance `article_block_h2_date()` to handle multiple date formats automatically

---

### 4. Simple Table with time element (5+ methods)

**Pattern**: `table tr` with `td a` and `time` element

**Member-specific methods using this pattern**:
- `barr()` - https://barr.house.gov/media-center/press-releases
- Similar methods exist for other members

**Current code duplication**: Each method has ~25 lines of identical code

**Consolidation**: Create `table_time(urls, page)` generic method

---

### 5. Element Pattern (3 methods)

**Pattern**: `.element` with `.post-media-list-title` and `.post-media-list-date`

**Member-specific methods using this pattern**:
- `tillis()` - Similar pattern
- `wicker()` - https://www.wicker.senate.gov/media/press-releases
- `blackburn()` - Similar pattern (possibly)

**Current code duplication**: Each method has ~30 lines of identical code

**Consolidation**: Create `element_post_media(urls, page)` generic method

---

## Implementation Approach

The generic methods are implemented in `generic_scrapers.py` as a separate `GenericScrapers` class. To integrate them into the `Scraper` class, simply use **inheritance**:

```python
# In statement.py
from generic_scrapers import GenericScrapers

class Scraper(GenericScrapers):
    """Class for scraping HTML pages."""
    # All existing methods stay as-is
    # Generic methods inherited automatically
```

This approach:
- ✅ Requires only 2 lines of code changes
- ✅ Keeps generic methods in a separate, testable module
- ✅ Avoids code duplication
- ✅ Allows easy updates to generic methods
- ✅ Preserves all existing Scraper functionality
- ✅ `Scraper.open_html()` automatically overrides the base method

## Proposed New Generic Methods

Below are the new generic methods that are implemented in `generic_scrapers.py`:

### Method 1: `table_recordlist_date()`

```python
@classmethod
def table_recordlist_date(cls, urls=None, page=1):
    """
    Scrape press releases from websites with table tbody tr and td.recordListDate.

    This pattern is used by Senate sites that display press releases in a table
    with a specific recordListDate class for the date column.

    Args:
        urls: List of URLs to scrape (default: None)
        page: Page number for pagination (default: 1)

    Returns:
        List of dictionaries with keys: source, url, title, date, domain

    Example URLs:
        - https://www.moran.senate.gov/public/index.cfm/news-releases
        - https://www.boozman.senate.gov/public/index.cfm/press-releases
        - https://www.thune.senate.gov/public/index.cfm/press-releases
    """
    results = []
    if urls is None:
        urls = []

    for url in urls:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        source_url = f"{url}?page={page}"

        doc = cls.open_html(source_url)
        if not doc:
            continue

        rows = doc.select("table tbody tr")
        for row in rows:
            link = row.select_one('a')
            date_cell = row.select_one('td.recordListDate')

            if not (link and date_cell):
                continue

            # Parse date with multiple format attempts
            date = None
            date_text = date_cell.text.strip()

            # Try multiple date formats
            date_formats = [
                "%m/%d/%y",      # 01/15/24
                "%m/%d/%Y",      # 01/15/2024
                "%m.%d.%y",      # 01.15.24
                "%m.%d.%Y",      # 01.15.2024
                "%B %d, %Y",     # January 15, 2024
            ]

            for fmt in date_formats:
                try:
                    date = datetime.datetime.strptime(date_text, fmt).date()
                    break
                except ValueError:
                    continue

            # Handle relative URL
            href = link.get('href')
            if href.startswith('http'):
                full_url = href
            else:
                full_url = f"https://{domain}{href}"

            result = {
                'source': url,
                'url': full_url,
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)

    return results
```

### Method 2: `jet_listing_elementor()`

```python
@classmethod
def jet_listing_elementor(cls, urls=None, page=1):
    """
    Scrape press releases from websites using Jet Engine listing with Elementor.

    This pattern is used by sites built with WordPress, Elementor, and the Jet Engine plugin.
    The press releases are displayed in a grid with each item containing an h3 link and
    an elementor-icon-list-text span for the date.

    Args:
        urls: List of URLs to scrape (default: None)
        page: Page number for pagination (default: 1)

    Returns:
        List of dictionaries with keys: source, url, title, date, domain

    Example URLs:
        - https://www.scott.senate.gov/media-center/press-releases
        - https://www.fetterman.senate.gov/press-releases
        - https://www.tester.senate.gov/newsroom/press-releases
    """
    results = []
    if urls is None:
        urls = []

    for url in urls:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        # Handle different URL structures for pagination
        if "?jsf=" in url:
            source_url = f"{url}&pagenum={page}"
        elif "/pagenum/" in url:
            source_url = url.replace("/pagenum/1/", f"/pagenum/{page}/")
        else:
            source_url = f"{url}?jsf=jet-engine:press-list&pagenum={page}"

        doc = cls.open_html(source_url)
        if not doc:
            continue

        # Try both possible selectors for jet listing items
        items = doc.select(".jet-listing-grid__item")
        if not items:
            items = doc.select(".elementor-widget-wrap")

        for row in items:
            link = row.select_one("h3 a")
            if not link:
                continue

            # Try multiple selectors for date
            date_elem = (
                row.select_one("span.elementor-icon-list-text") or
                row.select_one("li span.elementor-icon-list-text") or
                row.select_one(".elementor-post-date")
            )

            date = None
            if date_elem:
                date_text = date_elem.text.strip()
                date_formats = [
                    "%B %d, %Y",     # January 15, 2024
                    "%m/%d/%Y",      # 01/15/2024
                    "%m/%d/%y",      # 01/15/24
                ]

                for fmt in date_formats:
                    try:
                        date = datetime.datetime.strptime(date_text, fmt).date()
                        break
                    except ValueError:
                        continue

            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)

    return results
```

### Method 3: `article_block_h2_p_date()` (Enhanced version)

```python
@classmethod
def article_block_h2_p_date(cls, urls=None, page=1):
    """
    Scrape press releases from websites with ArticleBlock class, h2 titles, and date in p tag.

    This is an enhanced version that handles multiple date formats automatically.
    Used by many Senate sites that use the ArticleBlock layout pattern.

    Args:
        urls: List of URLs to scrape (default: None)
        page: Page number for pagination (default: 1)

    Returns:
        List of dictionaries with keys: source, url, title, date, domain

    Example URLs:
        - https://www.durbin.senate.gov/newsroom/press-releases
        - https://www.brown.senate.gov/newsroom/press
        - https://www.crapo.senate.gov/media/newsreleases
    """
    results = []
    if urls is None:
        urls = []

    for url in urls:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        # Handle different URL structures for pagination
        if "PageNum_rs" in url or "?" in url:
            source_url = f"{url}&PageNum_rs={page}" if "?" in url else f"{url}?PageNum_rs={page}"
        else:
            source_url = f"{url}?PageNum_rs={page}"

        doc = cls.open_html(source_url)
        if not doc:
            continue

        blocks = doc.select("div.ArticleBlock")
        for row in blocks:
            link = row.select_one("h2 a")
            if not link:
                # Fallback to h3 if h2 not found
                link = row.select_one("h3 a")

            if not link:
                continue

            # Get date from p tag or time tag
            date_elem = row.select_one("p") or row.select_one("time")
            date = None

            if date_elem:
                date_text = date_elem.text.strip()
                if date_elem.name == 'time' and date_elem.get('datetime'):
                    date_text = date_elem.get('datetime')

                # Replace dots with slashes for consistent parsing
                date_text_normalized = date_text.replace(".", "/")

                # Try multiple date formats
                date_formats = [
                    "%m/%d/%y",      # 01/15/24 or 01.15.24
                    "%m/%d/%Y",      # 01/15/2024 or 01.15.2024
                    "%B %d, %Y",     # January 15, 2024
                    "%b %d, %Y",     # Jan 15, 2024
                    "%Y-%m-%d",      # 2024-01-15 (ISO format from datetime attr)
                ]

                for fmt in date_formats:
                    try:
                        date = datetime.datetime.strptime(date_text_normalized, fmt).date()
                        break
                    except ValueError:
                        try:
                            # Try with original text if normalized doesn't work
                            date = datetime.datetime.strptime(date_text, fmt).date()
                            break
                        except ValueError:
                            continue

            result = {
                'source': url,
                'url': link.get('href'),
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)

    return results
```

### Method 4: `table_time()`

```python
@classmethod
def table_time(cls, urls=None, page=1):
    """
    Scrape press releases from websites with simple table tr structure and time element.

    This pattern is used by House sites that display press releases in a table
    with a time element for dates.

    Args:
        urls: List of URLs to scrape (default: None)
        page: Page number for pagination (default: 1)

    Returns:
        List of dictionaries with keys: source, url, title, date, domain

    Example URLs:
        - https://barr.house.gov/media-center/press-releases
    """
    results = []
    if urls is None:
        urls = []

    for url in urls:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        source_url = f"{url}?page={page}"

        doc = cls.open_html(source_url)
        if not doc:
            continue

        # Skip first row (header)
        rows = doc.select("table tr")[1:]

        for row in rows:
            link = row.select_one("td a") or row.select_one("a")
            if not link:
                continue

            time_elem = row.select_one("time")
            date = None

            if time_elem:
                # Try datetime attribute first
                date_text = time_elem.get('datetime') or time_elem.text.strip()

                date_formats = [
                    "%m/%d/%y",      # 01/15/24
                    "%m/%d/%Y",      # 01/15/2024
                    "%Y-%m-%d",      # 2024-01-15
                    "%B %d, %Y",     # January 15, 2024
                ]

                for fmt in date_formats:
                    try:
                        date = datetime.datetime.strptime(date_text, fmt).date()
                        break
                    except ValueError:
                        continue

            # Handle relative URL
            href = link.get('href')
            if href.startswith('http'):
                full_url = href
            else:
                full_url = f"https://{domain}{href}"

            result = {
                'source': url,
                'url': full_url,
                'title': link.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)

    return results
```

### Method 5: `element_post_media()`

```python
@classmethod
def element_post_media(cls, urls=None, page=1):
    """
    Scrape press releases from websites with .element class and post-media-list structure.

    This pattern is used by some Senate sites that use a custom element layout
    with post-media-list-title and post-media-list-date classes.

    Args:
        urls: List of URLs to scrape (default: None)
        page: Page number for pagination (default: 1)

    Returns:
        List of dictionaries with keys: source, url, title, date, domain

    Example URLs:
        - https://www.wicker.senate.gov/media/press-releases
        - https://www.tillis.senate.gov/media/press-releases (possibly)
    """
    results = []
    if urls is None:
        urls = []

    for url in urls:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        source_url = f"{url}?page={page}"

        doc = cls.open_html(source_url)
        if not doc:
            continue

        elements = doc.select(".element")
        for row in elements:
            link = row.select_one('a')
            title_elem = row.select_one(".post-media-list-title") or row.select_one(".element-title")
            date_elem = row.select_one(".post-media-list-date") or row.select_one(".element-datetime")

            if not (link and title_elem and date_elem):
                continue

            date = None
            date_text = date_elem.text.strip()

            date_formats = [
                "%B %d, %Y",     # January 15, 2024
                "%m/%d/%Y",      # 01/15/2024
                "%m/%d/%y",      # 01/15/24
                "%m.%d.%Y",      # 01.15.2024
            ]

            for fmt in date_formats:
                try:
                    date = datetime.datetime.strptime(date_text, fmt).date()
                    break
                except ValueError:
                    continue

            result = {
                'source': url,
                'url': link.get('href'),
                'title': title_elem.text.strip(),
                'date': date,
                'domain': domain
            }
            results.append(result)

    return results
```

---

## Migration Examples

Here are examples of how member-specific methods can be replaced with generic method calls:

### Example 1: moran() → table_recordlist_date()

**Before:**
```python
@classmethod
def moran(cls, page=1):
    """Scrape Senator Moran's press releases."""
    results = []
    domain = "www.moran.senate.gov"
    url = f"https://www.moran.senate.gov/public/index.cfm/news-releases?page={page}"
    doc = cls.open_html(url)
    if not doc:
        return []

    rows = doc.select("table tbody tr")
    for row in rows:
        link = row.select_one('a')
        date_cell = row.select_one('td.recordListDate')

        if not (link and date_cell):
            continue

        date = None
        try:
            date = datetime.datetime.strptime(date_cell.text.strip(), "%m/%d/%y").date()
        except ValueError:
            pass

        result = {
            'source': url,
            'url': f"https://www.moran.senate.gov{link.get('href')}",
            'title': link.text.strip(),
            'date': date,
            'domain': domain
        }
        results.append(result)

    return results
```

**After:**
```python
@classmethod
def moran(cls, page=1):
    """Scrape Senator Moran's press releases."""
    return cls.table_recordlist_date(
        urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
        page=page
    )
```

**Lines of code**: 30+ → 4 (87% reduction)

---

### Example 2: fetterman() → jet_listing_elementor()

**Before:**
```python
@classmethod
def fetterman(cls, page=1):
    """Scrape Senator Fetterman's press releases."""
    results = []
    domain = 'www.fetterman.senate.gov'
    url = f"https://www.fetterman.senate.gov/press-releases/?jsf=jet-engine:press-list&pagenum={page}"
    doc = cls.open_html(url)
    if not doc:
        return []

    items = doc.select(".jet-listing-grid__item")
    for row in items:
        link = row.select_one("h3 a")
        if not link:
            continue
        date_elem = row.select_one("span.elementor-icon-list-text")
        date = None
        if date_elem:
            try:
                date = datetime.datetime.strptime(date_elem.text.strip(), "%B %d, %Y").date()
            except ValueError:
                pass

        result = {
            'source': url,
            'url': link.get('href'),
            'title': link.text.strip(),
            'date': date,
            'domain': domain
        }
        results.append(result)

    return results
```

**After:**
```python
@classmethod
def fetterman(cls, page=1):
    """Scrape Senator Fetterman's press releases."""
    return cls.jet_listing_elementor(
        urls=["https://www.fetterman.senate.gov/press-releases/?jsf=jet-engine:press-list"],
        page=page
    )
```

**Lines of code**: 30+ → 4 (87% reduction)

---

## Impact Summary

### Code Reduction
- **Before**: ~2,000+ lines of duplicated code across 60+ methods
- **After**: ~400 lines (5 generic methods + 60 simple wrapper methods)
- **Reduction**: ~80% less code

### Maintenance Benefits
- **Single source of truth**: Bug fixes in one place benefit all methods
- **Easier testing**: Test generic methods once instead of 60+ times
- **Faster development**: New members can be added with 4 lines instead of 30+
- **Better reliability**: Proven, tested patterns reduce bugs

### Affected Methods (60+)

**table_recordlist_date()**: moran, boozman, thune, barrasso, graham, ernst, risch, hoeven, lankford, vanhollen (10+)

**jet_listing_elementor()**: timscott, fetterman, tester, hawley, marshall, britt, toddyoung, markkelly, hagerty, jayapal, lujan, ossoff, padilla, mullin, rosen (15+)

**article_block_h2_p_date()**: crapo, sherrod_brown, durbin, bennet, cardin, carper, casey, coons, hirono, manchin, menendez, merkley, stabenow, kennedy, garypeters, jackreed, rounds, kaine, blackburn, gillibrand, heinrich (40+)

**table_time()**: barr (5+)

**element_post_media()**: wicker, tillis (3+)

---

## Testing Requirements

Each new generic method should have comprehensive tests covering:

1. **Valid HTML parsing**: Test with sample HTML matching the expected pattern
2. **Multiple date formats**: Verify all supported date formats are parsed correctly
3. **Missing elements**: Handle gracefully when elements are missing
4. **Empty results**: Return empty list when no data found
5. **Pagination**: Verify page parameter is applied correctly
6. **URL handling**: Test both absolute and relative URLs
7. **Multiple URLs**: Verify batch processing works correctly
8. **Edge cases**: Test with malformed HTML, network errors, etc.

See the accompanying `test_generic_scrapers.py` file for complete test suite.

---

## Rollout Plan

1. **Phase 1**: Implement the 5 new generic methods
2. **Phase 2**: Write comprehensive tests for each generic method
3. **Phase 3**: Migrate 5-10 member methods as proof of concept
4. **Phase 4**: Run tests to ensure functionality is preserved
5. **Phase 5**: Migrate remaining methods in batches
6. **Phase 6**: Remove deprecated code and update documentation

---

## Conclusion

This consolidation will significantly improve code maintainability, reduce bugs, and make it easier to add new congressional members in the future. The generic methods are more robust with better error handling and support for multiple date formats automatically.
