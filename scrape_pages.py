import requests, json

BASE = 'http://127.0.0.1:5000/api/scrape'

for p in range(1, 6):
    print(f"Scraping page {p}...")
    try:
        r = requests.post(BASE, json={
            'page': p,
            'genre': 'all',
            'quality': 'all',
            'year': 'all',
            'fetch_details': False
        }, timeout=30)
        j = r.json()
        print(f"  Status: {r.status_code} — found={j.get('found')} saved={j.get('saved')}")
    except Exception as e:
        print(f"  Error scraping page {p}: {e}")

print('\nDone scraping pages 1-5')
