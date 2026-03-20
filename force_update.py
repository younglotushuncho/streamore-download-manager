"""Force update Super Shark torrents via API"""
import requests

# Get Super Shark
r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 1})
movie = r.json()['movies'][0]

print(f"🎬 Movie: {movie['title']} (ID: {movie['id']})")
print(f"   Current torrents: {len(movie.get('torrents', []))}")

# Force fetch
print(f"\n🔄 Fetching torrents from YTS...")
r2 = requests.post(f"http://127.0.0.1:5000/api/movie/{movie['id']}/fetch-torrents")

if r2.status_code == 200:
    result = r2.json()
    print(f"\n✅ API Response:")
    print(f"   Success: {result.get('success')}")
    print(f"   Message: {result.get('message')}")
    print(f"   Torrents: {len(result.get('torrents', []))}")
    
    if result.get('torrents'):
        for t in result['torrents']:
            print(f"     - {t['quality']} ({t['size']})")
else:
    print(f"\n❌ Failed: {r2.status_code}")
    print(r2.text)
