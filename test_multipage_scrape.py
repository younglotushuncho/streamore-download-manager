import requests
import json

# Test multi-page scraping for Animation/720p/2024
url = 'http://127.0.0.1:5000/api/browse/scrape'
params = {
    'keyword': '',
    'quality': '720p',
    'genre': 'animation',
    'rating': 0,
    'year': '2024',
    'order_by': 'latest',
    'page': 1,
    'max_pages': 6  # Try to scrape 6 pages
}

print(f"Testing multi-page browse/scrape:")
print(f"  Genre: {params['genre']}")
print(f"  Quality: {params['quality']}")
print(f"  Year: {params['year']}")
print(f"  Max pages: {params['max_pages']}")
print()
print("This may take 30-60 seconds due to rate limiting...")
print()

try:
    r = requests.get(url, params=params, timeout=120)
    print(f"HTTP {r.status_code}")
    data = r.json()
    
    if data.get('success'):
        count = data.get('count', 0)
        movies = data.get('movies', [])
        print(f"✓ Total movies scraped: {count}")
        print(f"\nFirst 15 titles:")
        for i, m in enumerate(movies[:15], 1):
            print(f"{i:2d}. {m.get('title')} ({m.get('year')}) - {m.get('rating')}/10")
        
        if count > 15:
            print(f"... and {count - 15} more movies")
    else:
        print(f"✗ Error: {data.get('error')}")
        
except Exception as e:
    print(f"✗ Request failed: {e}")
