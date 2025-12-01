#!/usr/bin/env python3
"""
Compare URLs between Ruby and Python scrapers to ensure they match.
Reports any discrepancies found.
"""

import re
from python_statement.statement import Scraper
import inspect


def extract_ruby_media_body_urls():
    """Extract URLs from Ruby media_body method (hardcoded from Ruby scraper.rb)."""
    return [
        "https://issa.house.gov/media/press-releases",
        "https://tenney.house.gov/media/press-releases",
        "https://amodei.house.gov/news-releases",
        "https://palmer.house.gov/media-center/press-releases",
        "https://newhouse.house.gov/media-center/press-releases",
        "https://doggett.house.gov/media/press-releases",
        "https://ocasio-cortez.house.gov/media/press-releases",
        "https://hudson.house.gov/media/press-releases",
        "https://davis.house.gov/media",
        "https://espaillat.house.gov/media/press-releases",
        "https://algreen.house.gov/media/press-releases",
        "https://mariodiazbalart.house.gov/media-center/press-releases",
        "https://biggs.house.gov/media/press-releases",
        "https://johnjoyce.house.gov/media/press-releases",
        "https://larson.house.gov/media-center/press-releases",
        "https://kaptur.house.gov/media-center/press-releases",
        "https://benniethompson.house.gov/media/press-releases",
        "https://walberg.house.gov/media/press-releases",
        "https://burchett.house.gov/media/press-releases",
        "https://cline.house.gov/media/press-releases",
        "https://golden.house.gov/media/press-releases",
        "https://harder.house.gov/media/press-releases",
        "https://dustyjohnson.house.gov/media/press-releases",
        "https://meuser.house.gov/media/press-releases",
        "https://miller.house.gov/media/press-releases",
        "https://johnrose.house.gov/media/press-releases",
        "https://roy.house.gov/media/press-releases",
        "https://sherrill.house.gov/media/press-releases",
        "https://steil.house.gov/media/press-releases",
        "https://schrier.house.gov/media/press-releases",
        "https://cherfilus-mccormick.house.gov/media/press-releases",
        "https://shontelbrown.house.gov/media/press-releases",
        "https://stansbury.house.gov/media/press-releases",
        "https://troycarter.house.gov/media/press-releases",
        "https://letlow.house.gov/media/press-releases",
        "https://matsui.house.gov/media",
        "https://harris.house.gov/media/press-releases",
        "https://wagner.house.gov/media-center/press-releases",
        "https://pappas.house.gov/media/press-releases",
        "https://crow.house.gov/media/press-releases",
        "https://chuygarcia.house.gov/media/press-releases",
        "https://omar.house.gov/media/press-releases",
        "https://underwood.house.gov/media/press-releases",
        "https://casten.house.gov/media/press-releases",
        "https://fleischmann.house.gov/media/press-releases",
        "https://stevens.house.gov/media/press-releases",
        "https://guest.house.gov/media/press-releases",
        "https://morelle.house.gov/media/press-releases",
        "https://beatty.house.gov/media-center/press-releases",
        "https://robinkelly.house.gov/media-center/press-releases",
        "https://moolenaar.house.gov/media-center/press-releases",
        "https://adams.house.gov/media-center/press-releases",
        "https://mfume.house.gov/media/press-releases",
        "https://tiffany.house.gov/media/press-releases",
        "https://barrymoore.house.gov/media/press-releases",
        "https://obernolte.house.gov/media/press-releases",
        "https://boebert.house.gov/media/press-releases",
        "https://cammack.house.gov/media/press-releases",
        "https://salazar.house.gov/media/press-releases",
        "https://hinson.house.gov/media/press-releases",
        "https://millermeeks.house.gov/media/press-releases",
        "https://feenstra.house.gov/media/press-releases",
        "https://marymiller.house.gov/media/press-releases",
        "https://mrvan.house.gov/media/press-releases",
        "https://spartz.house.gov/media/press-releases",
        "https://mann.house.gov/media/press-releases",
        "https://garbarino.house.gov/media/press-releases",
        "https://malliotakis.house.gov/media/press-releases",
        "https://bice.house.gov/media/press-releases",
        "https://bentz.house.gov/media/press-releases",
        "https://mace.house.gov/media/press-releases",
        "https://harshbarger.house.gov/media/press-releases",
        "https://blakemoore.house.gov/media/press-releases",
        "https://fitzgerald.house.gov/media/press-releases",
        "https://flood.house.gov/media/press-releases",
        "https://patryan.house.gov/media/press-releases",
        "https://kamlager-dove.house.gov/media/press-releases",
        "https://robertgarcia.house.gov/media/press-releases",
        "https://bean.house.gov/media/press-releases",
        "https://mccormick.house.gov/media/press-releases",
        "https://collins.house.gov/media/press-releases",
        "https://edwards.house.gov/media/press-releases",
        "https://kean.house.gov/media/press-releases",
        "https://goldman.house.gov/media/press-releases",
        "https://langworthy.house.gov/media/press-releases",
        "https://magaziner.house.gov/media/press-releases",
        "https://vanorden.house.gov/media/press-releases",
        "https://hunt.house.gov/media/press-releases",
        "https://casar.house.gov/media/press-releases",
        "https://crockett.house.gov/media/press-releases",
        "https://luttrell.house.gov/media/press-releases",
        "https://deluzio.house.gov/media/press-releases",
        "https://lalota.house.gov/media/press-releases",
        "https://vasquez.house.gov/media/press-releases",
        "https://scholten.house.gov/media/press-releases",
        "https://ivey.house.gov/media/press-releases",
        "https://sorensen.house.gov/media/press-releases",
        "https://nunn.house.gov/media/press-releases",
        "https://laurellee.house.gov/media/press-releases",
        "https://mills.house.gov/media/press-releases",
        "https://ciscomani.house.gov/media/press-releases",
        "https://democraticleader.house.gov/media/press-releases",
        "https://horsford.house.gov/media/press-releases",
        "https://cleaver.house.gov/media-center/press-releases",
        "https://aderholt.house.gov/media-center/press-releases",
        "https://courtney.house.gov/media-center/press-releases",
        "https://stauber.house.gov/media/press-releases",
        "https://mccaul.house.gov/media-center/press-releases",
        "https://foster.house.gov/media/press-releases",
        "https://schakowsky.house.gov/media/press-releases",
        "https://craig.house.gov/media/press-releases",
        "https://desaulnier.house.gov/media-center/press-releases",
        "https://scalise.house.gov/media/press-releases",
        "https://neguse.house.gov/media/press-releases",
        "https://murphy.house.gov/media/press-releases",
        "https://boyle.house.gov/media-center/press-releases",
        "https://calvert.house.gov/media/press-releases",
        "https://bobbyscott.house.gov/media-center/press-releases",
        "https://bilirakis.house.gov/media/press-releases",
        "https://delauro.house.gov/media-center/press-releases",
        "https://norton.house.gov/media/press-releases",
        "https://mikethompson.house.gov/newsroom/press-releases",
        "https://smucker.house.gov/media/press-releases",
        "https://degette.house.gov/media-center/press-releases",
        "https://ruiz.house.gov/media-center/press-releases",
        "https://sherman.house.gov/media-center/press-releases",
        "https://quigley.house.gov/media-center/press-releases",
        "https://waters.house.gov/media-center/press-releases",
        "https://swalwell.house.gov/media-center/press-releases",
        "https://khanna.house.gov/media/press-releases",
        "https://panetta.house.gov/media/press-releases",
        "https://schneider.house.gov/media/press-releases",
        "https://dankildee.house.gov/media/press-releases",
        "https://sylviagarcia.house.gov/media/press-releases",
        "https://susielee.house.gov/media/press-releases",
        "https://amo.house.gov/press-releases",
        "https://mcclellan.house.gov/media/press-releases",
        "https://rulli.house.gov/media/press-releases",
        "https://suozzi.house.gov/media/press-releases",
        "https://fong.house.gov/media/press-releases",
        "https://lopez.house.gov/media/press-releases",
        "https://mciver.house.gov/media/press-releases",
        "https://wied.house.gov/media/press-releases",
        "https://ericaleecarter.house.gov/media/press-releases",
        "https://moulton.house.gov/news/press-releases",
        "https://nehls.house.gov/media",
        "https://meng.house.gov/media-center/press-releases",
        "https://lindasanchez.house.gov/media-center/press-releases",
        "https://lamalfa.house.gov/media-center/press-releases",
        "https://dondavis.house.gov/media/press-releases",
        "https://strong.house.gov/media/press-releases",
        "https://chu.house.gov/media-center/press-releases",
        "https://lieu.house.gov/media-center/press-releases",
        "https://joewilson.house.gov/media/press-releases",
        "https://zinke.house.gov/media/press-releases",
        "https://pelosi.house.gov/news/press-releases",
        "https://rutherford.house.gov/media/press-releases",
        "https://veasey.house.gov/media-center/press-releases",
        "https://garamendi.house.gov/media/press-releases",
        "https://kustoff.house.gov/media/press-releases",
        "https://gonzalez.house.gov/media/press-releases",
        "https://costa.house.gov/media/press-releases",
        "https://houchin.house.gov/media/press-releases",
        "https://williams.house.gov/media-center/press-releases",
        "https://menendez.house.gov/media/press-releases",
        "https://pocan.house.gov/media-center/press-releases",
        "https://ogles.house.gov/media/press-releases",
        "https://velazquez.house.gov/media-center/press-releases",
        "https://bonamici.house.gov/media/press-releases",
        "https://keithself.house.gov/media/press-releases",
        "https://bishop.house.gov/media-center/press-releases",
        "https://hoyer.house.gov/media",
        "https://burlison.house.gov/media/press-releases",
        "https://jonathanjackson.house.gov/media/press-releases",
        "https://davids.house.gov/media/press-releases",
        "https://mccollum.house.gov/media/press-releases",
        "https://adamsmith.house.gov/news/press-releases",
        "https://hankjohnson.house.gov/media-center/press-releases",
        "https://evans.house.gov/media/press-releases",
        "https://salinas.house.gov/media/press-releases",
        "https://pallone.house.gov/media/press-releases",
        "https://ramirez.house.gov/media/press-releases",
        "https://graves.house.gov/media/press-releases",
        "https://cole.house.gov/media-center/press-releases",
        "https://jordan.house.gov/media/press-releases",
        "https://hageman.house.gov/media/press-releases",
        "https://figures.house.gov/media",
        "https://begich.house.gov/media/press-releases",
        "https://ansari.house.gov/media/press-releases",
        "https://simon.house.gov/media/press-releases",
        "https://gray.house.gov/media/press-releases",
        "https://liccardo.house.gov/media/press-releases",
        "https://rivas.house.gov/media/press-releases",
        "https://friedman.house.gov/media/press-releases",
        "https://tran.house.gov/media/press-releases",
        "https://min.house.gov/media/press-releases",
        "https://hurd.house.gov/media/press-releases",
        "https://crank.house.gov/media/press-releases",
        "https://gabeevans.house.gov/media/press-releases",
        "https://mcbride.house.gov/media/press-releases",
        "https://haridopolos.house.gov/media/press-releases",
        "https://jack.house.gov/media/press-releases",
        "https://stutzman.house.gov/media/press-releases",
        "https://shreve.house.gov/media/press-releases",
        "https://fields.house.gov/media/press-releases",
        "https://olszewski.house.gov/media/press-releases",
        "https://elfreth.house.gov/media/press-releases",
        "https://mcclaindelaney.house.gov/media/press-releases",
        "https://mcdonaldrivet.house.gov/media/press-releases",
        "https://barrett.house.gov/media/press-releases",
        "https://morrison.house.gov/media/press-releases",
        "https://bell.house.gov/media/press-releases",
        "https://downing.house.gov/media/press-releases",
        "https://goodlander.house.gov/media/press-releases",
        "https://pou.house.gov/media/press-releases",
        "https://mciver.house.gov/media/press-releases",  # Note: appears twice in Ruby
        "https://gillen.house.gov/media/press-releases",
        "https://latimer.house.gov/media/press-releases",
        "https://riley.house.gov/media/press-releases",
        "https://mannion.house.gov/media/press-releases",
        "https://mcdowell.house.gov/media/press-releases",
        "https://markharris.house.gov/media/press-releases",
        "https://harrigan.house.gov/media/press-releases",
        "https://knott.house.gov/media/press-releases",
        "https://timmoore.house.gov/media/press-releases",
        "https://fedorchak.house.gov/media/press-releases",
        "https://king-hinds.house.gov/media",
        "https://taylor.house.gov/media/press-releases",
        "https://dexter.house.gov/media/press-releases",
        "https://bynum.house.gov/media/press-releases",
        "https://mackenzie.house.gov/media/press-releases",
        "https://bresnahan.house.gov/media",
        "https://hernandez.house.gov/media/press-releases",
        "https://sheribiggs.house.gov/media/press-releases",
        "https://craiggoldman.house.gov/media/press-releases",
        "https://sylvesterturner.house.gov/media/press-releases",
        "https://gill.house.gov/media/press-releases",
        "https://juliejohnson.house.gov/media/press-releases",
        "https://mcguire.house.gov/media/press-releases",
        "https://vindman.house.gov/media/press-releases",
        "https://subramanyam.house.gov/media/press-releases",
        "https://baumgartner.house.gov/media/press-releases",
        "https://randall.house.gov/media/press-releases",
        "https://rileymoore.house.gov/media/press-releases"
    ]


def extract_ruby_react_domains():
    """Extract domains from Ruby react method."""
    return [
        "nikemawilliams.house.gov",
        "kiley.house.gov",
        "nehls.house.gov",
        "yakym.house.gov",
        "ritchietorres.house.gov",
        "cloud.house.gov",
        "owens.house.gov",
        "budzinski.house.gov",
        "gluesenkampperez.house.gov",
        "landsman.house.gov",
        "moskowitz.house.gov",
        "gottheimer.house.gov",
        "kiggans.house.gov",
        "luna.house.gov",
        "maxmiller.house.gov",
    ]


def extract_python_media_body_urls():
    """Extract URLs from Python media_body method."""
    # Get the source code of the media_body method
    source = inspect.getsource(Scraper.media_body)
    
    # Extract all URLs using regex - only from the urls array, not from code
    # Look for lines that are just URL strings in the array
    url_pattern = r'^\s*"(https://[a-z\-]+\.house\.gov/[^"]+)",?\s*$'
    urls = []
    for line in source.split('\n'):
        match = re.match(url_pattern, line)
        if match:
            urls.append(match.group(1))
    
    return urls


def extract_python_react_domains():
    """Extract domains from Python react method."""
    # Get the source code of the react method
    source = inspect.getsource(Scraper.react)
    
    # Extract all domains using regex
    domain_pattern = r'"([a-z\-]+\.house\.gov)"'
    domains = re.findall(domain_pattern, source)
    
    return domains


def compare_lists(ruby_list, python_list, list_name):
    """Compare two lists and print discrepancies."""
    ruby_set = set(ruby_list)
    python_set = set(python_list)
    
    in_ruby_not_python = ruby_set - python_set
    in_python_not_ruby = python_set - ruby_set
    
    print(f"\n{'=' * 80}")
    print(f"{list_name} Comparison")
    print(f"{'=' * 80}")
    print(f"Total in Ruby: {len(ruby_list)}")
    print(f"Total in Python: {len(python_list)}")
    print(f"Unique in Ruby: {len(ruby_set)}")
    print(f"Unique in Python: {len(python_set)}")
    
    if in_ruby_not_python:
        print(f"\n❌ In Ruby but NOT in Python ({len(in_ruby_not_python)}):")
        for item in sorted(in_ruby_not_python):
            print(f"  - {item}")
    
    if in_python_not_ruby:
        print(f"\n❌ In Python but NOT in Ruby ({len(in_python_not_ruby)}):")
        for item in sorted(in_python_not_ruby):
            print(f"  - {item}")
    
    if not in_ruby_not_python and not in_python_not_ruby:
        print("\n✅ All URLs/domains match between Ruby and Python!")
    
    return len(in_ruby_not_python) == 0 and len(in_python_not_ruby) == 0


def main():
    """Main comparison function."""
    print("Comparing Ruby and Python scrapers...")
    print("=" * 80)
    
    # Compare media_body URLs
    ruby_media_body = extract_ruby_media_body_urls()
    python_media_body = extract_python_media_body_urls()
    media_body_match = compare_lists(ruby_media_body, python_media_body, "media_body URLs")
    
    # Compare react domains
    ruby_react = extract_ruby_react_domains()
    python_react = extract_python_react_domains()
    react_match = compare_lists(ruby_react, python_react, "react domains")
    
    # Final summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    if media_body_match and react_match:
        print("✅ All scrapers match between Ruby and Python!")
    else:
        print("❌ Discrepancies found. Please update the Python implementation.")
        if not media_body_match:
            print("  - media_body URLs need updating")
        if not react_match:
            print("  - react domains need updating")


if __name__ == "__main__":
    main()
