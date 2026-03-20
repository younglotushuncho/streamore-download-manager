import requests
import json

# Test the new browse/scrape endpoint with filters matching the YTS URL pattern
# https://www.yts-official.top/browse-movies?keyword=&quality=720p&genre=action&rating=0&year=2024&order_by=latest

url = 'http://127.0.0.1:5000/api/browse/scrape'
params = {
    'keyword': '',
    'quality': '720p',
    'genre': 'action',
    'rating': 0,
    'year': '2024',
    'order_by': 'latest',
    'page': 1
}

print(f"Testing browse/scrape endpoint with filters:")
print(f"  Genre: {params['genre']}")
print(f"  Quality: {params['quality']}")
print(f"  Year: {params['year']}")
print()

try:
    r = requests.get(url, params=params, timeout=30)
    print(f"HTTP {r.status_code}")
    data = r.json()
    
    if data.get('success'):
        count = data.get('count', 0)
        movies = data.get('movies', [])
        print(f"✓ Found {count} movies")
        print(f"\nFirst 10 titles:")
        for i, m in enumerate(movies[:10], 1):
            print(f"{i:2d}. {m.get('title')} ({m.get('year')}) - {m.get('rating')}/10")
    else:
        print(f"✗ Error: {data.get('error')}")
        
except Exception as e:
    print(f"✗ Request failed: {e}")
