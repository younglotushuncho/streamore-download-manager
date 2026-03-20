"""Analyze .torrent file structure and check what URLs we're storing"""
import requests

print("🔍 Checking stored torrent URLs in database...\n")

# Get Super Shark which has torrents
r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 20})
movies = r.json()['movies']

for m in movies:
    torrents = m.get('torrents', [])
    if torrents:
        print(f"Movie: {m['title']}")
        for t in torrents:
            quality = t.get('quality', 'Unknown')
            magnet = t.get('magnet_link', '')
            torrent_url = t.get('torrent_url', '')
            
            print(f"  {quality}:")
            print(f"    Magnet: {magnet[:60] if magnet else 'NONE'}...")
            print(f"    Torrent URL: {torrent_url}")
        print()
        break  # Just show first movie with torrents

print("\n" + "="*60)
print("ANALYSIS:")
print("="*60)
print("""
The .torrent file you downloaded contains:
- Movie file: We.Bury.The.Dead.2024.720p.WEBRip.x264.AAC-[YTS.BZ].mp4 (914 MB)
- Subtitle: .srt file
- Extra files: YTS.BZ logo, readme

When you click "Download Selected" button, the app should:
1. FIRST try to download the .torrent file (direct download)
2. FALLBACK to magnet if .torrent URL is not available

The .torrent file download is BETTER because:
✓ Faster to add to qBittorrent (no need to fetch metadata)
✓ No protocol handler issues
✓ Can include extra files (subtitles, etc.)
✓ More reliable than magnet links

Current behavior needs to be changed to prioritize .torrent downloads.
""")
