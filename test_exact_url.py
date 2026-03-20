
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

logging.basicConfig(level=logging.INFO)

def test_exact_url():
    scraper = YTSScraper()
    
    # URL confirmed by subagent
    url = "https://yts.bz/browse-movies/0/720p/all/0/latest/2024/all?page=1"
    print(f"\nFetching EXACT URL: {url}")
    soup = scraper._make_request(url)
    if not soup:
        print("FAIL: Could not fetch URL")
        return

    from shared.constants import YTS_SELECTORS
    movie_cards = soup.select(YTS_SELECTORS['movie_cards'])
    print(f"Found {len(movie_cards)} movie cards")
    
    for i, card in enumerate(movie_cards[:10]):
        data = scraper._parse_movie_card(card)
        if data:
            print(f"[{i+1}] {data['title']} ({data['year']}) - URL: {data['yts_url']}")

if __name__ == "__main__":
    test_exact_url()
