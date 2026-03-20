
import logging
import sys
import os

sys.path.append(os.getcwd())

from backend.scraper import YTSScraper

logging.basicConfig(level=logging.ERROR)

def test_genres():
    scraper = YTSScraper()
    url = "https://yts.bz/browse-movies/0/720p/all/0/latest/2026/en"
    # Use internal _make_request to see what details we get
    soup = scraper._make_request(url)
    cards = soup.select('div.browse-movie-wrap')
    
    print(f"Testing genres on {len(cards)} cards...")
    for i, card in enumerate(cards[:5]):
        data = scraper._parse_movie_card(card)
        if data:
            print(f"[{i+1}] {data['title']} ({data['year']}) Genres: {data['genres']}")

if __name__ == "__main__":
    test_genres()
