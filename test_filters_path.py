
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

logging.basicConfig(level=logging.INFO)

def test_filters():
    scraper = YTSScraper()
    
    # Test Year=2010, Quality=1080p, Genre=Comedy
    print("\nTesting: Year=2010, Quality=1080p, Genre=Comedy")
    movies2 = scraper.scrape_browse_filtered(
        year="2010",
        quality="1080p",
        genre="comedy",
        max_pages=1
    )
    
    print(f"Total movies found: {len(movies)}")
    for m in movies[:5]:
        print(f" - {m['title']} ({m['year']}) - URL: {m['yts_url']}")
        # Note: scrape_browse_filtered doesn't fetch torrents, only the card info.
        # But we can see if it's actually getting results.

    if not movies:
        print("FAIL: No movies found with filters!")
    else:
        print("SUCCESS: Movies found.")

    # Test Year=2010, Quality=1080p, Genre=Comedy
    print("\nTesting: Year=2010, Quality=1080p, Genre=Comedy")
    movies2 = scraper.scrape_browse_filtered(
        year="2010",
        quality="1080p",
        genre="comedy",
        max_pages=1
    )
    print(f"Total movies found: {len(movies2)}")
    for m in movies2[:5]:
        print(f" - {m['title']} ({m['year']})")

if __name__ == "__main__":
    test_filters()
