#!/usr/bin/env python3
"""
Comprehensive comparison of Ruby and Python scraper methods.
Checks which methods exist in both implementations.
"""

from python_statement.statement import Scraper
import inspect


def get_ruby_member_methods():
    """List of member methods from Ruby scraper.rb."""
    return [
        'crapo', 'trentkelly', 'heinrich', 'document_query_new', 'barr',
        'media_body', 'steube', 'bera', 'meeks', 'sykes', 'barragan', 'castor', 'marshall', 'hawley',
        'jetlisting_h2', 'barrasso', 'timscott', 'senate_drupal_newscontent', 'shaheen',
        'paul', 'tlaib', 'grijalva', 'aguilar', 'bergman', 'scanlon', 'gimenez', 'mcgovern',
        'foxx', 'clarke', 'jayapal', 'carey', 'mikelee',
        'fischer', 'clark', 'cantwell', 'wyden', 'cornyn', 'connolly', 'mast', 'hassan', 'rickscott', 'joyce', 'gosar',
        'article_block_h2', 'griffith', 'daines', 'vanhollen', 'lummis',
        'schumer', 'cassidy', 'takano', 'gillibrand', 'garypeters', 'cortezmasto', 'hydesmith', 'recordlist',
        'rosen', 'schweikert', 'article_block_h2_date', 'hagerty', 'graham', 'article_span_published',
        'grassley', 'lofgren', 'senate_drupal', 'tinasmith', 'rounds', 'kennedy',
        'duckworth', 'angusking', 'tillis', 'emmer', 'house_title_header', 'lujan',
        'ronjohnson', 'mullin', 'brownley',
        'porter', 'jasonsmith', 'bacon', 'capito', 'tonko', 'larsen', 'mooney', 'ellzey', 'media_digest', 'crawford', 'lucas', 'article_newsblocker',
        'pressley', 'reschenthaler', 'norcross',
        'jeffries', 'article_block', 'jackreed', 'blackburn', 'murphy', 'schatz', 'kaine', 'cruz', 'padilla', 'baldwin', 'clyburn',
        'titus', 'houlahan', 'react', 'tokuda', 'huizenga',
        'moran', 'murray', 'thune', 'tuberville', 'warner', 'boozman', 'fetterman', 'rubio', 'whitehouse', 'wicker', 'toddyoung',
        'britt', 'markey', 'budd', 'elementor_post_date', 'markkelly',
        'ossoff', 'vance', 'welch', 'cotton'
    ]


def get_python_member_methods():
    """Get list of member methods from Python Scraper class."""
    methods = []
    for name, method in inspect.getmembers(Scraper, predicate=inspect.ismethod):
        # Exclude private methods, utility methods, and generic methods
        if not name.startswith('_') and name not in ['open_html', 'current_year', 'current_month', 'member_methods', 'committee_methods', 'member_scrapers']:
            methods.append(name)
    return methods


def main():
    """Main comparison function."""
    print("Comparing Member Scraper Methods")
    print("=" * 80)
    
    ruby_methods = set(get_ruby_member_methods())
    python_methods = set(get_python_member_methods())
    
    print(f"\nTotal methods in Ruby: {len(ruby_methods)}")
    print(f"Total methods in Python: {len(python_methods)}")
    
    # Methods in Ruby but not in Python
    missing_in_python = ruby_methods - python_methods
    if missing_in_python:
        print(f"\n❌ Methods in Ruby but NOT implemented in Python ({len(missing_in_python)}):")
        for method in sorted(missing_in_python):
            print(f"  - {method}")
    
    # Methods in Python but not in Ruby
    extra_in_python = python_methods - ruby_methods
    if extra_in_python:
        print(f"\n⚠️  Methods in Python but NOT in Ruby ({len(extra_in_python)}):")
        for method in sorted(extra_in_python):
            print(f"  - {method}")
    
    # Methods that exist in both
    common_methods = ruby_methods & python_methods
    print(f"\n✅ Methods implemented in both ({len(common_methods)}):")
    for method in sorted(common_methods):
        print(f"  - {method}")
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    implementation_percentage = (len(common_methods) / len(ruby_methods)) * 100
    print(f"Implementation coverage: {implementation_percentage:.1f}% ({len(common_methods)}/{len(ruby_methods)})")
    
    if not missing_in_python:
        print("✅ All Ruby member methods are implemented in Python!")
    else:
        print(f"❌ {len(missing_in_python)} methods still need to be implemented")


if __name__ == "__main__":
    main()
