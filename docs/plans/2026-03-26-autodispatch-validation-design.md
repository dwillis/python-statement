# Design: Auto-Dispatch + Config Schema Validation

**Date:** 2026-03-26

## Feature 1: Auto-Dispatch (Eliminate Wrapper Boilerplate)

### Problem
Every scraper needs a 2-line wrapper method in `scraper.py` plus a `member_methods()` entry. Forgetting either is the most common failure mode when adding a new site. Also, `member_methods()` returns bound method objects instead of strings, which causes a bug in health checker full mode.

### Approach
Auto-generate wrapper methods at import time by iterating SCRAPER_CONFIG.

### Behavior
At the bottom of `scraper.py`, after the class definition:

```python
def _make_scraper_method(name):
    @classmethod
    def method(cls, page=1):
        return cls.run_scraper(name, page)
    method.__doc__ = f"Scrape {name} press releases."
    method.__name__ = name
    return method

for _name in SCRAPER_CONFIG:
    if not hasattr(Scraper, _name):
        setattr(Scraper, _name, _make_scraper_method(_name))
```

- Existing custom methods (joyce, cornyn, etc.) are untouched — `hasattr` skips them
- Existing hand-written 2-line wrappers can be deleted (they'll be auto-generated)
- `member_methods()` replaced to return `sorted(SCRAPER_CONFIG.keys())` — fixes health checker bug
- Adding a new scraper becomes a single edit to `config.py`

### Files Modified
- `python_statement/scraper.py` — add auto-generation, delete ~380 wrapper methods, rewrite `member_methods()`

---

## Feature 2: Config Schema Validation

### Problem
Typos in SCRAPER_CONFIG entries (wrong key names, missing required keys, wrong types) are only caught at runtime when a scraper is called.

### Approach
Import-time validation in `config.py` with zero new dependencies.

### Rules

**All entries:** Must have `method` (string) and `url_base` (string). `method` must be a known method name.

**`generic` entries:** Must also have `container` and `title_sel`. `date_fmt` must be a list if present. Only allowed keys from a whitelist (catches typos).

### Allowed Keys
```python
VALID_GENERIC_KEYS = {
    'method', 'url_base', 'container', 'title_sel', 'date_sel',
    'date_fmt', 'date_attr', 'date_from_next_sibling', 'pagination',
    'url_prefix', 'skip_first', 'link_sel', 'link_attr', 'base_domain',
    'max_results',
}
```

### On Failure
Raises `ValueError` with scraper name and specific issue at import time.

### Files Modified
- `python_statement/config.py` — add `validate_config()` function, call at bottom of file
