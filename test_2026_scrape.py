
import logging
import sys
import os

# Add the current directory to sys.path so we can import backend
sys.path.append(os.getcwd())

from backend.scraper import YTSScraper

logging.basicConfig(level=logging.INFO)

def check_2026():
    scraper = YTSScraper()
    # Mock the filters the user might be using
    # Link: https://yts.bz/browse-movies/0/720p/all/0/latest/2026/en
    movies = scraper.scrape_browse_filtered(
        quality='720p',
        genre='all',
        year='2026',
        order_by='latest'
    )
    
    print(f"\nResults for 2026 / 720p / latest:")
    print(f"Total movies found: {len(movies)}")
    for i, m in enumerate(movies[:10]):
        print(f"[{i+1}] {m['title']} ({m['year']}) - {m['yts_url']}")

if __name__ == "__main__":
    check_2026()
