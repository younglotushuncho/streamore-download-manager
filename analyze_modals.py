"""Analyze modal-torrent structure"""
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

scraper = YTSScraper()
test_url = "https://www.yts-official.top/movies/inception-2010"

soup = scraper._make_request(test_url)
if not soup:
    exit(1)

print("🔍 Analyzing modal-torrent divs...\n")

modals = soup.select('div.modal-torrent')
print(f"Found {len(modals)} modal-torrent divs\n")

for i, modal in enumerate(modals[:3]):  # Check first 3
    print(f"=== MODAL {i+1} ===")
    
    # Try to find quality
    quality_p = modal.select_one('p.quality-size')
    if quality_p:
        quality_text = quality_p.text.strip()
        print(f"  Quality indicator: '{quality_text}'")
    
    # Look for actual quality/size text
    all_text = modal.get_text(strip=True)
    print(f"  All text: {all_text[:100]}")
    
    # Check for magnet link
    magnet = modal.select_one('a[href^="magnet:"]')
    if magnet:
        magnet_href = magnet.get('href', '')
        print(f"  ✓ Magnet: {magnet_href[:60]}...")
    else:
        print(f"  ✗ No magnet")
    
    # Check for torrent download
    torrent = modal.select_one('a.download-torrent')
    if torrent:
        torrent_href = torrent.get('href', '')
        print(f"  ✓ Torrent: {torrent_href}")
    else:
        print(f"  ✗ No torrent")
    
    print()

# Try to extract quality and size from the modal text or title
print("\n🎯 Trying to extract quality/size from modal...")
for i, modal in enumerate(modals[:2]):
    print(f"\n--- Modal {i+1} ---")
    
    # Check if there's an ID or data attribute
    modal_id = modal.get('id', '')
    print(f"  ID: {modal_id}")
    
    # Look for headings
    h4 = modal.select_one('h4')
    if h4:
        print(f"  H4: {h4.text.strip()}")
    
    h3 = modal.select_one('h3')
    if h3:
        print(f"  H3: {h3.text.strip()}")
    
    # Look for any text that looks like quality/size
    all_p = modal.select('p')
    print(f"  Found {len(all_p)} <p> tags:")
    for p in all_p:
        text = p.text.strip()
        if text:
            print(f"    - {text[:50]}")
