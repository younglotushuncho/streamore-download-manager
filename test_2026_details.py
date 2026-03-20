
import logging
import sys
import os

sys.path.append(os.getcwd())

from backend.scraper import YTSScraper

logging.basicConfig(level=logging.INFO)

def test_details():
    scraper = YTSScraper()
    # "Romance at Hope Ranch" URL from chunk 1
    url = "https://yts.bz/movies/romance-at-hope-ranch-2026"
    details = scraper.scrape_movie_details(url)
    if details:
        print(f"\nDetails for {url}:")
        print(f"Description: {details.get('description', 'N/A')[:100]}...")
        print(f"Genres: {details.get('genres', [])}")
        print(f"Torrents: {len(details.get('torrents', []))}")
        for t in details.get('torrents', []):
            print(f"  - {t['quality']} {t['size']}")
    else:
        print(f"Failed to get details for {url}")

if __name__ == "__main__":
    test_details()
