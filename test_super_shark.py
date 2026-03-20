"""Get Super Shark URL and test scraping it"""
import requests
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

# Get Super Shark from API
r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 1})
movie = r.json()['movies'][0]

print(f"🎬 Movie: {movie['title']}")
print(f"   YTS URL: {movie.get('yts_url')}")

if not movie.get('yts_url'):
    print("   ⚠️  No YTS URL stored!")
    exit(1)

# Try scraping it
scraper = YTSScraper()
print(f"\n🔄 Scraping {movie['yts_url']}...")
movie_data = scraper.scrape_movie_details(movie['yts_url'])

if movie_data:
    torrents = movie_data.get('torrents', [])
    print(f"\n✅ Found {len(torrents)} torrents:")
    for t in torrents:
        print(f"   - {t['quality']} ({t['size']})")
else:
    print(f"\n❌ Failed to scrape movie")
