"""Test fetching torrents for first movie using the API endpoint"""
import requests

# Get first movie
r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 1})
movie = r.json()['movies'][0]

print(f"🎬 Testing fetch-torrents for: {movie['title']}")
print(f"   ID: {movie['id']}")
print(f"   Current torrents: {len(movie.get('torrents', []))}")

# Fetch torrents
r2 = requests.post(f"http://127.0.0.1:5000/api/movie/{movie['id']}/fetch-torrents")
result = r2.json()

print(f"\n✅ API Response:")
print(f"   Success: {result.get('success')}")
print(f"   Torrents found: {len(result.get('torrents', []))}")

if result.get('torrents'):
    for t in result['torrents']:
        print(f"   - {t['quality']} ({t['size']})")
