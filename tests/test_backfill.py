#!/usr/bin/env python3
"""Offline tests for scripts/backfill.py."""

import argparse
import datetime
import unittest
from unittest.mock import patch

from scripts.backfill import backfill_one, select_scrapers

D = datetime.date


def rows(*items):
    """Build result rows from (url_suffix, date) pairs."""
    return [{'url': f'https://x.gov/{u}', 'title': u, 'date': d} for u, d in items]


def fake_pages(pages):
    """side_effect for run_scraper: return pages[page-1], [] past the end."""
    def run(name, page):
        return pages[page - 1] if page <= len(pages) else []
    return run


class TestBackfillOne(unittest.TestCase):

    def _run(self, pages, max_pages=10, since=None):
        with patch('scripts.backfill.Scraper.run_scraper',
                   side_effect=fake_pages(pages)) as run:
            result = backfill_one('s', max_pages, since=since)
        return result, run.call_count

    def test_stops_at_empty_page(self):
        (name, results, error, reason), calls = self._run([
            rows(('a', D(2026, 11, 1)), ('b', D(2026, 10, 1))),
            rows(('c', D(2026, 9, 1))),
        ])
        self.assertEqual([r['title'] for r in results], ['a', 'b', 'c'])
        self.assertIsNone(error)
        self.assertEqual(reason, 'empty')
        self.assertEqual(calls, 3)

    def test_stops_when_page_repeats(self):
        """Non-paginating listings return page 1 for every page number."""
        same = rows(('a', D(2026, 11, 1)), ('b', D(2026, 10, 1)))
        (name, results, error, reason), calls = self._run([same] * 10)
        self.assertEqual(len(results), 2)
        self.assertEqual(reason, 'repeat')
        self.assertEqual(calls, 2)

    def test_stops_at_page_limit(self):
        pages = [rows((f'p{i}', D(2026, 11, 1))) for i in range(10)]
        (name, results, error, reason), calls = self._run(pages, max_pages=3)
        self.assertEqual(len(results), 3)
        self.assertEqual(reason, 'max_pages')
        self.assertEqual(calls, 3)

    def test_since_drops_old_items_and_stops(self):
        (name, results, error, reason), calls = self._run([
            rows(('a', D(2025, 3, 1)), ('b', D(2025, 1, 10))),
            rows(('c', D(2025, 1, 5)), ('d', D(2024, 12, 20))),
            rows(('e', D(2024, 11, 1))),
        ], since=D(2025, 1, 3))
        self.assertEqual([r['title'] for r in results], ['a', 'b', 'c'])
        self.assertEqual(reason, 'since')
        self.assertEqual(calls, 3)  # page 3 is the first entirely before the cutoff

    def test_old_pinned_item_does_not_stop_paging(self):
        (name, results, error, reason), calls = self._run([
            rows(('pinned', D(2023, 5, 1)), ('a', D(2026, 11, 1))),
            rows(('b', D(2026, 6, 1))),
        ], since=D(2025, 1, 3))
        self.assertEqual([r['title'] for r in results], ['a', 'b'])
        self.assertEqual(reason, 'empty')

    def test_since_keeps_undated_items_and_keeps_paging(self):
        (name, results, error, reason), calls = self._run([
            rows(('a', None), ('b', None)),
            rows(('c', D(2024, 1, 1))),
        ], since=D(2025, 1, 3))
        self.assertEqual([r['title'] for r in results], ['a', 'b'])
        self.assertEqual(reason, 'since')
        self.assertEqual(calls, 2)

    def test_error_returns_partial_results(self):
        calls = {'n': 0}

        def run(name, page):
            calls['n'] += 1
            if page == 2:
                raise RuntimeError('boom')
            return rows(('a', D(2026, 1, 1)))

        with patch('scripts.backfill.Scraper.run_scraper', side_effect=run):
            name, results, error, reason = backfill_one('s', 5)
        self.assertEqual(len(results), 1)
        self.assertEqual(error, 'boom')
        self.assertEqual(reason, 'error')


def ns(**kw):
    defaults = dict(scraper=None, method=None, all=False, committee=None, collection='members')
    defaults.update(kw)
    return argparse.Namespace(**defaults)


class TestSelectScrapers(unittest.TestCase):

    MEMBERS = {
        'aaa': {'method': 'media_body', 'url_base': 'x'},
        'bbb': {'method': 'generic', 'url_base': 'x'},
    }
    COMMITTEES = {
        'hsag_majority': {'thomas_id': 'HSAG', 'side': 'majority', 'method': 'generic', 'url_base': 'x'},
        'hsag_minority': {'thomas_id': 'HSAG', 'side': 'minority', 'method': 'generic', 'url_base': 'x'},
        'ssfi_full': {'thomas_id': 'SSFI', 'side': 'full', 'method': 'rss', 'url_base': 'x'},
    }

    def setUp(self):
        p1 = patch('scripts.backfill.SCRAPER_CONFIG', self.MEMBERS)
        p2 = patch('scripts.backfill.COMMITTEE_CONFIG', self.COMMITTEES)
        p1.start(), p2.start()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)

    def test_all_members_by_default(self):
        self.assertEqual(select_scrapers(ns(all=True)), ['aaa', 'bbb'])

    def test_all_committees(self):
        self.assertEqual(select_scrapers(ns(all=True, collection='committees')),
                         ['hsag_majority', 'hsag_minority', 'ssfi_full'])

    def test_method_respects_collection(self):
        self.assertEqual(select_scrapers(ns(method='generic')), ['bbb'])
        self.assertEqual(select_scrapers(ns(method='generic', collection='committees')),
                         ['hsag_majority', 'hsag_minority'])

    def test_committee_selects_every_side(self):
        self.assertEqual(select_scrapers(ns(committee='hsag')),
                         ['hsag_majority', 'hsag_minority'])

    def test_single_scraper_passes_through(self):
        self.assertEqual(select_scrapers(ns(scraper='ssfi_full')), ['ssfi_full'])


if __name__ == '__main__':
    unittest.main()
