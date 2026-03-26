# Scraper Guide

A practical guide to adding new scrapers and fixing broken ones for congressional press release sites.

## Quick Start: Adding a New Site

### Step 1: Run Pattern Detection

```bash
uv run python scripts/detect_pattern.py https://newmember.house.gov/press
```

This tests 14 known HTML patterns against the page and recommends a config entry with CSS selectors. If it finds a match, it prints a ready-to-use config dict and then **verifies** the recommendation by running it through `generic_scraper()` — checking that results are returned, dates parse correctly, URLs are absolute, and pagination works.

Use `--no-verify` to skip verification for faster scanning.

### Step 2: Add the Config Entry

Edit `python_statement/config.py` and add the entry to `SCRAPER_CONFIG` (alphabetically):

```python
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

If the site matches one of the batch generic patterns (media_body, article_block_h2_p_date, etc.), use that method name instead:

```python
'newmember': {
    'method': 'media_body',
    'url_base': 'https://newmember.house.gov/media/press-releases'
},
```

### Step 3: Test

Wrapper methods are auto-generated from the config — no need to edit `scraper.py` or `member_methods()`. Just test:

```python
from python_statement import Scraper

results = Scraper.newmember(page=1)
print(f"Page 1: {len(results)} results")
for r in results[:3]:
    print(f"  {r['date']} - {r['title'][:60]}")

results2 = Scraper.newmember(page=2)
print(f"Page 2: {len(results2)} results")
```

## Generic Dispatcher Config Keys

For `'method': 'generic'` entries, these config keys control scraping behavior:

| Key | Required | Description | Example |
|-----|----------|-------------|---------|
| `url_base` | Yes | Base URL of the press page | `'https://member.senate.gov/news'` |
| `container` | Yes | CSS selector for each press release item | `'article'`, `'.jet-listing-grid__item'` |
| `title_sel` | Yes | CSS selector for title within container | `'h2 a'`, `'a'` |
| `date_sel` | No | CSS selector for date within container | `'time'`, `'span.published'` |
| `date_fmt` | No | List of strptime format strings | `['%B %d, %Y', '%m/%d/%y']` |
| `date_attr` | No | HTML attribute to read date from | `'datetime'` |
| `date_from_next_sibling` | No | Read date from text node after date_sel element | `True` |
| `pagination` | No | URL suffix with `{page}` placeholder | `'?page={page}'` |
| `url_prefix` | No | Path prefix for relative URLs | `'/news/'` |
| `skip_first` | No | Number of container elements to skip | `1` (for header rows) |
| `link_sel` | No | CSS selector for link if different from title | `'h3 a'` |
| `link_attr` | No | Attribute for URL if not `href` | |
| `base_domain` | No | Override domain for URL construction | |
| `max_results` | No | Limit results returned | |

## Batch Generic Methods

For sites that share an identical HTML structure, use one of the batch generic methods instead of `'method': 'generic'`. These require only `url_base`:

| Method | HTML Pattern | Sites | Typical Use |
|--------|-------------|-------|-------------|
| `media_body` | `.media-body` with `<time>` | 230+ House | Most House members |
| `article_block_h2_p_date` | `div.ArticleBlock` with `h2 a` + `p` date | 16+ Senate | Senate sites |
| `jet_listing_elementor` | `.jet-listing-grid__item` | 13 Senate | WordPress/Elementor |
| `table_recordlist_date` | `table` with `td.recordListDate` | 5 Senate | Table layouts |
| `element_post_media` | `div.element` with post-media classes | 3 Senate | Custom element layout |
| `table_time` | `table tr` with `<time>` | House | Simple table layout |

## Patterns Detected by detect_pattern.py

The pattern detection tool tests these 14 patterns (in order):

1. **media_body** — `.media-body` containers with `<time>` dates
2. **ArticleBlock** — `div.ArticleBlock` with `h2 a` titles
3. **jet_listing_grid** — `.jet-listing-grid__item` (WordPress/Elementor)
4. **et_pb_post** — `article.et_pb_post` (Divi theme)
5. **table_recordlist** — `table.recordList tr` with `td.recordListDate`
6. **table_time** — `tr` containers with `td a` titles and `<time>` dates
7. **documentquery_article** — `article` with `h2 a` and `<time>`
8. **documentquery_middot** — `article` with `span.middot` + sibling date text
9. **news_texthold** — `.news-texthold` with `h2 a` and `<time>`
10. **views_row** — `.views-row` with `.evo-card-date`
11. **element_post_media** — `div.element` with `span.element-datetime`
12. **elementor_post_card** — `.elementor-post__card` with `span.elementor-post-date`
13. **wordpress_article** — `article` with `h2 a` and `<time>`
14. **PageList_item** — `li.PageList__item`

## Writing Custom Scrapers

Write a custom scraper only when no pattern matches. Only ~7 scrapers need custom code (e.g., AJAX-loaded content, JSON APIs, unusual DOM structures).

Template:

```python
@classmethod
def lastname(cls, page=1):
    """Scrape Representative/Senator Lastname's press releases."""
    results = []
    domain = 'lastname.house.gov'
    url = f"https://{domain}/news/press-releases?page={page}"

    doc = cls.open_html(url)
    if not doc:
        return []

    containers = doc.select('.container-class')
    for container in containers:
        link = container.select_one('a')
        if not link:
            continue

        title = link.text.strip()
        href = link.get('href')
        if not href.startswith('http'):
            href = f"https://{domain}{href}"

        date = None
        date_elem = container.select_one('time')
        if date_elem:
            try:
                date = datetime.datetime.strptime(
                    date_elem.get('datetime', date_elem.text.strip()),
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                pass

        results.append({
            'source': url,
            'url': href,
            'title': title,
            'date': date,
            'domain': domain
        })

    return results
```

## Fixing Broken Scrapers

### Finding Broken Scrapers

```bash
# Run quick health check
make health-quick

# Or full check
make health
```

Results show status for each scraper: `+` OK, `-` empty, `?` no dates, `X` error.

### Debugging Process

1. **Test the URL:**
   ```python
   doc = Scraper.open_html('https://member.senate.gov/press')
   print("Loaded" if doc else "URL broken")
   ```

2. **Run pattern detection on the current URL:**
   ```bash
   uv run python scripts/detect_pattern.py https://member.senate.gov/press
   ```

3. **If the pattern changed:** Update the config entry in `config.py`

4. **If the URL changed:** Find the new press page URL and update `url_base`

### Common Issues

- **404 errors** — URL structure changed. Visit the site, find the new press page URL.
- **Empty results** — HTML structure changed. Run `detect_pattern.py` to identify new selectors.
- **No dates** — Date format or selector changed. Check the HTML and update `date_sel`/`date_fmt`.
- **Page 1 works, page 2 fails** — Pagination pattern changed. Update the `pagination` config key.

## Date Parsing

All date parsing uses `Utils.parse_date(text, formats)` which tries strptime formats first (with dot→slash normalization), then falls back to `dateutil.parser.parse(fuzzy=True)`. Never write raw strptime try/except blocks — use the helper.

For `'method': 'generic'` configs, list formats to try in `date_fmt`:

```python
'date_fmt': ['%B %d, %Y', '%m/%d/%y', '%Y-%m-%d']
```

Common formats:
- `%m/%d/%y` — 01/15/24
- `%m/%d/%Y` — 01/15/2024
- `%m.%d.%y` — 01.15.24
- `%B %d, %Y` — January 15, 2024
- `%Y-%m-%d` — 2024-01-15 (ISO, common in `<time datetime="">`)

For sites with `<time datetime="...">`, use `date_attr: 'datetime'` to read the attribute directly.

For sites where the date is a text node after a marker element (e.g., `<span class="middot">&middot;</span> 01/15/2024`), use `date_from_next_sibling: True`.

## Required Return Format

Every scraper returns a list of dicts with these keys:

```python
{
    'source': 'https://site.gov/press',      # List page URL
    'url': 'https://site.gov/press/123',     # Individual release URL
    'title': 'Press Release Title',          # Title text
    'date': datetime.date(2024, 1, 15),      # Date object or None
    'domain': 'site.gov'                     # Domain name
}
```

## File Locations

| What | Where |
|------|-------|
| Scraper config | `python_statement/config.py` — `SCRAPER_CONFIG` dict |
| Wrapper methods | `python_statement/scraper.py` — `Scraper` class |
| Generic dispatcher | `python_statement/scraper.py` — `generic_scraper()` |
| Health checker | `python_statement/health.py` — `HealthChecker` class |
| Pattern detection | `scripts/detect_pattern.py` |
| Health check CLI | `scripts/run_health_check.py` |
| CI workflow | `.github/workflows/scraper-health.yml` |
