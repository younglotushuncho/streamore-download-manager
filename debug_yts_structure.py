"""Debug YTS page structure to fix selectors"""
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

scraper = YTSScraper()
test_url = "https://www.yts-official.top/movies/inception-2010"

print("🔍 Analyzing YTS page structure...\n")

soup = scraper._make_request(test_url)
if not soup:
    print("❌ Failed to load page")
    exit(1)

# Check quality sections
quality_sections = soup.select('p.quality-size')
print(f"Found {len(quality_sections)} quality sections\n")

if quality_sections:
    # Analyze first section structure
    section = quality_sections[0]
    print("First quality section HTML:")
    print("=" * 60)
    print(section.prettify()[:500])
    print("=" * 60)
    
    # Try to find quality and size within section
    print("\n🔍 Looking for quality within section...")
    
    # Try different selectors
    quality_options = [
        ('span.quality-tag', section.select('span.quality-tag')),
        ('.quality-tag', section.select('.quality-tag')),
        ('span', section.select('span')),
        ('a', section.select('a')),
    ]
    
    for selector, results in quality_options:
        if results:
            print(f"  ✓ '{selector}': {len(results)} found")
            if results:
                print(f"    First: {results[0].text.strip()[:30]}")
        else:
            print(f"  ✗ '{selector}': 0 found")
    
    print("\n🔍 Looking for size within section...")
    size_options = [
        ('span.quality-size', section.select('span.quality-size')),
        ('.quality-size', section.select('.quality-size')),
        ('span', section.select('span')),
    ]
    
    for selector, results in size_options:
        if results:
            print(f"  ✓ '{selector}': {len(results)} found")
            if len(results) > 1:
                print(f"    Second: {results[1].text.strip()[:30]}")
        else:
            print(f"  ✗ '{selector}': 0 found")

# Check for magnet and torrent links
print("\n🔍 Checking download links...")
magnets = soup.select('a[href^="magnet:"]')
print(f"  Magnet links: {len(magnets)}")
if magnets:
    print(f"    Example: {magnets[0].get('href', '')[:80]}...")

torrents = soup.select('a.download-torrent')
print(f"  Torrent links (.download-torrent): {len(torrents)}")
if torrents:
    print(f"    Example: {torrents[0].get('href', '')[:80]}...")

# Try alternative torrent selectors
alt_torrents = soup.select('a[href*="/torrent/download/"]')
print(f"  Torrent links (href*='/torrent/download/'): {len(alt_torrents)}")
if alt_torrents:
    print(f"    Example: {alt_torrents[0].get('href', '')[:80]}...")
