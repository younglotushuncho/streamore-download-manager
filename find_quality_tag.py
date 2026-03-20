"""Find where quality resolution (1080p, 720p, etc) is located"""
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

print("🔍 Looking for quality tags (1080p, 720p, etc.)...\n")

modals = soup.select('div.modal-torrent')

for i, modal in enumerate(modals[:3]):
    print(f"=== MODAL {i+1} ===")
    
    # Look for all elements with class
    for elem in modal.find_all(True):  # All tags
        if elem.name in ['a', 'span', 'div', 'p']:
            text = elem.get_text(strip=True)
            classes = elem.get('class', [])
            
            # Check if contains resolution
            if any(res in text for res in ['1080p', '720p', '2160p', '480p']):
                print(f"  Found '{text}' in <{elem.name}> with classes: {classes}")
    
    print()
