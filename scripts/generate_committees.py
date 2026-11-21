#!/usr/bin/env python
"""
Match current congressional committees to committee scrapers.

The canonical committee list is committees-current.yaml from
unitedstates/congress-legislators. Committees are joined to COMMITTEE_CONFIG
on thomas_id. Writes:

    committees_with_scrapers.json     committees with at least one scraper
    committees_without_scrapers.json  committees with none (excluding COMMITTEE_SKIP)

and prints committees missing a minority scraper and config/skip entries whose
thomas_id is no longer in the YAML (dissolved or renamed committees).
Subcommittees are ignored.
"""

import json
from collections import defaultdict

import requests
import yaml

COMMITTEES_URL = (
    "https://raw.githubusercontent.com/unitedstates/congress-legislators/"
    "refs/heads/main/committees-current.yaml"
)

# Fields copied from the YAML into the output records.
RECORD_FIELDS = ['thomas_id', 'name', 'type', 'url', 'minority_url', 'rss_url', 'minority_rss_url']

WITH_FILE = "committees_with_scrapers.json"
WITHOUT_FILE = "committees_without_scrapers.json"


def fetch_committees():
    """Fetch current committees from the unitedstates/congress-legislators repository."""
    response = requests.get(COMMITTEES_URL, timeout=30)
    response.raise_for_status()
    return yaml.safe_load(response.content)


def match_committees(committees, config, skip):
    """Join committees to scraper config entries on thomas_id.

    Args:
        committees: Parsed committees-current.yaml (list of dicts).
        config: COMMITTEE_CONFIG-shaped dict.
        skip: COMMITTEE_SKIP-shaped dict (thomas_id -> reason).

    Returns:
        dict with keys:
            with_scrapers: committee records with a 'scrapers' list and 'needs_minority'
            without_scrapers: committee records with no scraper and not skipped
            skipped: {thomas_id, name, reason} for committees in skip
            orphans: {thomas_id, source, names} for config/skip ids not in the YAML
    """
    scrapers_by_id = defaultdict(list)
    for name in sorted(config):
        entry = config[name]
        scrapers_by_id[entry['thomas_id']].append({
            'scraper_method': name,
            'side': entry['side'],
            'url_base': entry['url_base'],
        })

    with_scrapers, without_scrapers, skipped = [], [], []
    yaml_ids = set()
    for committee in committees:
        thomas_id = committee['thomas_id']
        yaml_ids.add(thomas_id)
        record = {field: committee.get(field) for field in RECORD_FIELDS}
        scrapers = scrapers_by_id.get(thomas_id)
        if scrapers:
            sides = {s['side'] for s in scrapers}
            record['scrapers'] = scrapers
            record['needs_minority'] = bool(
                committee.get('minority_url') and not sides & {'minority', 'full'}
            )
            with_scrapers.append(record)
        elif thomas_id in skip:
            skipped.append({'thomas_id': thomas_id, 'name': committee['name'],
                            'reason': skip[thomas_id]})
        else:
            without_scrapers.append(record)

    orphans = [
        {'thomas_id': tid, 'source': 'COMMITTEE_CONFIG',
         'names': [s['scraper_method'] for s in scrapers_by_id[tid]]}
        for tid in sorted(set(scrapers_by_id) - yaml_ids)
    ] + [
        {'thomas_id': tid, 'source': 'COMMITTEE_SKIP', 'names': []}
        for tid in sorted(set(skip) - yaml_ids)
    ]

    return {
        'with_scrapers': with_scrapers,
        'without_scrapers': without_scrapers,
        'skipped': skipped,
        'orphans': orphans,
    }


def print_summary(result, total):
    """Print a coverage summary."""
    with_s = result['with_scrapers']
    print(f"Committees in YAML: {total}")
    print(f"  With scrapers:    {len(with_s)}")
    print(f"  Without scrapers: {len(result['without_scrapers'])}")
    print(f"  Skipped:          {len(result['skipped'])}")
    print(f"  Scraper entries:  {sum(len(c['scrapers']) for c in with_s)}")

    if result['without_scrapers']:
        print("\nWithout scrapers:")
        for c in result['without_scrapers']:
            print(f"  {c['thomas_id']}  {c['name']}  {c['url'] or '(no url)'}")

    needs_minority = [c for c in with_s if c['needs_minority']]
    if needs_minority:
        print("\nMissing a minority scraper (YAML lists minority_url):")
        for c in needs_minority:
            print(f"  {c['thomas_id']}  {c['minority_url']}")

    if result['orphans']:
        print("\nWARNING: thomas_ids not in committees-current.yaml (dissolved or renamed?):")
        for o in result['orphans']:
            names = ', '.join(o['names'])
            print(f"  {o['thomas_id']} in {o['source']}" + (f": {names}" if names else ""))


def main():
    from python_statement.committee_config import COMMITTEE_CONFIG, COMMITTEE_SKIP

    committees = fetch_committees()
    result = match_committees(committees, COMMITTEE_CONFIG, COMMITTEE_SKIP)
    print_summary(result, len(committees))

    with open(WITH_FILE, 'w') as f:
        json.dump(result['with_scrapers'], f, indent=2)
    print(f"\n✓ Saved {len(result['with_scrapers'])} committees to {WITH_FILE}")

    with open(WITHOUT_FILE, 'w') as f:
        json.dump(result['without_scrapers'], f, indent=2)
    print(f"✓ Saved {len(result['without_scrapers'])} committees to {WITHOUT_FILE}")


if __name__ == "__main__":
    main()
