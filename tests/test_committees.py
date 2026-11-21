"""
Offline tests for the committee collection (COMMITTEE_CONFIG).
"""

import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from python_statement import Scraper
from python_statement import config as member_config_module
from python_statement import committee_config
from python_statement.committee_config import (
    COMMITTEE_CONFIG,
    COMMITTEE_SKIP,
    validate_committee_config,
)


GENERIC_ENTRY = {
    'thomas_id': 'HSAG',
    'side': 'majority',
    'method': 'generic',
    'url_base': 'https://agriculture.house.gov/news',
    'container': '.views-row',
    'title_sel': '.h3 a',
    'date_sel': '.col-auto',
    'date_fmt': ['%B %d, %Y'],
}

LISTING_HTML = """
<html><body>
  <div class="views-row">
    <div class="h3"><a href="/news/release-0">Release Zero</a></div>
    <div class="col-auto">March 3, 2026</div>
  </div>
  <div class="views-row">
    <div class="h3"><a href="/news/release-1">Release One</a></div>
    <div class="col-auto">March 2, 2026</div>
  </div>
</body></html>
"""


class TestValidateCommitteeConfig(unittest.TestCase):

    def test_valid_generic_entry_passes(self):
        validate_committee_config({'hsag_majority': dict(GENERIC_ENTRY)}, member_config={})

    def test_valid_batch_entry_passes(self):
        validate_committee_config({
            'ssfi_minority': {
                'thomas_id': 'SSFI', 'side': 'minority',
                'method': 'rss', 'url_base': 'https://www.finance.senate.gov/rss/feed/ranking/',
            }
        }, member_config={})

    def test_full_side_allowed(self):
        entry = dict(GENERIC_ENTRY, side='full')
        validate_committee_config({'hsag_full': entry}, member_config={})

    def test_missing_thomas_id_rejected(self):
        entry = dict(GENERIC_ENTRY)
        del entry['thomas_id']
        with self.assertRaisesRegex(ValueError, 'thomas_id'):
            validate_committee_config({'hsag_majority': entry}, member_config={})

    def test_missing_side_rejected(self):
        entry = dict(GENERIC_ENTRY)
        del entry['side']
        with self.assertRaisesRegex(ValueError, 'side'):
            validate_committee_config({'hsag_majority': entry}, member_config={})

    def test_bad_side_rejected(self):
        entry = dict(GENERIC_ENTRY, side='republican')
        with self.assertRaisesRegex(ValueError, 'side'):
            validate_committee_config({'hsag_republican': entry}, member_config={})

    def test_bad_thomas_id_rejected(self):
        entry = dict(GENERIC_ENTRY, thomas_id='hsag')
        with self.assertRaisesRegex(ValueError, 'thomas_id'):
            validate_committee_config({'hsag_majority': entry}, member_config={})

    def test_key_must_match_thomas_id_and_side(self):
        with self.assertRaisesRegex(ValueError, 'hsag_majority'):
            validate_committee_config({'agriculture': dict(GENERIC_ENTRY)}, member_config={})

    def test_collision_with_member_name_rejected(self):
        with self.assertRaisesRegex(ValueError, 'member'):
            validate_committee_config(
                {'hsag_majority': dict(GENERIC_ENTRY)},
                member_config={'hsag_majority': {'method': 'media_body', 'url_base': 'x'}},
            )

    def test_unknown_generic_key_still_rejected(self):
        entry = dict(GENERIC_ENTRY, contianer='.typo')
        with self.assertRaisesRegex(ValueError, 'unknown config keys'):
            validate_committee_config({'hsag_majority': entry}, member_config={})

    def test_extra_key_on_batch_entry_rejected(self):
        with self.assertRaisesRegex(ValueError, 'extra keys'):
            validate_committee_config({
                'ssfi_minority': {
                    'thomas_id': 'SSFI', 'side': 'minority', 'method': 'rss',
                    'url_base': 'https://example.senate.gov/rss', 'container': 'x',
                }
            }, member_config={})

    def test_committee_keys_not_allowed_in_member_config(self):
        """thomas_id/side are committee-only; member validation must still reject them."""
        with self.assertRaises(ValueError):
            member_config_module.validate_config({'somebody': dict(GENERIC_ENTRY)})

    def test_shipped_config_is_valid(self):
        validate_committee_config(COMMITTEE_CONFIG)

    def test_skip_list_does_not_overlap_config(self):
        configured = {c['thomas_id'] for c in COMMITTEE_CONFIG.values()}
        self.assertFalse(configured & set(COMMITTEE_SKIP))


class TestCommitteeScraping(unittest.TestCase):

    @patch('python_statement.scraper.Scraper.open_html')
    def test_run_scraper_tags_committee_results(self, mock_open_html):
        mock_open_html.return_value = BeautifulSoup(LISTING_HTML, 'lxml')
        with patch.dict(committee_config.COMMITTEE_CONFIG, {'hsag_majority': dict(GENERIC_ENTRY)}):
            results = Scraper.run_scraper('hsag_majority', 1)

        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r['committee'], 'HSAG')
            self.assertEqual(r['side'], 'majority')
        self.assertEqual(results[0]['url'], 'https://agriculture.house.gov/news/release-0')
        self.assertEqual(str(results[0]['date']), '2026-03-03')

    @patch('python_statement.scraper.Scraper.open_html')
    def test_member_results_are_not_tagged(self, mock_open_html):
        mock_open_html.return_value = BeautifulSoup(LISTING_HTML, 'lxml')
        member_entry = {k: v for k, v in GENERIC_ENTRY.items() if k not in ('thomas_id', 'side')}
        with patch.dict(member_config_module.SCRAPER_CONFIG, {'membertest': member_entry}):
            results = Scraper.run_scraper('membertest', 1)

        self.assertEqual(len(results), 2)
        for r in results:
            self.assertNotIn('committee', r)
            self.assertNotIn('side', r)

    def test_committee_methods_lists_only_committee_keys(self):
        with patch.dict(committee_config.COMMITTEE_CONFIG, {'hsag_majority': dict(GENERIC_ENTRY)}):
            names = Scraper.committee_methods()
        self.assertIn('hsag_majority', names)
        self.assertEqual(names, sorted(names))
        self.assertFalse(set(names) & set(Scraper.member_methods()))

    def test_member_methods_excludes_committees(self):
        with patch.dict(committee_config.COMMITTEE_CONFIG, {'hsag_majority': dict(GENERIC_ENTRY)}):
            self.assertNotIn('hsag_majority', Scraper.member_methods())

    def test_committee_scrapers_aggregates_all(self):
        fake = {
            'hsag_majority': [{'url': 'https://a.gov/1', 'title': 'A'}],
            'hsag_minority': [{'url': 'https://b.gov/1', 'title': 'B'}],
        }
        entries = {
            'hsag_majority': dict(GENERIC_ENTRY),
            'hsag_minority': dict(GENERIC_ENTRY, side='minority'),
        }
        with patch.dict(committee_config.COMMITTEE_CONFIG, entries, clear=True), \
             patch.object(Scraper, 'run_scraper', side_effect=lambda n, page=1: fake[n]):
            results = Scraper.committee_scrapers()
        self.assertEqual({r['title'] for r in results}, {'A', 'B'})

    def test_every_committee_entry_has_wrapper(self):
        for name in COMMITTEE_CONFIG:
            self.assertTrue(callable(getattr(Scraper, name, None)), name)


if __name__ == '__main__':
    unittest.main()
