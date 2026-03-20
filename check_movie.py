import requests
import json

# Get a movie
r = requests.get('http://127.0.0.1:5000/api/movie/7a936fe0be17')
data = r.json()
movie = data['movie']

print(f"Title: {movie['title']}")
print(f"Description: {movie['description'][:150] if movie['description'] else 'EMPTY'}...")
print(f"Torrents: {len(movie['torrents'])} found")

if movie['torrents']:
    print("\nTorrent details:")
    for t in movie['torrents']:
        print(f"  - {t['quality']}: {t['size']}")
        print(f"    Magnet: {t['magnet_link'][:60]}...")
