"""
Test to see what torrent URLs the scraper extracts vs what YTS "Copy Link" gives
"""
from backend.scraper import YTSScraper
from curl_cffi import requests
from bs4 import BeautifulSoup

# Initialize scraper
scraper = YTSScraper()

# Test with a known movie (Super Shark)
movie_url = "https://yts.bz/movies/super-shark-2011"

print(f"Testing: {movie_url}")
print("=" * 80)

# Get the page
response = scraper._make_request(movie_url)
if not response:
    print("Failed to fetch page")
    exit(1)

soup = BeautifulSoup(response.text, 'html.parser')

# Extract torrents using the scraper method
torrents = scraper._extract_torrents(soup)

print(f"\nTorrents extracted by scraper ({len(torrents)}):")
print("-" * 80)
for t in torrents:
    print(f"Quality: {t['quality']}")
    print(f"Size: {t['size']}")
    print(f"Torrent URL: {t['torrent_url']}")
    print(f"Magnet (first 80 chars): {t['magnet_link'][:80]}...")
    print()

# Now let's manually check what's in the HTML
print("\nManual HTML inspection:")
print("-" * 80)

# Look for all download-torrent links
download_links = soup.select('a.download-torrent')
print(f"Found {len(download_links)} a.download-torrent elements")
for i, link in enumerate(download_links):
    href = link.get('href', '')
    print(f"{i+1}. href='{href}'")
    # Check parent to see quality context
    parent_text = link.parent.get_text(strip=True) if link.parent else 'N/A'
    print(f"   Parent text: {parent_text[:100]}")
    print()

# Check if there are any data attributes or JS-generated links
print("\nChecking for data-* attributes or onclick handlers:")
print("-" * 80)
torrent_buttons = soup.select('a[href*="torrent"]')
for i, btn in enumerate(torrent_buttons[:5]):  # First 5 only
    print(f"{i+1}. {btn.get('class', [])} - href='{btn.get('href', '')[:100]}'")
    for attr in btn.attrs:
        if attr.startswith('data-') or attr == 'onclick':
            print(f"   {attr}='{btn.get(attr, '')[:100]}'")
    print()
