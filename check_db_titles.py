import requests
import json

r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 100})
data = r.json()
print(f"Total movies in DB: {data.get('count')}")
print("\nAll movie titles:")
for m in data.get('movies', []):
    print(f"  - {m.get('title')}")
