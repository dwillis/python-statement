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
| `detail_date_sel` | No | Date selector on the item's detail page; followed only when the listing has no usable date | `'.col-auto'`, `'.date'` |
| `detail_date_attr` | No | Attribute to read the detail-page date from | `'datetime'` |
| `detail_date_fmt` | No | strptime formats for the detail-page date (defaults to `date_fmt`) | `['%B %d, %Y']` |

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

## Committee Scrapers

Committees are a separate collection in `python_statement/committee_config.py`. They use the same engine, methods and selector keys as member scrapers. The canonical committee list is [`committees-current.yaml`](https://github.com/unitedstates/congress-legislators/blob/main/committees-current.yaml) from unitedstates/congress-legislators.

### Entry rules

```python
'ssfi_minority': {
    'thomas_id': 'SSFI',     # required: committee id from committees-current.yaml
    'side': 'minority',      # required: 'majority' | 'minority' | 'full'
    'method': 'generic',
    'url_base': 'https://www.finance.senate.gov/newsroom/ranking-members-news/',
    'container': '.e-loop-item',
    'title_sel': '.elementor-heading-title a',
    'date_sel': 'time',
    'date_fmt': ['%m/%d/%y'],
    'pagination': '{page}/',
},
```

- The key must be `<thomas_id lowercase>_<side>`, and a typo is caught at import.
- `side` is the party's current status: majority means the chair's party. Use `full` only for a single shared, nonpartisan newsroom.
- Results get `committee` and `side` added automatically.
- Committees that publish no press releases, or can't be scraped, go in `COMMITTEE_SKIP` with a reason.

### Where committee newsrooms live

| Chamber | Majority | Minority |
|---------|----------|----------|
| House | Main host, e.g. `agriculture.house.gov` | Usually `democrats-<name>.house.gov` (Oversight: `oversightdemocrats.house.gov`) |
| Senate | Same host as the minority, chair's listing (e.g. `/newsroom/chairmans-news/`, `/press/majority`, `/republican/...`) | Ranking member's listing on the same host (`/newsroom/ranking-members-news/`, `/press/minority`, `/democratic/...`) |
| Joint | JEC: Republican newsroom | JEC: Democratic newsroom |

The YAML's `minority_url` values are stale: the House ones still point at `republicans-*` hosts. Find the live host instead of copying it.

### Workflow

1. **Discover:**
   ```bash
   uv run python scripts/discover_committee_press.py --only HSAG,SSFI --cache
   ```
   For each committee, this:
   - tries every party variant of House hosts and follows redirects;
   - assigns `side` from the final host's party label and `--house-majority`/`--senate-majority` (default `republicans`);
   - collects press listings from site navigation plus standard paths;
   - scores them with the `detect_pattern.py` patterns;
   - verifies the best through `run_scraper`.

   Output sections:
   - **READY**: verified entries to paste.
   - **NEEDS ATTENTION**: no dates, no working pagination, newest item 90+ days old, or a listing URL where no pattern matched. These need selectors written by hand.
   - **NO CANDIDATE**: blocked, 404, or no URL in the YAML.
   - **MISSING A SIDE**: only one side was found.
2. **Write selectors** for anything that needs them. Common committee layouts:
   - **House Drupal:** `.media-body` or `.views-row`; date in `.col-auto`; `?page={page}` with `page_offset: -1`.
   - **House `documentquery.aspx`:** `article` / `h2 a` / `time`; `&Page={page}`.
   - **House table views (`.../table`):** `tr` with `td a`, `time`; `?PageNum_rs={page}`.
   - **Senate `li.PageList__item`:** date in `p`; `?PageNum_rs={page}`.
   - **Senate Elementor:** `.e-loop-item`; pagination `{page}/`.
   - **Senate JetEngine:** `.jet-listing-grid__item`; `?jsf=jet-engine:press-list&pagenum={page}`.
3. **Verify** pages 1 and 2: dated, absolute URLs, different items, recent newest date.
4. **Check coverage:** `make generate-committees`. `committees_without_scrapers.json` should be empty, and the script warns about committees whose `thomas_id` has left the YAML (dissolved or renamed).
5. **Health:** `make health-committees`.
6. **Backfill** a new entry's history: `uv run python scripts/backfill.py --scraper hsag_minority --since 2025-01-03 --pages 50`. Before running a big backfill, check that `pagination` works past page 2.

### When majority control changes

At the start of a Congress where a chamber flips, `side` flips for every committee in that chamber. Swap `majority`/`minority` in those entries and their keys. Senate listings named by party (e.g. `/republican/...`) stay attached to the same party. Re-run discovery with the new `--house-majority`/`--senate-majority` to confirm.

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

Committee scrapers also return `'committee'` (thomas_id) and `'side'`.

## File Locations

| What | Where |
|------|-------|
| Scraper config | `python_statement/config.py` — `SCRAPER_CONFIG` dict |
| Committee config | `python_statement/committee_config.py` — `COMMITTEE_CONFIG`, `COMMITTEE_SKIP` |
| Wrapper methods | `python_statement/scraper.py` — `Scraper` class |
| Generic dispatcher | `python_statement/scraper.py` — `generic_scraper()` |
| Health checker | `python_statement/health.py` — `HealthChecker` class |
| Pattern detection | `scripts/detect_pattern.py` |
| Committee discovery | `scripts/discover_committee_press.py` |
| Committee coverage | `scripts/generate_committees.py` → `committees_with_scrapers.json`, `committees_without_scrapers.json` |
| Health check CLI | `scripts/run_health_check.py` |
| CI workflow | `.github/workflows/scraper-health.yml` |
