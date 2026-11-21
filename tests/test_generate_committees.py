"""Offline tests for scripts/generate_committees.py."""

import unittest

from scripts.generate_committees import match_committees


COMMITTEES = [
    {
        'type': 'house', 'name': 'House Committee on Agriculture', 'thomas_id': 'HSAG',
        'url': 'https://agriculture.house.gov/',
        'minority_url': 'https://democrats-agriculture.house.gov',
        'subcommittees': [{'name': 'Livestock', 'thomas_id': '29'}],
        'jurisdiction': 'long text that should not be copied',
    },
    {
        'type': 'senate', 'name': 'Senate Committee on Finance', 'thomas_id': 'SSFI',
        'url': 'http://www.finance.senate.gov/',
        'rss_url': 'http://www.finance.senate.gov/rss/feed/chair/',
    },
    {
        'type': 'joint', 'name': 'Joint Committee on Printing', 'thomas_id': 'JSPR',
        'url': 'https://cha.house.gov/jointcommittees/joint-committee-on-printing',
    },
    {
        'type': 'house', 'name': 'House Committee on Rules', 'thomas_id': 'HSRU',
        'url': 'https://rules.house.gov/',
        'minority_url': 'https://democrats-rules.house.gov/',
    },
]

CONFIG = {
    'hsag_majority': {'thomas_id': 'HSAG', 'side': 'majority', 'method': 'rss',
                      'url_base': 'https://agriculture.house.gov/rss'},
    'ssfi_full': {'thomas_id': 'SSFI', 'side': 'full', 'method': 'rss',
                  'url_base': 'https://www.finance.senate.gov/rss'},
    'hsxx_majority': {'thomas_id': 'HSXX', 'side': 'majority', 'method': 'rss',
                      'url_base': 'https://gone.house.gov/rss'},
    'hsru_majority': {'thomas_id': 'HSRU', 'side': 'majority', 'method': 'rss',
                      'url_base': 'https://rules.house.gov/rss'},
    'hsru_minority': {'thomas_id': 'HSRU', 'side': 'minority', 'method': 'rss',
                      'url_base': 'https://democrats-rules.house.gov/rss'},
}

SKIP = {'JSPR': 'no press releases', 'JOLD': 'dissolved'}


class TestMatchCommittees(unittest.TestCase):

    def setUp(self):
        self.result = match_committees(COMMITTEES, CONFIG, SKIP)
        self.with_by_id = {c['thomas_id']: c for c in self.result['with_scrapers']}

    def test_configured_committees_listed_with_their_scrapers(self):
        self.assertEqual(set(self.with_by_id), {'HSAG', 'SSFI', 'HSRU'})
        self.assertEqual(
            self.with_by_id['HSAG']['scrapers'],
            [{'scraper_method': 'hsag_majority', 'side': 'majority',
              'url_base': 'https://agriculture.house.gov/rss'}],
        )
        self.assertEqual(
            [s['side'] for s in self.with_by_id['HSRU']['scrapers']], ['majority', 'minority'],
        )

    def test_record_keeps_identity_fields_only(self):
        rec = self.with_by_id['HSAG']
        self.assertEqual(rec['name'], 'House Committee on Agriculture')
        self.assertEqual(rec['type'], 'house')
        self.assertEqual(rec['minority_url'], 'https://democrats-agriculture.house.gov')
        self.assertNotIn('subcommittees', rec)
        self.assertNotIn('jurisdiction', rec)

    def test_missing_minority_flagged_only_when_yaml_has_minority_url(self):
        self.assertTrue(self.with_by_id['HSAG']['needs_minority'])
        self.assertFalse(self.with_by_id['HSRU']['needs_minority'])
        # Senate entry has no minority_url, and 'full' covers both sides anyway.
        self.assertFalse(self.with_by_id['SSFI']['needs_minority'])

    def test_skipped_committees_are_not_reported_as_missing(self):
        self.assertEqual(self.result['without_scrapers'], [])
        self.assertEqual(
            self.result['skipped'], [{'thomas_id': 'JSPR', 'name': 'Joint Committee on Printing',
                                      'reason': 'no press releases'}],
        )

    def test_unconfigured_committee_reported_missing(self):
        result = match_committees(COMMITTEES, {}, {})
        self.assertEqual(
            [c['thomas_id'] for c in result['without_scrapers']], ['HSAG', 'SSFI', 'JSPR', 'HSRU'],
        )
        self.assertNotIn('scrapers', result['without_scrapers'][0])

    def test_orphans_are_config_and_skip_ids_not_in_yaml(self):
        self.assertEqual(
            self.result['orphans'],
            [{'thomas_id': 'HSXX', 'source': 'COMMITTEE_CONFIG', 'names': ['hsxx_majority']},
             {'thomas_id': 'JOLD', 'source': 'COMMITTEE_SKIP', 'names': []}],
        )


if __name__ == '__main__':
    unittest.main()
