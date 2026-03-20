import requests
import json

url = 'http://127.0.0.1:5000/api/movies'
try:
    r = requests.get(url, params={'limit': 200}, timeout=10)
    print('HTTP', r.status_code)
    data = r.json()
    print('Total movies in DB:', data.get('count'))
    print('\nFirst 40 titles:')
    for i, m in enumerate(data.get('movies', [])[:40], 1):
        print(f"{i:2d}. {m.get('title')}")
except Exception as e:
    print('ERROR:', e)
