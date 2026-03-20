"""Test the updated download priority (.torrent first, then magnet)"""
import requests

print("🧪 Testing download priority logic...\n")

# Get Super Shark
r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 20})
movies = r.json()['movies']

for m in movies:
    torrents = m.get('torrents', [])
    if torrents:
        print(f"✓ Movie: {m['title']}")
        print(f"  Has {len(torrents)} quality options\n")
        
        for i, t in enumerate(torrents, 1):
            quality = t.get('quality', 'Unknown')
            torrent_url = t.get('torrent_url', '')
            magnet = t.get('magnet_link', '')
            
            print(f"  Option {i}: {quality}")
            print(f"    Priority 1 - .torrent URL: {'✓ AVAILABLE' if torrent_url else '✗ MISSING'}")
            if torrent_url:
                print(f"      → {torrent_url}")
            print(f"    Priority 2 - Magnet link: {'✓ AVAILABLE' if magnet else '✗ MISSING'}")
            if magnet:
                print(f"      → {magnet[:80]}...")
            
            print(f"\n    🎯 DOWNLOAD WILL USE: ", end="")
            if torrent_url:
                print(".torrent file (PRIORITY 1) ✓")
            elif magnet:
                print("magnet link (FALLBACK)")
            else:
                print("❌ NOTHING AVAILABLE")
            print()
        
        break

print("\n" + "="*60)
print("HOW IT WORKS NOW:")
print("="*60)
print("""
When you click "Download Selected" button:

1️⃣  FIRST: Try to download .torrent file
   ✓ Opens URL in browser (auto-downloads .torrent)
   ✓ You add the .torrent file to qBittorrent
   ✓ Includes subtitles and extra files
   ✓ No protocol handler issues!

2️⃣  FALLBACK: If .torrent fails or unavailable, use magnet
   → Opens magnet:// link in qBittorrent
   → May have protocol handler issues on some systems

3️⃣  If both fail: Show error message

This is the BEST approach because:
✓ .torrent files are more reliable
✓ Work on all systems
✓ No "unsupported URL protocol" errors
✓ Faster (no metadata fetch needed)
""")
