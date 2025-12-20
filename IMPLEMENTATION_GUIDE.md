# Generic Scraper Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing the generic scraper consolidation identified in the CONSOLIDATION_PLAN.md document.

## Files Created

1. **CONSOLIDATION_PLAN.md** - Comprehensive analysis of consolidation opportunities
2. **generic_scrapers.py** - Python implementations of 5 new generic methods
3. **test_generic_scrapers.py** - Comprehensive test suite for the generic methods
4. **IMPLEMENTATION_GUIDE.md** - This file

## Quick Start

### Step 1: Add Generic Methods to Scraper Class

Copy the methods from `generic_scrapers.py` into the `Scraper` class in `statement.py`:

```python
# In statement.py, add these methods to the Scraper class:

@classmethod
def table_recordlist_date(cls, urls=None, page=1):
    # Copy implementation from generic_scrapers.py
    pass

@classmethod
def jet_listing_elementor(cls, urls=None, page=1):
    # Copy implementation from generic_scrapers.py
    pass

@classmethod
def article_block_h2_p_date(cls, urls=None, page=1):
    # Copy implementation from generic_scrapers.py
    pass

@classmethod
def table_time(cls, urls=None, page=1):
    # Copy implementation from generic_scrapers.py
    pass

@classmethod
def element_post_media(cls, urls=None, page=1):
    # Copy implementation from generic_scrapers.py
    pass
```

### Step 2: Run Tests

Before making any changes to existing methods, run the test suite:

```bash
cd /home/user/python-statement
python -m pytest test_generic_scrapers.py -v
```

Or with unittest:

```bash
python test_generic_scrapers.py
```

### Step 3: Migrate Member Methods (Gradual Approach)

Start with a small batch (5-10 methods) as proof of concept:

#### Example: Migrate `moran()` method

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

### Step 4: Validate Migrated Methods

After migrating each method, run integration tests:

```python
# Test the migrated method
from python_statement.statement import Scraper

# Test moran() method
results = Scraper.moran(page=1)
print(f"Found {len(results)} press releases")
print(f"First result: {results[0] if results else 'None'}")

# Verify structure
if results:
    assert 'source' in results[0]
    assert 'url' in results[0]
    assert 'title' in results[0]
    assert 'date' in results[0]
    assert 'domain' in results[0]
    print("✓ Structure validated")
```

## Migration Batches

### Batch 1: table_recordlist_date() - 10 methods

Priority: HIGH (identical pattern, easy wins)

Methods to migrate:
1. `moran()` - https://www.moran.senate.gov/public/index.cfm/news-releases
2. `boozman()` - https://www.boozman.senate.gov/public/index.cfm/press-releases
3. `thune()` - https://www.thune.senate.gov/public/index.cfm/press-releases
4. `barrasso()` - https://www.barrasso.senate.gov/public/index.cfm/news-releases
5. `graham()` - https://www.lgraham.senate.gov/public/index.cfm/press-releases

Example migration:
```python
@classmethod
def boozman(cls, page=1):
    """Scrape Senator Boozman's press releases."""
    return cls.table_recordlist_date(
        urls=["https://www.boozman.senate.gov/public/index.cfm/press-releases"],
        page=page
    )
```

### Batch 2: jet_listing_elementor() - 15 methods

Priority: HIGH (identical pattern, many methods affected)

Methods to migrate:
1. `timscott()` - https://www.scott.senate.gov/media-center/press-releases
2. `fetterman()` - https://www.fetterman.senate.gov/press-releases
3. `tester()` - https://www.tester.senate.gov/newsroom/press-releases
4. `hawley()` - Similar pattern
5. `marshall()` - Similar pattern

Example migration:
```python
@classmethod
def timscott(cls, page=1):
    """Scrape Senator Tim Scott's press releases."""
    return cls.jet_listing_elementor(
        urls=["https://www.scott.senate.gov/media-center/press-releases/jsf/jet-engine:press-list/pagenum/"],
        page=page
    )
```

### Batch 3: article_block_h2_p_date() - 40+ methods

Priority: MEDIUM (many methods but need to verify date format compatibility)

Methods to migrate:
1. `crapo()` - https://www.crapo.senate.gov/media/newsreleases
2. `sherrod_brown()` - https://www.brown.senate.gov/newsroom/press
3. `durbin()` - https://www.durbin.senate.gov/newsroom/press-releases
4. `bennet()` - Similar pattern
5. `cardin()` - Similar pattern

Example migration:
```python
@classmethod
def durbin(cls, page=1):
    """Scrape Senator Durbin's press releases."""
    return cls.article_block_h2_p_date(
        urls=["https://www.durbin.senate.gov/newsroom/press-releases"],
        page=page
    )
```

### Batch 4: table_time() - 5+ methods

Priority: LOW (fewer methods affected)

Methods to migrate:
1. `barr()` - https://barr.house.gov/media-center/press-releases

Example migration:
```python
@classmethod
def barr(cls, page=1):
    """Scrape Congressman Barr's press releases."""
    return cls.table_time(
        urls=["https://barr.house.gov/media-center/press-releases"],
        page=page
    )
```

### Batch 5: element_post_media() - 3 methods

Priority: LOW (few methods affected)

Methods to migrate:
1. `wicker()` - https://www.wicker.senate.gov/media/press-releases

Example migration:
```python
@classmethod
def wicker(cls, page=1):
    """Scrape Senator Wicker's press releases."""
    return cls.element_post_media(
        urls=["https://www.wicker.senate.gov/media/press-releases"],
        page=page
    )
```

## Testing Strategy

### Unit Tests

Run the comprehensive unit tests:

```bash
python test_generic_scrapers.py
```

Expected output:
```
test_basic_parsing (test_generic_scrapers.TestTableRecordlistDate) ... ok
test_multiple_date_formats (test_generic_scrapers.TestTableRecordlistDate) ... ok
test_missing_elements (test_generic_scrapers.TestTableRecordlistDate) ... ok
...

----------------------------------------------------------------------
Ran 20 tests in 0.123s

OK
```

### Integration Tests

Test actual scraping (requires network access):

```python
#!/usr/bin/env python3
"""Integration test for migrated methods."""

from python_statement.statement import Scraper

def test_migrated_methods():
    """Test that migrated methods still work correctly."""

    # Test table_recordlist_date methods
    print("Testing moran()...")
    results = Scraper.moran(page=1)
    assert len(results) > 0, "moran() returned no results"
    assert results[0]['domain'] == 'www.moran.senate.gov'
    print(f"✓ moran() returned {len(results)} results")

    print("\nTesting boozman()...")
    results = Scraper.boozman(page=1)
    assert len(results) > 0, "boozman() returned no results"
    print(f"✓ boozman() returned {len(results)} results")

    # Test jet_listing_elementor methods
    print("\nTesting timscott()...")
    results = Scraper.timscott(page=1)
    assert len(results) > 0, "timscott() returned no results"
    print(f"✓ timscott() returned {len(results)} results")

    # Test article_block_h2_p_date methods
    print("\nTesting durbin()...")
    results = Scraper.durbin(page=1)
    assert len(results) > 0, "durbin() returned no results"
    print(f"✓ durbin() returned {len(results)} results")

    print("\n✓ All integration tests passed!")

if __name__ == '__main__':
    test_migrated_methods()
```

Run with:
```bash
python integration_test.py
```

## Rollback Plan

If a migrated method doesn't work correctly:

1. **Keep the old implementation commented out** during migration:

```python
@classmethod
def moran(cls, page=1):
    """Scrape Senator Moran's press releases."""
    return cls.table_recordlist_date(
        urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
        page=page
    )

# OLD IMPLEMENTATION (keep for 1-2 release cycles)
# @classmethod
# def moran_old(cls, page=1):
#     """Scrape Senator Moran's press releases (OLD)."""
#     results = []
#     ... original implementation ...
#     return results
```

2. **Create a fallback mechanism** in production:

```python
@classmethod
def moran(cls, page=1):
    """Scrape Senator Moran's press releases."""
    try:
        results = cls.table_recordlist_date(
            urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
            page=page
        )
        if not results:
            # Fallback to old implementation if new one returns empty
            return cls.moran_old(page)
        return results
    except Exception as e:
        print(f"Error in new moran() implementation: {e}")
        return cls.moran_old(page)
```

## Benefits Checklist

After completing migration, verify these benefits:

- [ ] Code reduction: ~80% less code
- [ ] Single source of truth: Bug fixes benefit all methods
- [ ] Improved test coverage: Test generic methods once
- [ ] Better date handling: Multiple formats supported automatically
- [ ] Easier maintenance: Add new members with 4 lines instead of 30+
- [ ] Better error handling: Centralized logic
- [ ] Consistent behavior: All methods use same patterns

## Performance Considerations

The generic methods should have equivalent or better performance:

1. **No additional HTTP requests** - Same number of requests as before
2. **Minimal overhead** - Just function call overhead (~microseconds)
3. **Better caching** - Centralized logic allows for future caching improvements
4. **Reduced memory** - Less code means less memory usage

## Future Enhancements

After successful migration, consider these enhancements:

1. **Add caching** - Cache results to reduce redundant requests
2. **Add retry logic** - Automatic retries on network failures
3. **Add rate limiting** - Prevent overwhelming websites
4. **Add logging** - Better debugging and monitoring
5. **Add validation** - Validate results before returning
6. **Add metrics** - Track success/failure rates

## Conclusion

This consolidation effort will significantly improve the codebase maintainability while preserving all existing functionality. Follow the batched approach to minimize risk and validate each step before proceeding.

For questions or issues, refer to:
- CONSOLIDATION_PLAN.md - Detailed analysis
- generic_scrapers.py - Method implementations
- test_generic_scrapers.py - Test suite
