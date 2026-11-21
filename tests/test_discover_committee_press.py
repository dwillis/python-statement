"""Offline tests for the pure helpers in scripts/discover_committee_press.py."""

import datetime
import unittest

from bs4 import BeautifulSoup

from python_statement.committee_config import validate_committee_config
from scripts.discover_committee_press import (
    build_entry,
    classify_side,
    host_party,
    host_variants,
    nav_candidates,
    pagination_ok,
    pagination_variants,
    side_for_host,
    stale_days,
)


class TestHosts(unittest.TestCase):

    def test_host_party(self):
        self.assertEqual(host_party('democrats-agriculture.house.gov'), 'democrats')
        self.assertEqual(host_party('republicans-oversight.house.gov'), 'republicans')
        self.assertEqual(host_party('gop-waysandmeans.house.gov'), 'republicans')
        self.assertEqual(host_party('oversightdemocrats.house.gov'), 'democrats')
        self.assertIsNone(host_party('agriculture.house.gov'))
        self.assertIsNone(host_party('www.finance.senate.gov'))

    def test_side_for_host(self):
        self.assertEqual(side_for_host('democrats-agriculture.house.gov', 'republicans'), 'minority')
        self.assertEqual(side_for_host('republicans-agriculture.house.gov', 'republicans'), 'majority')
        self.assertEqual(side_for_host('democrats-agriculture.house.gov', 'democrats'), 'majority')
        self.assertIsNone(side_for_host('agriculture.house.gov', 'republicans'))

    def test_house_host_variants_cover_both_parties(self):
        variants = host_variants('https://republicans-agriculture.house.gov/')
        self.assertEqual(variants, [
            'https://agriculture.house.gov',
            'https://democrats-agriculture.house.gov',
            'https://republicans-agriculture.house.gov',
        ])

    def test_gop_prefix_kept_as_variant(self):
        variants = host_variants('https://gop-waysandmeans.house.gov/')
        self.assertIn('https://gop-waysandmeans.house.gov', variants)
        self.assertIn('https://waysandmeans.house.gov', variants)
        self.assertIn('https://democrats-waysandmeans.house.gov', variants)

    def test_non_house_host_is_upgraded_to_https_only(self):
        self.assertEqual(host_variants('http://www.finance.senate.gov/'),
                         ['https://www.finance.senate.gov'])

    def test_subpath_urls_keep_their_path(self):
        url = 'https://cha.house.gov/jointcommittees/joint-committee-library'
        self.assertEqual(host_variants(url), [url])


class TestClassifySide(unittest.TestCase):

    def test_keywords(self):
        self.assertEqual(classify_side('/newsroom/minority-press-releases', 'republicans'), 'minority')
        self.assertEqual(classify_side('Ranking Member News', 'republicans'), 'minority')
        self.assertEqual(classify_side('/news/majority', 'republicans'), 'majority')
        self.assertEqual(classify_side("Chairman's News", 'republicans'), 'majority')
        self.assertIsNone(classify_side('/newsroom/press-releases', 'republicans'))

    def test_party_names_map_through_majority_party(self):
        self.assertEqual(classify_side('/democratic-news', 'republicans'), 'minority')
        self.assertEqual(classify_side('/republicans/press', 'republicans'), 'majority')
        self.assertEqual(classify_side('/democratic-news', 'democrats'), 'majority')


class TestNavCandidates(unittest.TestCase):

    HTML = """
    <nav>
      <a href="/news/press-releases">Press Releases</a>
      <a href="https://www.finance.senate.gov/chairmans-news">Chairman's News</a>
      <a href="/news/in-the-news">In the News</a>
      <a href="/hearings">Hearings</a>
      <a href="https://twitter.com/x/news">News on X</a>
      <a href="/news/press-releases#top">Press Releases again</a>
      <a href="mailto:press@example.gov">Press contact</a>
      <a href="/press/rep/some-single-release">Read More</a>
      <a href="/chairmans-news/crapo-welcomes-new-opportunity-zone-designations">Crapo Welcomes New
         Opportunity Zone Designations in Idaho</a>
    </nav>
    """

    def test_keeps_same_host_listing_links_only(self):
        """Drops other hosts, excluded sections, duplicates, and long headline links."""
        doc = BeautifulSoup(self.HTML, 'lxml')
        found = nav_candidates(doc, 'https://www.finance.senate.gov/')
        self.assertEqual([u for u, _ in found], [
            'https://www.finance.senate.gov/news/press-releases',
            'https://www.finance.senate.gov/chairmans-news',
        ])


class TestPagination(unittest.TestCase):

    def test_variants_for_plain_url(self):
        variants = pagination_variants('https://x.house.gov/news/press-releases')
        self.assertEqual(variants[0], ('?page={page}', -1))
        self.assertIn(('?page={page}', 0), variants)
        self.assertIn(('?PageNum_rs={page}', 0), variants)

    def test_variants_for_url_with_query(self):
        variants = pagination_variants('https://x.house.gov/news/documentquery.aspx?DocumentTypeID=1')
        self.assertTrue(all(p.startswith('&') for p, _ in variants))
        self.assertIn(('&Page={page}', 0), variants)

    def test_pagination_ok_requires_page1_to_be_the_listing(self):
        listing = {'a', 'b', 'c'}
        self.assertTrue(pagination_ok(listing, {'a', 'b', 'c'}, {'d', 'e', 'f'}))
        # Off-by-one Drupal: "page 1" is really the second page.
        self.assertFalse(pagination_ok(listing, {'d', 'e', 'f'}, {'g', 'h', 'i'}))
        # Page 2 repeats page 1: pagination parameter ignored.
        self.assertFalse(pagination_ok(listing, {'a', 'b', 'c'}, {'a', 'b', 'c'}))
        self.assertFalse(pagination_ok(listing, {'a', 'b', 'c'}, set()))


class TestStaleDays(unittest.TestCase):

    def test_stale_only_past_threshold(self):
        today = datetime.date(2026, 11, 21)
        self.assertEqual(stale_days('2024-12-16', today), 705)
        self.assertIsNone(stale_days('2026-11-01', today))
        self.assertIsNone(stale_days(None, today))


class TestBuildEntry(unittest.TestCase):

    PATTERN = {
        'name': 'media_body', 'container': '.media-body', 'title_sel': 'a',
        'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'],
    }

    def test_entry_is_valid_committee_config(self):
        key, entry = build_entry('HSAG', 'minority', 'https://democrats-agriculture.house.gov/news',
                                 self.PATTERN, '?page={page}', -1)
        self.assertEqual(key, 'hsag_minority')
        self.assertEqual(entry['page_offset'], -1)
        self.assertNotIn('name', entry)
        validate_committee_config({key: entry}, member_config={})

    def test_no_pagination_and_zero_offset_omitted(self):
        _, entry = build_entry('SSFI', 'full', 'https://www.finance.senate.gov/news',
                               self.PATTERN, None, 0)
        self.assertEqual(entry['pagination'], '')
        self.assertNotIn('page_offset', entry)


if __name__ == '__main__':
    unittest.main()
