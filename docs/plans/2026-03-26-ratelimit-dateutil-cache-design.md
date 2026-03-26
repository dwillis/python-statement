# Design: Rate Limiting, dateutil Fallback, Disk Cache

**Date:** 2026-03-26

## Feature 1: Rate Limiting (0.5s delay)

### Problem
`open_html()` fires HTTP requests with no delay, risking rate-limit blocks from congressional servers during batch scraping.

### Approach
Add `time.sleep(0.5)` at the top of `open_html()` before every request. Simple, stateless, predictable.

### Files Modified
- `python_statement/scraper.py` — add `import time`, add `time.sleep(0.5)` in `open_html()`

---

## Feature 2: Centralized `parse_date()` Helper

### Problem
Date parsing logic (strptime loop + normalization) is duplicated ~20 times across `generic_scraper()` and all batch generic methods. No fallback for unexpected date formats — if strptime fails, the date is silently None.

### Approach
Add `parse_date(text, formats=None)` to `Utils` class in `utils.py`. Tries strptime formats first (fast, predictable), then falls back to `dateutil.parser.parse(fuzzy=True)`. Replace all strptime call sites with `Utils.parse_date()`.

### Behavior
```python
def parse_date(text, formats=None):
    if not text:
        return None
    text = text.strip()
    if formats:
        normalized = text.replace('.', '/')
        for fmt in formats:
            try:
                return datetime.datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue
        for fmt in formats:
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    try:
        from dateutil import parser as dateutil_parser
        return dateutil_parser.parse(text, fuzzy=True).date()
    except (ValueError, OverflowError):
        return None
```

### Files Modified
- `python_statement/utils.py` — add `parse_date()` to Utils class
- `python_statement/scraper.py` — replace ~20 strptime call sites with `Utils.parse_date()`

---

## Feature 3: Opt-in Disk Cache

### Problem
During development and debugging, the same URLs are fetched repeatedly. Each fetch takes 1-3 seconds plus the new 0.5s delay, making iteration slow.

### Approach
File-based cache in `~/.cache/python-statement/` using SHA-256 URL hash as filename. 1-hour default TTL (checks file mtime). Off by default — opt-in via `Scraper.enable_cache()`.

### Behavior
```python
class Scraper:
    _cache_enabled = False
    _cache_dir = os.path.expanduser('~/.cache/python-statement')
    _cache_ttl = 3600

    @classmethod
    def enable_cache(cls, ttl=3600, cache_dir=None):
        cls._cache_enabled = True
        cls._cache_ttl = ttl
        if cache_dir:
            cls._cache_dir = cache_dir
        os.makedirs(cls._cache_dir, exist_ok=True)

    @classmethod
    def disable_cache(cls):
        cls._cache_enabled = False

    @classmethod
    def clear_cache(cls):
        if os.path.exists(cls._cache_dir):
            shutil.rmtree(cls._cache_dir)
```

`open_html()` changes from `@staticmethod` to `@classmethod`. Before fetching, checks cache. After fetching, writes to cache. Cache stores raw response bytes; BeautifulSoup parsing happens after cache read.

### Cache key
`hashlib.sha256(url.encode()).hexdigest()` — deterministic, no collisions in practice.

### TTL check
Compare `os.path.getmtime(cache_path)` against `time.time() - ttl`. Expired files are re-fetched.

### Files Modified
- `python_statement/scraper.py` — add cache class vars, `enable_cache()`, `disable_cache()`, `clear_cache()`, modify `open_html()` to check/write cache, change from `@staticmethod` to `@classmethod`
