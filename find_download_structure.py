"""Find the correct container for quality+size+links"""
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.scraper import YTSScraper

scraper = YTSScraper()
test_url = "https://www.yts-official.top/movies/inception-2010"

soup = scraper._make_request(test_url)
if not soup:
    print("❌ Failed")
    exit(1)

print("🔍 Finding download container structure...\n")

# The torrent links should tell us the structure
torrent_links = soup.select('a.download-torrent')
if torrent_links:
    first_link = torrent_links[0]
    print("First torrent link:")
    print(f"  Href: {first_link.get('href', '')}")
    print(f"  Text: {first_link.text.strip()}")
    
    # Check parent structure
    print("\n📦 Parent chain:")
    parent = first_link.parent
    level = 0
    while parent and level < 5:
        tag = parent.name
        classes = ' '.join(parent.get('class', []))
        print(f"  Level {level}: <{tag} class='{classes}'>")
        
        # Show siblings at this level
        if level == 1:
            print(f"    Siblings: {len(list(parent.children))} elements")
            for i, sibling in enumerate(list(parent.children)):
                if hasattr(sibling, 'name'):
                    sib_class = ' '.join(sibling.get('class', []))
                    sib_text = sibling.text.strip()[:40]
                    print(f"      [{i}] <{sibling.name} class='{sib_class}'> {sib_text}")
        
        parent = parent.parent
        level += 1

# Now find magnet links
print("\n\n🔍 Magnet links structure...")
magnet_links = soup.select('a[href^="magnet:"]')
if magnet_links:
    first_magnet = magnet_links[0]
    print(f"First magnet href: {first_magnet.get('href', '')[:80]}...")
    print(f"Text: '{first_magnet.text.strip()}'")
    
    parent = first_magnet.parent
    print(f"\nParent: <{parent.name} class='{' '.join(parent.get('class', []))}'>")
    print(f"Siblings: {len(list(parent.children))}")
