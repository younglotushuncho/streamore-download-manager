"""Scrape a popular recent movie that should have torrents"""
import requests
import time

# Scrape page 1 to get fresh popular movies WITH details (torrents)
print("🔄 Scraping YTS for popular movies with torrents...")
print("This will take a moment...\n")

r = requests.post('http://127.0.0.1:5000/api/scrape', json={
    'page': 1,
    'fetch_details': True,  # Important: fetch full details including torrents
    'sort_by': 'download_count'
})

result = r.json()
if result.get('success'):
    print(f"✅ Scrape complete!")
    print(f"   Found: {result.get('found')} movies")
    print(f"   Saved: {result.get('saved')} movies")
    
    # Check if any have torrents now
    print("\n🔍 Checking for torrents...")
    r2 = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 10})
    movies = r2.json()['movies']
    
    count_with_torrents = 0
    for m in movies:
        tc = len(m.get('torrents', []))
        if tc > 0:
            count_with_torrents += 1
            print(f"✓ {m['title'][:40]:40} - {tc} torrents")
    
    if count_with_torrents > 0:
        print(f"\n✅ SUCCESS! {count_with_torrents} movies now have torrents!")
        print("👉 Try clicking these movies in the frontend")
    else:
        print("\n⚠️  Movies scraped but no torrents found")
        print("💡 This can happen if YTS has removed torrents")
        print("💡 Try the 🔄 Refresh button in the dialog for live fetching")
else:
    print(f"❌ Scrape failed: {result.get('error')}")
