"""Remove specific downloads by GID using backend API and DB delete."""
import requests
import sqlite3

API = 'http://127.0.0.1:5000'

# List current downloads
r = requests.get(f"{API}/api/downloads")
if r.status_code != 200:
    print('Failed to list downloads:', r.status_code, r.text)
    exit(1)

data = r.json()
for d in data.get('downloads', []):
    gid = d['id']
    title = d.get('movie_title')
    print(f'Removing {gid} - {title}')
    try:
        rc = requests.post(f"{API}/api/download/{gid}/cancel", timeout=5)
        print('  cancel response:', rc.status_code, rc.text[:200])
    except Exception as e:
        print('  cancel failed:', e)

# Cleanup DB entries regardless
conn = sqlite3.connect('data/movies.db')
cur = conn.cursor()
cur.execute("DELETE FROM downloads")
conn.commit()
conn.close()
print('DB downloads table cleared.')
