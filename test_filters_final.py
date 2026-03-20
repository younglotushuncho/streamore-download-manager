
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

# Set logging to INFO to see the URLs being fetched
logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_filters():
    scraper = YTSScraper()
    
    # Test 1: Year 2010
    print("\n--- TEST 1: Year 2010, Quality all, Genre all ---")
    movies = scraper.scrape_browse_filtered(
        year="2010",
        quality="all",
        genre="all",
        max_pages=1
    )
    print(f"Total movies found: {len(movies)}")
    for m in movies[:3]:
        print(f" - {m['title']} ({m['year']})")

    # Test 2: Year 2024, Quality 720p, Genre all
    print("\n--- TEST 2: Year 2024, Quality 720p, Genre all ---")
    movies = scraper.scrape_browse_filtered(
        year="2024",
        quality="720p",
        genre="all",
        max_pages=1
    )
    print(f"Total movies found: {len(movies)}")
    for m in movies[:3]:
        print(f" - {m['title']} ({m['year']})")

if __name__ == "__main__":
    test_filters()
