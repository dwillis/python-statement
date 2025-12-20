# Testing Guide for Generic Scrapers

## Test Files

### 1. test_generic_scrapers_standalone.py ✓ **USE THIS NOW**

**Status**: ✅ All 9 tests passing

This is the current working test suite that tests the generic methods in `generic_scrapers.py` before they are integrated into the Scraper class.

**Run with**:
```bash
python test_generic_scrapers_standalone.py
```

**Test Coverage**:
- `TestTableRecordlistDate` - 4 tests
  - Basic HTML parsing
  - Multiple date format handling
  - Missing element handling
  - Network error handling
- `TestJetListingElementor` - 1 test
  - Basic HTML parsing
- `TestArticleBlockH2PDate` - 2 tests
  - Basic HTML parsing
  - Date format normalization
- `TestTableTime` - 1 test
  - Basic HTML parsing with time elements
- `TestElementPostMedia` - 1 test
  - Basic HTML parsing with element structure

### 2. test_generic_scrapers.py (For Future Use)

**Status**: ⏳ Ready for use after integration

This comprehensive test suite (20+ tests) is designed to be used AFTER the generic methods have been integrated into the `Scraper` class in `statement.py`.

**Run with** (after integration):
```bash
python test_generic_scrapers.py
```

or with pytest:
```bash
pytest test_generic_scrapers.py -v
```

**Additional Test Coverage**:
- Absolute and relative URL handling
- Empty table handling
- Alternative HTML selectors
- Time element with datetime attributes
- Multiple URLs in single call
- Pagination validation
- Integration tests

## Current Test Results

```
$ python test_generic_scrapers_standalone.py

test_basic_parsing (__main__.TestArticleBlockH2PDate) ... ok
test_date_format_normalization (__main__.TestArticleBlockH2PDate) ... ok
test_basic_parsing (__main__.TestElementPostMedia) ... ok
test_basic_parsing (__main__.TestJetListingElementor) ... ok
test_basic_parsing (__main__.TestTableRecordlistDate) ... ok
test_missing_elements (__main__.TestTableRecordlistDate) ... ok
test_multiple_date_formats (__main__.TestTableRecordlistDate) ... ok
test_network_error (__main__.TestTableRecordlistDate) ... ok
test_basic_parsing (__main__.TestTableTime) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.014s

OK
```

## Running Tests

### Quick Test
```bash
# Run the standalone tests (current)
python test_generic_scrapers_standalone.py
```

### Verbose Output
```bash
# Run with verbose output
python test_generic_scrapers_standalone.py -v
```

### Run Specific Test Class
```bash
# Run only table_recordlist_date tests
python -m unittest test_generic_scrapers_standalone.TestTableRecordlistDate
```

### Run Specific Test Method
```bash
# Run a single test
python -m unittest test_generic_scrapers_standalone.TestTableRecordlistDate.test_basic_parsing
```

## Test Structure

Each test follows this pattern:

1. **Setup**: Create sample HTML fixture
2. **Mock**: Mock the `open_html` method to return BeautifulSoup object
3. **Execute**: Call the generic method with test URLs
4. **Assert**: Verify expected results (count, titles, dates, URLs)

Example:
```python
@patch.object(GenericScrapers, 'open_html')
def test_basic_parsing(self, mock_open_html):
    """Test basic HTML parsing."""
    mock_open_html.return_value = BeautifulSoup(self.sample_html, 'html.parser')

    results = GenericScrapers.table_recordlist_date(
        urls=["https://example.com/press"],
        page=1
    )

    self.assertEqual(len(results), 3)
    self.assertEqual(results[0]['title'], 'Expected Title')
    self.assertEqual(results[0]['date'], datetime.date(2024, 1, 15))
```

## What the Tests Validate

### Data Structure
Each result must contain:
- `source`: The source URL
- `url`: The press release URL (absolute)
- `title`: The press release title
- `date`: The press release date (datetime.date object or None)
- `domain`: The domain name

### Date Format Handling
Tests validate parsing of multiple date formats:
- `01/15/24` (MM/DD/YY)
- `01/15/2024` (MM/DD/YYYY)
- `01.15.24` (MM.DD.YY with dots)
- `01.15.2024` (MM.DD.YYYY with dots)
- `January 15, 2024` (Full month name)
- `2024-01-15` (ISO format from datetime attributes)

### Error Handling
Tests validate graceful handling of:
- Missing elements (no link, no date)
- Empty tables
- Network errors (returns empty list)
- Malformed HTML

### Edge Cases
- Relative vs absolute URLs
- Alternative CSS selectors
- Multiple URLs in single call
- Pagination parameters

## Adding New Tests

To add a new test:

1. Add a new test method to the appropriate test class
2. Create sample HTML fixture in `setUp()`
3. Mock `open_html` to return your fixture
4. Call the method and assert expected behavior

Example:
```python
@patch.object(GenericScrapers, 'open_html')
def test_my_new_case(self, mock_open_html):
    """Test description."""
    html = """<html>...</html>"""
    mock_open_html.return_value = BeautifulSoup(html, 'html.parser')

    results = GenericScrapers.table_recordlist_date(
        urls=["https://example.com"],
        page=1
    )

    # Add assertions
    self.assertEqual(len(results), expected_count)
```

## Integration Testing

For testing with real websites (requires network):

```python
# integration_test_real.py
from generic_scrapers import GenericScrapers

# Test with real URL (use sparingly to avoid hitting servers)
results = GenericScrapers.table_recordlist_date(
    urls=["https://www.moran.senate.gov/public/index.cfm/news-releases"],
    page=1
)

print(f"Found {len(results)} results")
if results:
    print(f"First result: {results[0]['title']}")
```

⚠️ **Warning**: Integration tests hit real websites. Use sparingly during development.

## Continuous Integration

For CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Test Generic Scrapers

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          python test_generic_scrapers_standalone.py
```

## Next Steps

After the generic methods are integrated into the Scraper class:

1. Switch to using `test_generic_scrapers.py`
2. Run the full test suite (20+ tests)
3. Add integration tests with real websites
4. Set up CI/CD to run tests on every commit

## Troubleshooting

### ImportError: No module named 'bs4'
```bash
pip install beautifulsoup4 lxml python-dateutil requests
```

### Tests fail with "open_html not found"
Make sure you're running `test_generic_scrapers_standalone.py`, not the post-integration test file.

### All tests return 0 results
Check that the mock is properly set up with `@patch.object(GenericScrapers, 'open_html')`
