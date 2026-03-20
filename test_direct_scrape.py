"""Test direct scraping of a specific YTS movie page"""
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

scraper = YTSScraper()

# Test with a known popular movie URL
test_url = "https://www.yts-official.top/movies/inception-2010"

print(f"🔍 Testing scrape of: {test_url}\n")

details = scraper.scrape_movie_details(test_url)

if details:
    print("✅ Scraping successful!")
    print(f"\nDescription: {details.get('description', 'N/A')[:100]}...")
    print(f"\nGenres: {details.get('genres', [])}")
    
    torrents = details.get('torrents', [])
    print(f"\n🎬 Found {len(torrents)} torrents:")
    
    if torrents:
        for t in torrents:
            print(f"  - {t.get('quality', '?')} ({t.get('size', '?')})")
            print(f"    Magnet: {t.get('magnet_link', 'MISSING')[:50]}...")
            print(f"    Torrent: {t.get('torrent_url', 'MISSING')[:50]}...")
    else:
        print("  ⚠️  No torrents found on page")
        print("  💡 Checking what we found on the page...")
        
        # Debug: Try to see what's on the page
        from backend.scraper import YTSScraper
        soup = scraper._make_request(test_url)
        if soup:
            # Check for quality sections
            quality_sections = soup.select('p.quality-size')
            print(f"  Quality sections found: {len(quality_sections)}")
            
            # Check for magnet links
            magnet_links = soup.select('a[href^="magnet:"]')
            print(f"  Magnet links found: {len(magnet_links)}")
            
            # Check for download buttons
            download_links = soup.select('a.download-torrent')
            print(f"  Download torrent links found: {len(download_links)}")
            
            # Try alternative selectors
            print("\n  🔎 Trying alternative selectors...")
            alt_download = soup.select('a[href*="torrent"]')
            print(f"  Links with 'torrent': {len(alt_download)}")
            
            alt_magnet = soup.select('a[href*="magnet"]')
            print(f"  Links with 'magnet': {len(alt_magnet)}")
else:
    print("❌ Failed to scrape page")
    print("   Check internet connection and YTS site accessibility")
