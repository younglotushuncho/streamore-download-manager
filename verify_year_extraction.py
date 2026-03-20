
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

# Set logging to ERROR to keep output clean, but scraper uses INFO for counts
logging.basicConfig(level=logging.ERROR)

def test_year_extraction():
    scraper = YTSScraper()
    url = "https://yts.bz/browse-movies/0/all/all/0/latest/2010/en?page=1"
    print(f"Scraping: {url}")
    soup = scraper._make_request(url)
    if not soup:
        print("Failed to fetch.")
        return
        
    from shared.constants import YTS_SELECTORS
    movie_cards = soup.select(YTS_SELECTORS['movie_cards'])
    print(f"Found {len(movie_cards)} cards.")
    
    for i, card in enumerate(movie_cards):
        data = scraper._parse_movie_card(card)
        title = data['title'] if data else "PARSE FAILED"
        year = data['year'] if data else "????"
        year_elem = card.select_one(YTS_SELECTORS['year'])
        raw_year_text = year_elem.text.strip() if year_elem else "MISSING ELEM"
        print(f" [{i+1}] {title} | Parsed Year: {year} | Raw Year Elem: {raw_year_text}")

if __name__ == "__main__":
    test_year_extraction()
