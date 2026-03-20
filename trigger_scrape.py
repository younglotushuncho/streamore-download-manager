import requests
import json

print("Triggering YTS scrape...")
print("This will scrape page 1 of YTS movies\n")

response = requests.post(
    'http://127.0.0.1:5000/api/scrape',
    json={
        'page': 1,
        'genre': 'all',
        'quality': 'all',
        'year': 'all',
        'fetch_details': False
    }
)

print(f"Status: {response.status_code}")
result = response.json()
print(json.dumps(result, indent=2))

if result.get('success'):
    print(f"\n✓ Scrape successful!")
    print(f"  Found: {result.get('found')} movies")
    print(f"  Saved: {result.get('saved')} movies")
else:
    print(f"\n✗ Scrape failed: {result.get('error')}")
