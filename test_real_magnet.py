"""Test getting a real magnet link from the database and validate its format"""
import requests
import re

print("🔍 Testing real magnet link from database...\n")

# Get Super Shark (has torrents)
r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 20})
movies = r.json()['movies']

# Find a movie with torrents
movie_with_torrents = None
for m in movies:
    if m.get('torrents') and len(m['torrents']) > 0:
        movie_with_torrents = m
        break

if not movie_with_torrents:
    print("❌ No movies with torrents found in database")
    exit(1)

print(f"✓ Found movie: {movie_with_torrents['title']}")
print(f"  Torrents: {len(movie_with_torrents['torrents'])}\n")

for i, torrent in enumerate(movie_with_torrents['torrents'], 1):
    quality = torrent.get('quality', 'Unknown')
    size = torrent.get('size', 'Unknown')
    magnet = torrent.get('magnet_link', '')
    
    print(f"--- Torrent {i}: {quality} ({size}) ---")
    print(f"Magnet length: {len(magnet)} chars")
    
    if not magnet:
        print("❌ Empty magnet link!\n")
        continue
    
    # Show first 120 chars
    print(f"Preview: {magnet[:120]}...")
    
    # Validate format
    if not magnet.startswith('magnet:'):
        print("❌ Does not start with 'magnet:'\n")
        continue
    
    # Check for info-hash
    btih_match = re.search(r'xt=urn:btih:([A-Fa-f0-9]{40})', magnet)
    if not btih_match:
        print("❌ No valid info-hash found (expected 40 hex chars)")
        print(f"   Looking for pattern: xt=urn:btih:[40 hex digits]\n")
        continue
    
    info_hash = btih_match.group(1)
    print(f"✓ Valid info-hash: {info_hash}")
    
    # Check for display name
    if '&dn=' in magnet:
        print("✓ Has display name (&dn=)")
    else:
        print("⚠️  No display name (&dn=) - optional but recommended")
    
    # Check for trackers
    tracker_count = magnet.count('&tr=')
    if tracker_count > 0:
        print(f"✓ Has {tracker_count} tracker(s)")
    else:
        print("⚠️  No trackers (&tr=) - may affect connectivity")
    
    print(f"\n✅ Magnet is VALID and ready for qBittorrent\n")
    print("=" * 60)
    print("FULL MAGNET (copy this to test manually):")
    print(magnet)
    print("=" * 60)
    break  # Only show first valid one
