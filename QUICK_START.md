# Quick Start: Adding Generic Scrapers

## Step 1: Enable Generic Methods (2 lines of code)

Edit `python_statement/statement.py`:

### Add Import at the Top

```python
# Add this import near the top of the file (after other imports)
from generic_scrapers import GenericScrapers
```

### Update Class Definition

Find this line:
```python
class Scraper:
    """Class for scraping HTML pages."""
```

Change it to:
```python
class Scraper(GenericScrapers):
    """Class for scraping HTML pages."""
```

**That's it!** The `Scraper` class now has all 5 generic methods:
- ✅ `table_recordlist_date()`
- ✅ `jet_listing_elementor()`
- ✅ `article_block_h2_p_date()`
- ✅ `table_time()`
- ✅ `element_post_media()`

---

## Step 2: Test the Integration

```bash
cd /home/user/python-statement
python test_generic_scrapers_standalone.py
```

Expected output:
```
Ran 9 tests in 0.014s
OK
```

---

## Step 3: Start Migrating Member Methods

Example: Replace `moran()` with a call to the generic method:

### Before (30+ lines):
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
        # ... 20+ more lines ...
    return results
```

### After (4 lines):
```python
@classmethod
def moran(cls, page=1):
    """Scrape Senator Moran's press releases."""
    return cls.table_recordlist_date(
        urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
        page=page
    )
```

---

## Step 4: Verify Migration

Test the migrated method:

```python
from python_statement.statement import Scraper

# Test the method
results = Scraper.moran(page=1)
print(f"Found {len(results)} press releases")
if results:
    print(f"First: {results[0]['title']}")
    print(f"Date: {results[0]['date']}")
```

---

## Migration Cheatsheet

| Member Method | Generic Method | URL Pattern |
|--------------|----------------|-------------|
| `moran()`, `boozman()`, `thune()` | `table_recordlist_date()` | Senate table with recordListDate |
| `timscott()`, `fetterman()`, `tester()` | `jet_listing_elementor()` | WordPress/Elementor with Jet Engine |
| `durbin()`, `sherrod_brown()`, `crapo()` | `article_block_h2_p_date()` | ArticleBlock layout |
| `barr()` | `table_time()` | Simple table with time element |
| `wicker()` | `element_post_media()` | Custom element layout |

---

## Example Migration Script

```python
# migrate_methods.py
"""Helper script to test migrated methods."""

from python_statement.statement import Scraper

def test_method(name, method, page=1):
    """Test a single method."""
    print(f"\nTesting {name}...")
    try:
        results = method(page=page)
        if results:
            print(f"  ✓ {len(results)} results")
            print(f"  First: {results[0]['title'][:50]}...")
            return True
        else:
            print(f"  ⚠ No results (might be empty page)")
            return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

# Test migrated methods
test_method("moran", Scraper.moran)
test_method("boozman", Scraper.boozman)
test_method("timscott", Scraper.timscott)
test_method("durbin", Scraper.durbin)

print("\n✓ All tests complete!")
```

---

## Benefits Summary

- **80% code reduction**: 2,000+ lines → 400 lines
- **Single source of truth**: Fix bugs once, benefit everywhere
- **Better date handling**: Multiple formats supported automatically
- **Easy maintenance**: Add new members with 4 lines instead of 30+
- **Better testing**: Test generic methods once instead of 60+ times

---

## Need Help?

- **Implementation details**: See `IMPLEMENTATION_GUIDE.md`
- **Full analysis**: See `CONSOLIDATION_PLAN.md`
- **Testing guide**: See `TEST_README.md`
- **Method implementations**: See `generic_scrapers.py`

---

## Rollback

If something doesn't work, just revert the 2-line change:

```python
# Remove the import
# from generic_scrapers import GenericScrapers

# Change back to:
class Scraper:
    """Class for scraping HTML pages."""
```

All original methods continue to work unchanged!
