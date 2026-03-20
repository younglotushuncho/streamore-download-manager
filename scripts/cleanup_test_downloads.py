"""Remove known test downloads from database and aria2.
This script will:
 - Look for downloads whose movie_title contains 'Test' or 'Auto Test'
 - Call backend API to cancel/remove the download by GID
 - Remove the rows from the downloads table
"""
import sqlite3
import requests

API = 'http://127.0.0.1:5000'

conn = sqlite3.connect('data/movies.db')
cur = conn.cursor()

cur.execute("SELECT id, movie_title FROM downloads")
rows = cur.fetchall()

candidates = [r for r in rows if ('test' in r[1].lower()) or ('auto test' in r[1].lower())]

if not candidates:
    print('No test downloads found to remove.')
    conn.close()
    exit(0)

print('Found test downloads:')
for gid, title in candidates:
    print(f'  - {gid} : {title}')

for gid, title in candidates:
    try:
        print(f'Cancelling via backend: {gid}')
        r = requests.post(f"{API}/api/download/{gid}/cancel", timeout=5)
        print('  backend response:', r.status_code, r.text[:200])
    except Exception as e:
        print('  backend cancel failed:', e)

    try:
        print(f'Removing from DB: {gid}')
        cur.execute("DELETE FROM downloads WHERE id = ?", (gid,))
    except Exception as e:
        print('  DB delete failed:', e)

conn.commit()
conn.close()
print('Done.')
