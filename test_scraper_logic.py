"""
Test what the scraper extracts from real YTS HTML
Since we can see the correct link in browser DevTools, let's simulate that HTML
"""
from bs4 import BeautifulSoup

# Simulated HTML based on what you showed in DevTools
html = '''
<div class="modal-torrent">
    <div class="modal-quality">
        <span>720p</span>
    </div>
    <p>File size</p>
    <p>800 MB</p>
    <a href="https://yts.bz/torrent/download/5826DC2904F26EAFC7E29F2931122B436E41BCB6" 
       rel="nofollow" 
       title="Download Super Shark 720p.BluRay Torrent" 
       class="download-torrent">
        Download
    </a>
    <a href="magnet:?xt=urn:btih:5826DC2904F26EAFC7E29F2931122B436E41BCB6&dn=Super+Shark" class="magnet-link">
        Magnet
    </a>
</div>
'''

soup = BeautifulSoup(html, 'html.parser')

# Test current scraper logic
modal = soup.select_one('div.modal-torrent')
if modal:
    print("✓ Found modal-torrent div")
    
    # Quality
    quality_elem = modal.select_one('div.modal-quality span')
    quality = quality_elem.text.strip() if quality_elem else 'N/A'
    print(f"Quality: {quality}")
    
    # Torrent URL
    torrent_elem = modal.select_one('a.download-torrent')
    if torrent_elem:
        torrent_url = torrent_elem.get('href', '')
        print(f"Torrent URL: {torrent_url}")
        print(f"Hash length: {len(torrent_url.split('/')[-1])}")
        print(f"Hash: {torrent_url.split('/')[-1]}")
    else:
        print("❌ No download-torrent link found")
        
    # Try alternate selector
    all_links = modal.select('a[href*="torrent/download"]')
    print(f"\nAll torrent download links: {len(all_links)}")
    for link in all_links:
        href = link.get('href', '')
        print(f"  - {href}")
else:
    print("❌ No modal-torrent div found")
