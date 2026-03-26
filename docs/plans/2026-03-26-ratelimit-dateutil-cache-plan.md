# Rate Limiting, dateutil Fallback & Disk Cache Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 0.5s rate limiting between HTTP requests, centralize date parsing with dateutil fallback, and add opt-in disk caching for development.

**Architecture:** Rate limiting is a one-line `time.sleep(0.5)` in `open_html()`. Date parsing is centralized into a `Utils.parse_date()` helper that tries strptime formats then falls back to `dateutil.parser.parse(fuzzy=True)`, replacing ~40 strptime call sites. Disk caching stores raw HTTP response bytes in `~/.cache/python-statement/` keyed by URL SHA-256 hash, with configurable TTL. Cache is off by default, opt-in via `Scraper.enable_cache()`.

**Tech Stack:** Python 3.12+, python-dateutil (already a dependency), hashlib, shutil (stdlib)

---

### Task 1: Add `parse_date()` helper to Utils

**Files:**
- Modify: `python_statement/utils.py`

**Step 1: Add the `parse_date` static method to the Utils class**

Add this method to the `Utils` class in `python_statement/utils.py` after `remove_generic_urls()` (after line 48):

```python
    @staticmethod
    def parse_date(text, formats=None):
        """Parse a date string, trying explicit formats first, then dateutil fallback.

        Args:
            text: Date string to parse (e.g., "January 15, 2024", "01/15/24")
            formats: Optional list of strptime format strings to try first

        Returns:
            datetime.date or None
        """
        if not text:
            return None
        text = text.strip()
        if not text:
            return None

        if formats:
            import datetime
            # Try with normalized separators (dots → slashes)
            normalized = text.replace('.', '/')
            for fmt in formats:
                try:
                    return datetime.datetime.strptime(normalized, fmt).date()
                except ValueError:
                    continue
            # Try original text (unnormalized)
            for fmt in formats:
                try:
                    return datetime.datetime.strptime(text, fmt).date()
                except ValueError:
                    continue

        # Fallback: dateutil fuzzy parsing
        try:
            from dateutil import parser as dateutil_parser
            return dateutil_parser.parse(text, fuzzy=True).date()
        except (ValueError, OverflowError, TypeError):
            return None
```

Also add `import datetime` at the top of the file (after line 5):

```python
import datetime
```

**Step 2: Verify the helper works**

```bash
uv run python -c "
from python_statement.utils import Utils

# Test with explicit formats
d = Utils.parse_date('01/15/24', ['%m/%d/%y'])
assert str(d) == '2024-01-15', f'Got {d}'

# Test dot normalization
d = Utils.parse_date('01.15.24', ['%m/%d/%y'])
assert str(d) == '2024-01-15', f'Got {d}'

# Test dateutil fallback (no formats)
d = Utils.parse_date('January 15, 2024')
assert str(d) == '2024-01-15', f'Got {d}'

# Test dateutil fallback (formats fail)
d = Utils.parse_date('Mar 5, 2026', ['%m/%d/%y'])
assert str(d) == '2026-03-05', f'Got {d}'

# Test None/empty
assert Utils.parse_date(None) is None
assert Utils.parse_date('') is None
assert Utils.parse_date('   ') is None

# Test garbage
assert Utils.parse_date('not a date') is None

print('All parse_date tests passed')
"
```
Expected: `All parse_date tests passed`

**Step 3: Commit**

```bash
git add python_statement/utils.py
git commit -m "$(cat <<'EOF'
Add Utils.parse_date() helper with dateutil fallback

Centralizes date parsing: tries strptime formats first (with dot
normalization), then falls back to dateutil.parser.parse(fuzzy=True).
Returns datetime.date or None.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Replace strptime calls in `generic_scraper()` with `parse_date()`

**Files:**
- Modify: `python_statement/scraper.py:159-192`

**Step 1: Replace the date parsing block in `generic_scraper()`**

In `python_statement/scraper.py`, the date parsing block at lines 159-192 currently does manual strptime loops. Replace lines 176-192 (the `if date_text:` block that does strptime) with a single call:

Replace this block (lines 176-192):
```python
                    if date_text:
                        # Normalize common separators
                        date_text_normalized = date_text.replace('.', '/')
                        for fmt in date_fmts:
                            try:
                                date = datetime.datetime.strptime(date_text_normalized, fmt).date()
                                break
                            except ValueError:
                                continue
                        # If none of the formats worked, try the original text
                        if date is None:
                            for fmt in date_fmts:
                                try:
                                    date = datetime.datetime.strptime(date_text, fmt).date()
                                    break
                                except ValueError:
                                    continue
```

With:
```python
                    if date_text:
                        date = Utils.parse_date(date_text, date_fmts)
```

**Step 2: Run existing tests**

```bash
uv run pytest tests/test_statement.py -v
```
Expected: All tests pass.

**Step 3: Commit**

```bash
git add python_statement/scraper.py
git commit -m "$(cat <<'EOF'
Use Utils.parse_date() in generic_scraper()

Replaces 17-line strptime loop with single parse_date() call.
Adds dateutil fallback for unrecognized date formats.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Replace strptime calls in batch generic methods

**Files:**
- Modify: `python_statement/scraper.py` — all batch generic methods

**Step 1: Replace strptime in `media_body()` (line 344-347)**

Find the try/except blocks in `media_body()` around lines 340-350 that look like:
```python
                    try:
                        date = datetime.datetime.strptime(date_attr, "%Y-%m-%d").date()
                    except ValueError:
                        try:
                            date = datetime.datetime.strptime(time_elem.text, "%B %d, %Y").date()
                        except ValueError:
                            pass
```

Replace with:
```python
                    date = Utils.parse_date(date_attr, ["%Y-%m-%d"])
                    if date is None:
                        date = Utils.parse_date(time_elem.text, ["%B %d, %Y"])
```

Apply the same pattern to ALL strptime call sites in batch methods. For each one:

**Pattern A — Single format try/except:**
```python
# Before:
try:
    date = datetime.datetime.strptime(text, "%B %d, %Y").date()
except ValueError:
    pass

# After:
date = Utils.parse_date(text, ["%B %d, %Y"])
```

**Pattern B — Multiple format try/except chain:**
```python
# Before:
try:
    date = datetime.datetime.strptime(text, "%m/%d/%y").date()
except ValueError:
    try:
        date = datetime.datetime.strptime(text, "%B %d, %Y").date()
    except ValueError:
        pass

# After:
date = Utils.parse_date(text, ["%m/%d/%y", "%B %d, %Y"])
```

**Pattern C — Format loop in a batch method:**
```python
# Before:
for fmt in [...]:
    try:
        date = datetime.datetime.strptime(date_text, fmt).date()
        break
    except ValueError:
        continue

# After:
date = Utils.parse_date(date_text, [...])
```

**Full list of methods and approximate line numbers to update** (all in `scraper.py`):

1. `media_body()` — lines ~344-347 (two formats: %Y-%m-%d, %B %d, %Y)
2. `marshall()` — lines ~393-401 (two formats: %m/%d/%y, %B %d, %Y)
3. `article_block()` — lines ~745-750 (one format: %B %d, %Y)
4. Lines ~788-793 (one format: %B %d, %Y)
5. Lines ~836 (one format: %B %d, %Y)
6. Lines ~877 (one format: %B %d, %Y)
7. Lines ~922-924 (two formats: %Y-%m-%d, %B %d, %Y)
8. Lines ~981-995 (three formats: %B %d, %Y, %m/%d/%y, %m.%d.%y)
9. Lines ~1040 (one format: %B %d, %Y)
10. `jet_listing_elementor()` — lines ~450, ~494, ~546-549, ~591 (various)
11. `table_recordlist_date()` — lines ~638, ~695-698 (two formats)
12. `table_time()` — lines ~1414+ (format loop)
13. `element_post_media()` — lines ~1549 (format loop)
14. `tokuda()` — line ~1594
15. `fischer()` — line ~1869
16. `kennedy()` — line ~1903
17. `clark()` — line ~1941
18. Custom methods with strptime at lines ~1181, ~1293, ~1392-1397, ~1468, ~1682, ~1719, ~1757

**Note:** Do NOT change `house_gop()` at line 253 — it parses a URL query parameter, not page content. Leave it as-is.

Also do NOT change `media_digest()` at line 1981 — it uses `datetime.datetime.fromisoformat()`, not strptime.

**Step 2: Run all tests**

```bash
uv run pytest tests/ -v
```
Expected: All tests pass.

**Step 3: Commit**

```bash
git add python_statement/scraper.py
git commit -m "$(cat <<'EOF'
Replace all strptime calls in batch methods with Utils.parse_date()

Replaces ~35 try/except strptime blocks across all batch generic
methods and custom scrapers with Utils.parse_date(). Every scraper
now benefits from dateutil fallback for unrecognized date formats.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Add rate limiting to `open_html()`

**Files:**
- Modify: `python_statement/scraper.py:205-231`

**Step 1: Add `time.sleep(0.5)` at the start of `open_html()`**

`time` is already imported (line 10). Change `open_html()` at line 205-208 from:

```python
    @staticmethod
    def open_html(url):
        """Open an HTML page and return a BeautifulSoup object."""
        try:
```

To:

```python
    @staticmethod
    def open_html(url):
        """Open an HTML page and return a BeautifulSoup object."""
        time.sleep(0.5)  # Rate limit: be polite to congressional servers
        try:
```

**Step 2: Verify it works**

```bash
uv run python -c "
import time
from python_statement import Scraper

start = time.time()
# open_html on a non-existent URL should still sleep before failing
Scraper.open_html('http://localhost:1/nonexistent')
elapsed = time.time() - start
assert elapsed >= 0.5, f'Expected >= 0.5s, got {elapsed:.2f}s'
print(f'Rate limiting working: {elapsed:.2f}s elapsed')
"
```
Expected: `Rate limiting working: 0.5Xs elapsed` (where X is small)

**Step 3: Commit**

```bash
git add python_statement/scraper.py
git commit -m "$(cat <<'EOF'
Add 0.5s rate limiting delay to open_html()

Sleeps 0.5s before every HTTP request to be polite to congressional
servers during batch scraping.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Add opt-in disk cache to `open_html()`

**Files:**
- Modify: `python_statement/scraper.py`

**Step 1: Add cache class variables and methods**

Add these after the `SCRAPER_CONFIG = SCRAPER_CONFIG` line (after line 23), before `run_scraper()`:

```python
    # Opt-in disk cache for HTTP responses (off by default)
    _cache_enabled = False
    _cache_dir = os.path.expanduser('~/.cache/python-statement')
    _cache_ttl = 3600  # seconds

    @classmethod
    def enable_cache(cls, ttl=3600, cache_dir=None):
        """Enable disk caching of HTTP responses.

        Args:
            ttl: Cache time-to-live in seconds (default: 1 hour)
            cache_dir: Custom cache directory (default: ~/.cache/python-statement)
        """
        cls._cache_enabled = True
        cls._cache_ttl = ttl
        if cache_dir:
            cls._cache_dir = cache_dir
        os.makedirs(cls._cache_dir, exist_ok=True)

    @classmethod
    def disable_cache(cls):
        """Disable disk caching (HTTP requests go to the network)."""
        cls._cache_enabled = False

    @classmethod
    def clear_cache(cls):
        """Delete all cached HTTP responses."""
        import shutil
        if os.path.exists(cls._cache_dir):
            shutil.rmtree(cls._cache_dir)
```

**Step 2: Add `import hashlib` at the top of scraper.py**

Add after `import os` (line 12):
```python
import hashlib
```

**Step 3: Change `open_html()` from `@staticmethod` to `@classmethod` and add cache logic**

Replace the entire `open_html()` method (lines 205-231) with:

```python
    @classmethod
    def open_html(cls, url):
        """Open an HTML page and return a BeautifulSoup object.

        If caching is enabled via enable_cache(), checks for a cached
        response before making an HTTP request. Cached responses are
        stored as raw bytes in ~/.cache/python-statement/.
        """
        # Check cache first
        cache_path = None
        if cls._cache_enabled:
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            cache_path = os.path.join(cls._cache_dir, url_hash)
            if os.path.exists(cache_path):
                age = time.time() - os.path.getmtime(cache_path)
                if age < cls._cache_ttl:
                    try:
                        with open(cache_path, 'rb') as f:
                            content = f.read()
                        try:
                            return BeautifulSoup(content, 'lxml')
                        except Exception:
                            return BeautifulSoup(content, 'html.parser')
                    except OSError:
                        pass  # Cache read failed, fetch from network

        time.sleep(0.5)  # Rate limit: be polite to congressional servers
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Write to cache before parsing
            if cache_path is not None:
                try:
                    os.makedirs(cls._cache_dir, exist_ok=True)
                    with open(cache_path, 'wb') as f:
                        f.write(response.content)
                except OSError:
                    pass  # Cache write failed, not critical

            try:
                return BeautifulSoup(response.content, 'lxml')
            except Exception:
                return BeautifulSoup(response.content, 'html.parser')

        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            print(f"Error opening HTML page {url}: {e}")
            return None
```

**Step 4: Verify cache works**

```bash
uv run python -c "
import time, os
from python_statement import Scraper

# Enable cache with short TTL for testing
cache_dir = '/tmp/test-statement-cache'
Scraper.enable_cache(ttl=60, cache_dir=cache_dir)

# First call: cache miss (network + sleep)
start = time.time()
doc1 = Scraper.open_html('https://pelosi.house.gov/media/press-releases')
t1 = time.time() - start
print(f'First call: {t1:.2f}s (network)')

# Second call: cache hit (no sleep, no network)
start = time.time()
doc2 = Scraper.open_html('https://pelosi.house.gov/media/press-releases')
t2 = time.time() - start
print(f'Second call: {t2:.2f}s (cache)')

assert t2 < t1, f'Cache should be faster: {t2:.2f} vs {t1:.2f}'
assert doc1 is not None
assert doc2 is not None

# Clean up
Scraper.clear_cache()
Scraper.disable_cache()
assert not os.path.exists(cache_dir)
print('Cache test passed')
"
```
Expected: First call takes ~1-3s, second call takes <0.1s.

**Step 5: Run all tests**

```bash
uv run pytest tests/ -v
```
Expected: All tests pass. Tests mock `open_html()` so cache doesn't interfere. The `@staticmethod` → `@classmethod` change is compatible because `cls.open_html(url)` calls work the same way.

**Step 6: Commit**

```bash
git add python_statement/scraper.py
git commit -m "$(cat <<'EOF'
Add opt-in disk cache to open_html()

Caches raw HTTP response bytes in ~/.cache/python-statement/
keyed by SHA-256 URL hash. Off by default — enable with
Scraper.enable_cache(ttl=3600). Cache hits skip the 0.5s
rate-limit delay. Includes clear_cache() and disable_cache().

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `SCRAPER_GUIDE.md`

**Step 1: Update CLAUDE.md**

In the "Important Implementation Notes" section, add a new subsection after "HTTP Requests":

```markdown
### Rate Limiting
`open_html()` sleeps 0.5s before every HTTP request. Cache hits bypass this delay.

### Date Parsing
Use `Utils.parse_date(text, formats)` for all date parsing. It tries strptime formats first, then falls back to `dateutil.parser.parse(fuzzy=True)`. Never write raw strptime try/except blocks.

### Disk Cache
`Scraper.enable_cache(ttl=3600)` enables file-based caching in `~/.cache/python-statement/`. Useful during development to avoid repeated HTTP requests. Off by default. Use `Scraper.clear_cache()` to reset.
```

**Step 2: Update SCRAPER_GUIDE.md**

In the "Date Parsing" section, add a note about `parse_date()`:

```markdown
All date parsing should use `Utils.parse_date(text, formats)` which tries strptime formats first, then falls back to dateutil. Never write raw strptime try/except blocks — use the helper.
```

**Step 3: Commit**

```bash
git add CLAUDE.md SCRAPER_GUIDE.md
git commit -m "$(cat <<'EOF'
Document rate limiting, parse_date(), and disk cache

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```
