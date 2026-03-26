# Auto-Dispatch + Config Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate wrapper method boilerplate so adding a scraper is a single edit to config.py, and validate config entries at import time to catch typos immediately.

**Architecture:** Auto-generate wrapper methods from SCRAPER_CONFIG at import time using setattr. Validate all config entries with a whitelist of allowed keys and required-key checks. Rewrite member_methods() to return config key names.

**Tech Stack:** Python 3.12+, no new dependencies

---

### Task 1: Add config schema validation to config.py

**Files:**
- Modify: `python_statement/config.py`

**Step 1: Add validate_config() function and known-methods/keys constants**

Add this after the SCRAPER_CONFIG dict (after line 964), before any other code:

```python
VALID_METHODS = {
    'generic', 'media_body', 'article_block_h2_p_date',
    'jet_listing_elementor', 'table_recordlist_date',
    'element_post_media', 'table_time',
}

VALID_GENERIC_KEYS = {
    'method', 'url_base', 'container', 'title_sel', 'date_sel',
    'date_fmt', 'date_attr', 'date_from_next_sibling', 'pagination',
    'url_prefix', 'skip_first', 'link_sel', 'link_attr', 'base_domain',
    'max_results',
}

VALID_BATCH_KEYS = {'method', 'url_base'}


def validate_config():
    """Validate all SCRAPER_CONFIG entries at import time."""
    for name, config in SCRAPER_CONFIG.items():
        # All entries must have method and url_base
        if 'method' not in config:
            raise ValueError(f"Scraper '{name}': missing required key 'method'")
        if 'url_base' not in config:
            raise ValueError(f"Scraper '{name}': missing required key 'url_base'")

        method = config['method']
        if method not in VALID_METHODS:
            raise ValueError(
                f"Scraper '{name}': unknown method '{method}'. "
                f"Valid methods: {sorted(VALID_METHODS)}"
            )

        if method == 'generic':
            # Generic entries need container and title_sel
            if 'container' not in config:
                raise ValueError(f"Scraper '{name}': generic method requires 'container'")
            if 'title_sel' not in config:
                raise ValueError(f"Scraper '{name}': generic method requires 'title_sel'")

            # Check for unknown keys (catches typos)
            unknown = set(config.keys()) - VALID_GENERIC_KEYS
            if unknown:
                raise ValueError(
                    f"Scraper '{name}': unknown config keys {unknown}. "
                    f"Valid keys: {sorted(VALID_GENERIC_KEYS)}"
                )

            # date_fmt must be a list
            if 'date_fmt' in config and not isinstance(config['date_fmt'], list):
                raise ValueError(
                    f"Scraper '{name}': 'date_fmt' must be a list, "
                    f"got {type(config['date_fmt']).__name__}"
                )
        else:
            # Batch method entries should only have method and url_base
            unknown = set(config.keys()) - VALID_BATCH_KEYS
            if unknown:
                raise ValueError(
                    f"Scraper '{name}': batch method '{method}' only accepts "
                    f"'method' and 'url_base', got extra keys {unknown}"
                )


validate_config()
```

**Step 2: Test that validation catches errors**

```bash
uv run python -c "from python_statement.config import SCRAPER_CONFIG; print(f'{len(SCRAPER_CONFIG)} entries validated OK')"
```
Expected: `390 entries validated OK`

Then test that a bad config raises:
```bash
uv run python -c "
from python_statement.config import SCRAPER_CONFIG, validate_config
SCRAPER_CONFIG['__test_bad'] = {'method': 'generic', 'url_base': 'http://x', 'contaner': 'div'}
try:
    validate_config()
    print('ERROR: should have raised')
except ValueError as e:
    print(f'Caught: {e}')
finally:
    del SCRAPER_CONFIG['__test_bad']
"
```
Expected: `Caught: Scraper '__test_bad': generic method requires 'container'`

**Step 3: Commit**

```bash
git add python_statement/config.py
git commit -m "$(cat <<'EOF'
Add import-time config schema validation

Validates all SCRAPER_CONFIG entries when config.py loads:
required keys, valid method names, key whitelist for generic
entries, date_fmt type check. Catches typos immediately.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Add auto-dispatch and rewrite member_methods()

**Files:**
- Modify: `python_statement/scraper.py`

**Step 1: Delete all 2-line wrapper methods**

Remove all methods between line ~337 (first wrapper, `crapo`) and line ~2763 (last wrapper, `lucas`) that consist of exactly a docstring + `return cls.run_scraper('name', page)`. Keep the 7 custom methods:
- `marshall` (line 504) — custom pagination with posts_per_page
- `tokuda` (line 1697) — custom HTML parsing
- `cornyn` (line 1817) — custom JSON/AJAX
- `fischer` (line 1861) — custom HTML parsing
- `kennedy` (line 1913) — custom HTML parsing
- `clark` (line 2005) — custom HTML parsing
- `joyce` (line 2048) — custom HTML parsing

Also keep the batch generic methods (`media_body`, `article_block`, `article_block_h2`, `article_block_h2_date`, `table_recordlist_date`, `jet_listing_elementor`, `article_block_h2_p_date`, `table_time`, `element_post_media`, etc.) — these are NOT wrappers, they're the actual implementation methods.

**Step 2: Rewrite member_methods()**

Replace the current `member_methods()` (which returns a list of bound method objects) with:

```python
    @classmethod
    def member_methods(cls):
        """Return a list of all member scraper names."""
        return sorted(SCRAPER_CONFIG.keys())
```

This returns strings (config entry names), fixing the health checker full-mode bug.

**Step 3: Add auto-generation at the bottom of scraper.py**

After the class definition (at the very end of the file), add:

```python
# Auto-generate wrapper methods for all SCRAPER_CONFIG entries
# that don't already have a method on the Scraper class.
def _make_scraper_method(name):
    """Create a classmethod wrapper that calls run_scraper."""
    @classmethod
    def method(cls, page=1):
        return cls.run_scraper(name, page)
    method.__func__.__doc__ = f"Scrape {name} press releases."
    method.__func__.__name__ = name
    return method


for _name in SCRAPER_CONFIG:
    if not hasattr(Scraper, _name):
        setattr(Scraper, _name, _make_scraper_method(_name))
```

**Step 4: Test that auto-dispatch works**

```bash
uv run python -c "
from python_statement import Scraper
# Check a config-only scraper is callable
assert hasattr(Scraper, 'pelosi'), 'pelosi not found'
assert callable(Scraper.pelosi), 'pelosi not callable'
# Check a custom method still exists
assert hasattr(Scraper, 'joyce'), 'joyce not found'
# Check member_methods returns strings
methods = Scraper.member_methods()
assert isinstance(methods[0], str), f'Expected str, got {type(methods[0])}'
assert 'pelosi' in methods, 'pelosi not in member_methods'
print(f'OK: {len(methods)} scrapers, all strings')
"
```

**Step 5: Run existing tests**

```bash
uv run pytest tests/ -v
```
Expected: All tests pass. The test for `Scraper.crapo()` should still work via auto-dispatch since `crapo` is in SCRAPER_CONFIG.

**Step 6: Commit**

```bash
git add python_statement/scraper.py
git commit -m "$(cat <<'EOF'
Auto-generate scraper methods from SCRAPER_CONFIG at import time

Eliminates ~148 hand-written 2-line wrapper methods. Adding a new
scraper is now a single edit to config.py. Custom methods (joyce,
cornyn, etc.) are preserved via hasattr check. member_methods()
now returns sorted config key names (strings) instead of bound
method objects, fixing the health checker full-mode bug.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Fix health checker to work with string-based member_methods()

**Files:**
- Modify: `python_statement/health.py`

**Step 1: Verify health checker works with the new member_methods()**

The health checker `run()` method already uses `Scraper.member_methods()` for full mode and passes names to `check_scraper(name)` which calls `Scraper.run_scraper(name, page=1)`. Since `member_methods()` now returns strings, this should work correctly. Verify:

```bash
uv run python -c "
from python_statement.health import HealthChecker
# check_scraper expects a string name
result = HealthChecker.check_scraper('pelosi')
print(f'pelosi: {result[\"status\"]} ({result[\"count\"]} results)')
"
```

If this works, no changes needed to health.py. If not, fix the issue.

**Step 2: Commit (only if changes were needed)**

---

### Task 4: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `SCRAPER_GUIDE.md`

**Step 1: Update CLAUDE.md**

In the "Adding a New Scraper" section, remove step about creating a wrapper method. Update to say adding a scraper is a single edit to config.py. Remove step about adding to member_methods() list. Mention that custom methods are only needed for sites that can't be expressed in config.

**Step 2: Update SCRAPER_GUIDE.md**

In "Quick Start: Adding a New Site", remove Step 3 (add wrapper method) and Step 4 (register in member_methods). Replace with a note that wrapper methods are auto-generated from config. Update "Step 4: Register and Test" to just be "Step 3: Test".

**Step 3: Update README.md**

In "Adding a New Scraper" and "Contributing" sections, simplify to reflect single-edit workflow.

**Step 4: Commit**

```bash
git add CLAUDE.md README.md SCRAPER_GUIDE.md
git commit -m "$(cat <<'EOF'
Update docs: adding a scraper is now a single config edit

Wrapper methods are auto-generated from SCRAPER_CONFIG.
No need to edit scraper.py or member_methods() for new scrapers.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```
