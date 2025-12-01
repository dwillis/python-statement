#!/usr/bin/env python
"""
Test script for the react scraper with error tracking.
"""

from python_statement.statement import Scraper
import time
from datetime import datetime

def test_react_scraper():
    """Run the react scraper and track successes and errors."""
    
    print("=" * 80)
    print("TESTING REACT SCRAPER")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Track results
    successes = []
    errors = []
    total_results = []
    
    # Get all domains from the react method
    from inspect import getsource
    source = getsource(Scraper.react)
    
    # Extract domains from the source
    import re
    domain_pattern = r'"([a-z0-9\-]+\.house\.gov)"'
    all_domains = re.findall(domain_pattern, source)
    
    print(f"Found {len(all_domains)} domains to test")
    print()
    
    for idx, domain in enumerate(all_domains, 1):
        url = f"https://{domain}/press"
        print(f"[{idx}/{len(all_domains)}] Processing: {url}")
        
        try:
            # Try to scrape the domain
            results = Scraper.react(domains=[domain])
            
            if results:
                num_results = len(results)
                successes.append({
                    'domain': domain,
                    'count': num_results,
                    'results': results
                })
                total_results.extend(results)
                print(f"  ✓ Success: Found {num_results} press releases")
                
                # Show sample result
                if results:
                    sample = results[0]
                    print(f"  Sample: {sample['title'][:60]}...")
                    print(f"  Date: {sample.get('date', 'N/A')}")
            else:
                errors.append({
                    'domain': domain,
                    'url': url,
                    'error': 'No results returned'
                })
                print(f"  ✗ Warning: No results found")
                
        except Exception as e:
            errors.append({
                'domain': domain,
                'url': url,
                'error': str(e)
            })
            print(f"  ✗ Error: {str(e)}")
        
        print()
        # Small delay to be respectful
        time.sleep(0.5)
    
    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total domains tested: {len(all_domains)}")
    print(f"Successful scrapes: {len(successes)}")
    print(f"Failed scrapes: {len(errors)}")
    print(f"Total press releases found: {len(total_results)}")
    print(f"Success rate: {len(successes)/len(all_domains)*100:.1f}%")
    print()
    
    if successes:
        print("SUCCESSFUL DOMAINS:")
        for success in successes:
            print(f"  • {success['domain']}: {success['count']} releases")
        print()
    
    if errors:
        print("FAILED DOMAINS:")
        for error in errors:
            print(f"  • {error['domain']}")
            print(f"    URL: {error['url']}")
            print(f"    Error: {error['error']}")
        print()
    
    # Sample results
    if total_results:
        print("SAMPLE RESULTS (first 5):")
        for i, result in enumerate(total_results[:5], 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Date: {result.get('date', 'N/A')}")
            print(f"   Domain: {result['domain']}")
    
    print()
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return {
        'successes': successes,
        'errors': errors,
        'total_results': total_results
    }

if __name__ == "__main__":
    results = test_react_scraper()
