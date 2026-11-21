#!/usr/bin/env python3
"""
Discover press release pages for congressional committees and draft
COMMITTEE_CONFIG entries.

For each committee in committees-current.yaml (skipping ones already in
COMMITTEE_CONFIG or COMMITTEE_SKIP unless --all):

1. Resolve live hosts. The YAML's minority_url values are often stale (they
   still point at republicans-* hosts), so for House committees every party
   variant of the host is tried (bare, democrats-, republicans-, gop-) and
   redirects are followed. The side comes from the final host's party prefix
   and the current majority party, not from the YAML field name.
2. Collect candidate press pages from each site's own navigation links plus a
   few standard paths. On single-host sites (Senate, joint) the side comes
   from link keywords (majority/chair vs minority/ranking), else 'full'.
3. Score each candidate with the detection patterns from detect_pattern.py.
4. Verify the best candidates through the real scraper (Scraper.run_scraper)
   and pick a pagination variant whose page 1 is the unpaginated listing and
   whose page 2 is different (this catches 0-indexed Drupal sites that need
   page_offset -1).
5. Check any rss_url / minority_rss_url in the YAML.

Writes a JSON report and prints paste-ready config entries.

Usage:
    uv run python scripts/discover_committee_press.py
    uv run python scripts/discover_committee_press.py --only HSAG,SSFI
    uv run python scripts/discover_committee_press.py --workers 6 --cache
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_statement.scraper import Scraper
from python_statement.utils import Utils
from python_statement.committee_config import COMMITTEE_CONFIG, COMMITTEE_SKIP
from scripts.detect_pattern import PATTERNS, try_pattern
from scripts.generate_committees import fetch_committees


USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
)

PARTY_PREFIXES = {'democrats': 'democrats', 'republicans': 'republicans', 'gop': 'republicans'}
PREFIX_RE = re.compile(r'^(democrats|republicans|gop)-(.+)$')

PRESS_RE = re.compile(r'press|news|release|statement', re.I)
EXCLUDE_RE = re.compile(
    r'in-the-news|in the news|inthenews|clip|video|photo|podcast|newsletter|'
    r'subscribe|mailto:|tel:|javascript:|\.pdf$|read more|continue reading|learn more',
    re.I,
)

HOUSE_PATHS = [
    '/news/documentquery.aspx?DocumentTypeID=1',
    '/news/press-releases',
    '/media/press-releases',
    '/press-releases',
]
SINGLE_HOST_PATHS = [
    '/newsroom/press-releases',
    '/news/press-releases',
    '/newsroom/majority-news',
    '/newsroom/minority-news',
    '/press-releases',
]

MAX_CANDIDATES_PER_HOST = 12
MAX_NAV_WORDS = 6  # longer link text is a release headline, not a listing link
MIN_ITEMS = 3
STALE_DAYS = 90  # newest item older than this suggests an archive page


# ---------------------------------------------------------------------------
# Pure helpers (unit tested)
# ---------------------------------------------------------------------------

def host_party(host):
    """Return 'democrats' / 'republicans' for a party-labelled host, else None.

    Handles prefixes (democrats-oversight.house.gov, gop-waysandmeans...) and
    suffixes run together with the committee name (oversightdemocrats.house.gov).
    """
    label = host.lower().split('.')[0]
    m = PREFIX_RE.match(label)
    if m:
        return PARTY_PREFIXES[m.group(1)]
    for word, party in (('democrats', 'democrats'), ('republicans', 'republicans')):
        if label.endswith(word):
            return party
    return None


def side_for_host(host, majority_party):
    """Map a party-prefixed host to 'majority' / 'minority'; None if unprefixed."""
    party = host_party(host)
    if party is None:
        return None
    return 'majority' if party == majority_party else 'minority'


def host_variants(url):
    """Base URLs to try for a committee URL from the YAML.

    House root URLs expand to every party variant of the host. Everything is
    upgraded to https. URLs with a path (e.g. cha.house.gov sub-pages) are
    returned as-is.
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    if path:
        return [f"https://{host}{path}"]
    if not host.endswith('.house.gov'):
        return [f"https://{host}"]

    label, _, rest = host.partition('.')
    m = PREFIX_RE.match(label)
    core = m.group(2) if m else label
    variants = [f"https://{core}.{rest}",
                f"https://democrats-{core}.{rest}",
                f"https://republicans-{core}.{rest}"]
    original = f"https://{host}"
    if original not in variants:
        variants.append(original)
    return variants


def classify_side(text, majority_party):
    """Guess a side from a URL / link text on a single-host site, else None."""
    t = text.lower()
    if 'minority' in t or 'ranking' in t:
        return 'minority'
    if 'majority' in t or 'chair' in t:
        return 'majority'
    for word, party in (('democrat', 'democrats'), ('republican', 'republicans')):
        if word in t:
            return 'majority' if party == majority_party else 'minority'
    return None


def _norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith('www.') else host


def nav_candidates(doc, base_url):
    """Same-host links that look like press/news listings, in page order."""
    base_host = _norm_host(urlparse(base_url).netloc)
    seen = {urldefrag(base_url)[0].rstrip('/')}
    found = []
    for a in doc.select('a[href]'):
        href = a.get('href', '').strip()
        text = ' '.join(a.get_text().split())
        if not href or EXCLUDE_RE.search(href) or EXCLUDE_RE.search(text):
            continue
        if len(text.split()) > MAX_NAV_WORDS:
            continue
        if not (PRESS_RE.search(href) or PRESS_RE.search(text)):
            continue
        url = urldefrag(urljoin(base_url, href))[0]
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or _norm_host(parsed.netloc) != base_host:
            continue
        key = url.rstrip('/')
        if key in seen:
            continue
        seen.add(key)
        found.append((url, text))
    return found


def pagination_variants(url):
    """(pagination, page_offset) pairs to try, most likely first."""
    if '?' in url:
        return [('&page={page}', -1), ('&page={page}', 0),
                ('&Page={page}', 0), ('&PageNum_rs={page}', 0)]
    slash = '' if url.endswith('/') else '/'
    return [('?page={page}', -1), ('?page={page}', 0),
            ('?PageNum_rs={page}', 0), (slash + 'page/{page}/', 0)]


def pagination_ok(listing_urls, page1_urls, page2_urls):
    """True when page 1 is the unpaginated listing and page 2 is new items."""
    if not page1_urls or not page2_urls:
        return False
    if len(page1_urls & listing_urls) * 2 < len(page1_urls):
        return False
    return len(page2_urls & page1_urls) * 2 < len(page2_urls)


def stale_days(latest, today=None):
    """Days since an ISO date if older than STALE_DAYS, else None."""
    if not latest:
        return None
    today = today or datetime.date.today()
    age = (today - datetime.date.fromisoformat(latest)).days
    return age if age > STALE_DAYS else None


def build_entry(thomas_id, side, url, pattern, pagination, page_offset):
    """Build a (key, COMMITTEE_CONFIG entry) pair from a detection pattern."""
    entry = {'thomas_id': thomas_id, 'side': side, 'method': 'generic', 'url_base': url}
    for k in ('container', 'title_sel', 'date_sel', 'date_attr', 'date_fmt',
              'date_from_next_sibling', 'skip_first'):
        if k in pattern:
            entry[k] = pattern[k]
    entry['pagination'] = pagination or ''
    if page_offset:
        entry['page_offset'] = page_offset
    return f"{thomas_id.lower()}_{side}", entry


# ---------------------------------------------------------------------------
# Network steps
# ---------------------------------------------------------------------------

def _error_label(e):
    """Short error label; HTTP errors include the status code."""
    response = getattr(e, 'response', None)
    if response is not None:
        return f"HTTP {response.status_code}"
    return type(e).__name__


def fetch_with_redirects(url):
    """GET a URL following redirects. Returns (final_url, soup) or (None, error)."""
    time.sleep(0.5)
    try:
        r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        return None, _error_label(e)
    return r.url, BeautifulSoup(r.content, 'lxml')


def score_candidate(url, text):
    """Fetch a candidate page and find its best detection pattern."""
    doc = Scraper.open_html(url)
    if doc is None:
        return None
    if doc.select_one('#__NEXT_DATA__'):
        return {'pattern': None, 'react': True, 'score': 0}
    unmatched = {'pattern': None, 'react': False, 'score': 0}
    domain = urlparse(url).netloc
    best, best_pattern = None, None
    for pattern in PATTERNS:
        result = try_pattern(doc, pattern, url, domain)
        if result and (best is None or
                       result['with_dates'] * 10 + result['matches'] >
                       best['with_dates'] * 10 + best['matches']):
            best, best_pattern = result, pattern
    if not best or best['matches'] < MIN_ITEMS:
        return unmatched
    score =best['with_dates'] * 10 + min(best['matches'], 20)
    if 'press' in (url + ' ' + text).lower():
        score += 3
    return {'pattern': best_pattern, 'react': False, 'score': score,
            'matches': best['matches'], 'with_dates': best['with_dates']}


def _run_temp(key, entry, page):
    Scraper.COMMITTEE_CONFIG[key] = entry
    try:
        return Scraper.run_scraper(key, page) or []
    finally:
        Scraper.COMMITTEE_CONFIG.pop(key, None)


def verify_candidate(thomas_id, side, url, pattern):
    """Run a candidate through the real scraper; pick working pagination."""
    tmp = f"__discover_{thomas_id.lower()}_{side}"
    _, base = build_entry(thomas_id, side, url, pattern, None, 0)
    listing = _run_temp(tmp, base, 1)
    if len(listing) < MIN_ITEMS:
        return None
    listing_urls = {r['url'] for r in listing}

    chosen, paginated = base, False
    for pag, offset in pagination_variants(url):
        _, entry = build_entry(thomas_id, side, url, pattern, pag, offset)
        p1 = {r['url'] for r in _run_temp(tmp, entry, 1)}
        p2 = {r['url'] for r in _run_temp(tmp, entry, 2)}
        if pagination_ok(listing_urls, p1, p2):
            chosen, paginated = entry, True
            break

    dates = [r['date'] for r in listing if r.get('date')]
    return {
        'entry': chosen,
        'results': len(listing),
        'dated_pct': round(100 * len(dates) / len(listing)),
        'latest': str(max(dates)) if dates else None,
        'paginated': paginated,
        'relative_urls': sum(1 for r in listing if not r['url'].startswith('http')),
        'sample': [r['title'][:80] for r in listing[:3]],
    }


def check_feed(url):
    """Check whether an RSS/Atom feed URL is live. Returns a small status dict."""
    url = url.replace('&amp;', '&')
    time.sleep(0.5)
    try:
        r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        return {'url': url, 'live': False, 'error': _error_label(e)}
    doc = BeautifulSoup(r.content, 'xml')
    items = doc.find_all('item') or doc.find_all('entry')
    dates = []
    for item in items:
        tag = item.find('pubDate') or item.find('published') or item.find('updated')
        if tag and tag.text:
            d = Utils.parse_date(tag.text.strip())
            if d:
                dates.append(d)
    return {'url': url, 'live': bool(items), 'items': len(items),
            'latest': str(max(dates)) if dates else None}


def discover_committee(committee, majority):
    """Discover press pages for one committee. Returns a report dict."""
    tid = committee['thomas_id']
    chamber = committee['type']
    majority_party = majority['house'] if chamber == 'house' else majority['senate']
    report = {'thomas_id': tid, 'name': committee['name'], 'type': chamber,
              'hosts': [], 'recommended': [], 'needs_attention': [], 'feeds': []}

    yaml_urls = [u for u in (committee.get('url'), committee.get('minority_url')) if u]
    if not yaml_urls:
        report['note'] = 'no url in committees-current.yaml'
        return report

    bases = []
    for u in yaml_urls:
        for v in host_variants(u):
            if v not in bases:
                bases.append(v)

    hosts, seen_hosts = [], set()
    for base in bases:
        final_url, doc = fetch_with_redirects(base)
        if final_url is None:
            report['hosts'].append({'requested': base, 'error': doc})
            continue
        final_host = urlparse(final_url).netloc.lower()
        record = {'requested': base, 'final': final_url}
        if final_host in seen_hosts:
            record['duplicate'] = True
            report['hosts'].append(record)
            continue
        seen_hosts.add(final_host)
        side = side_for_host(final_host, majority_party)
        has_path = bool(urlparse(final_url).path.strip('/'))
        if side is None and chamber == 'house' and final_host.endswith('.house.gov') \
                and not has_path:
            side = 'majority'
        record['side'] = side
        report['hosts'].append(record)
        hosts.append((final_url, doc, side, has_path))

    candidates, unmatched = [], []
    for final_url, doc, host_side, has_path in hosts:
        root = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}"
        cands = nav_candidates(doc, final_url)[:MAX_CANDIDATES_PER_HOST]
        if not has_path:
            known = {u.rstrip('/') for u, _ in cands}
            paths = HOUSE_PATHS if root.endswith('.house.gov') else SINGLE_HOST_PATHS
            cands += [(root + p, '') for p in paths if (root + p).rstrip('/') not in known]
        for url, text in cands:
            side = host_side or classify_side(url + ' ' + text, majority_party) or 'full'
            scored = score_candidate(url, text)
            if scored is None:
                continue
            if scored['react']:
                report['needs_attention'].append(
                    {'side': side, 'url': url, 'issue': 'React/Next.js page'})
                continue
            if scored['pattern'] is None:
                unmatched.append({'side': side, 'url': url, 'text': text})
                continue
            candidates.append({'url': url, 'side': side, **scored})

    by_side = {}
    for c in sorted(candidates, key=lambda c: -c['score']):
        by_side.setdefault(c['side'], []).append(c)

    found = {}
    for side, cands in by_side.items():
        for c in cands[:3]:
            v = verify_candidate(tid, side, c['url'], c['pattern'])
            if v:
                v['pattern'] = c['pattern']['name']
                found[side] = v
                break

    if 'majority' in found and 'minority' in found:
        found.pop('full', None)

    # Pages that loaded but matched no pattern, for sides with no
    # recommendation: likely listings that need hand-written selectors.
    # Nav links (which carry text) are listed before guessed standard paths.
    per_side = {}
    for u in sorted(unmatched, key=lambda u: not u['text']):
        if u['side'] in found or len(per_side.setdefault(u['side'], [])) >= 3:
            continue
        per_side[u['side']].append(u['url'])
    sides_covered = set(found) | set(per_side)
    if {'majority', 'minority'} <= sides_covered:
        per_side.pop('full', None)
    for side, urls in per_side.items():
        for url in urls:
            report['needs_attention'].append(
                {'side': side, 'url': url, 'issue': 'page loads but no pattern matched'})

    for side in sorted(found):
        v = found[side]
        issues = []
        if v['dated_pct'] < 50:
            issues.append(f"only {v['dated_pct']}% dated")
        if not v['paginated']:
            issues.append('no working pagination')
        if v['relative_urls']:
            issues.append(f"{v['relative_urls']} relative URLs")
        stale = stale_days(v['latest'])
        if stale:
            issues.append(f"newest item is {stale} days old (archive page?)")
        v['issues'] = issues
        report['recommended'].append(v)

    for field in ('rss_url', 'minority_rss_url'):
        if committee.get(field):
            report['feeds'].append({'field': field, **check_feed(committee[field])})

    return report


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_entry(entry):
    key = f"{entry['thomas_id'].lower()}_{entry['side']}"
    return f"    {key!r}: {entry!r},"


def print_report(reports):
    ready, attention, empty = [], [], []
    for r in reports:
        if not r['recommended'] and not r['needs_attention']:
            empty.append(r)
        for v in r['recommended']:
            (attention if v['issues'] else ready).append((r, v))
        for n in r['needs_attention']:
            attention.append((r, n))

    print(f"\n{'=' * 78}\nREADY ({len(ready)}): verified, dated, paginated\n{'=' * 78}")
    for r, v in ready:
        print(f"    # {r['name']} — {v['results']} items, latest {v['latest']}, "
              f"pattern {v['pattern']}")
        print(format_entry(v['entry']))

    print(f"\n{'=' * 78}\nNEEDS ATTENTION ({len(attention)})\n{'=' * 78}")
    for r, v in attention:
        if 'entry' in v:
            print(f"    # {r['name']} — {', '.join(v['issues'])}; "
                  f"{v['results']} items, latest {v['latest']}")
            print(format_entry(v['entry']))
        else:
            print(f"    # {r['thomas_id']} {v['side']}: {v['issue']} — {v['url']}")

    print(f"\n{'=' * 78}\nNO CANDIDATE FOUND ({len(empty)})\n{'=' * 78}")
    for r in empty:
        hosts = ', '.join(h.get('final') or f"{h['requested']} ({h.get('error')})"
                          for h in r['hosts'] if not h.get('duplicate'))
        print(f"  {r['thomas_id']}  {r['name']}  {r.get('note') or hosts}")

    missing = []
    for r in reports:
        sides = {v['entry']['side'] for v in r['recommended']}
        if r['recommended'] and 'full' not in sides and not {'majority', 'minority'} <= sides:
            missing.append(f"  {r['thomas_id']}  has {sorted(sides)}")
    if missing:
        print(f"\n{'=' * 78}\nMISSING A SIDE ({len(missing)})\n{'=' * 78}")
        print('\n'.join(missing))

    live = [(r, f) for r in reports for f in r['feeds'] if f.get('live')]
    if live:
        print(f"\n{'=' * 78}\nLIVE RSS FEEDS IN YAML ({len(live)})\n{'=' * 78}")
        for r, f in live:
            print(f"  {r['thomas_id']}  {f['field']}  {f['items']} items, "
                  f"latest {f['latest']}  {f['url']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--only', help='Comma-separated thomas_ids to check')
    parser.add_argument('--all', action='store_true',
                        help='Include committees already configured or skipped')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--house-majority', default='republicans',
                        choices=['republicans', 'democrats'])
    parser.add_argument('--senate-majority', default='republicans',
                        choices=['republicans', 'democrats'])
    parser.add_argument('--output', default='committee_discovery.json')
    parser.add_argument('--cache', action='store_true',
                        help='Cache listing pages for 24h (handy when re-running)')
    args = parser.parse_args()

    if args.cache:
        Scraper.enable_cache(ttl=86400)

    committees = fetch_committees()
    if args.only:
        wanted = {t.strip().upper() for t in args.only.split(',')}
        committees = [c for c in committees if c['thomas_id'] in wanted]
    elif not args.all:
        done = {e['thomas_id'] for e in COMMITTEE_CONFIG.values()} | set(COMMITTEE_SKIP)
        committees = [c for c in committees if c['thomas_id'] not in done]

    majority = {'house': args.house_majority, 'senate': args.senate_majority}
    print(f"Discovering {len(committees)} committees "
          f"(majority: House {majority['house']}, Senate {majority['senate']})",
          file=sys.stderr)

    reports = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(discover_committee, c, majority): c for c in committees}
        for fut in as_completed(futures):
            c = futures[fut]
            try:
                r = fut.result()
            except Exception as e:  # keep going; report the failure
                r = {'thomas_id': c['thomas_id'], 'name': c['name'], 'type': c['type'],
                     'hosts': [], 'recommended': [], 'needs_attention': [], 'feeds': [],
                     'note': f'error: {type(e).__name__}: {e}'}
            print(f"  {r['thomas_id']}: {len(r['recommended'])} recommended", file=sys.stderr)
            reports.append(r)

    order = {c['thomas_id']: i for i, c in enumerate(committees)}
    reports.sort(key=lambda r: order[r['thomas_id']])

    with open(args.output, 'w') as f:
        json.dump({'generated': datetime.datetime.now().isoformat(timespec='seconds'),
                   'majority': majority, 'committees': reports}, f, indent=2, default=str)
    print_report(reports)
    print(f"\nFull report: {args.output}")


if __name__ == '__main__':
    main()
