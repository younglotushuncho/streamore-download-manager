"""Test downloading a real movie from the database"""
import requests
import sqlite3
import json

# Get a real movie from database
conn = sqlite3.connect('data/movies.db')
cursor = conn.cursor()

# Get a movie with torrents
cursor.execute('''
    SELECT id, title, torrents
    FROM movies
    WHERE torrents IS NOT NULL AND torrents != '[]'
    LIMIT 1
''')

result = cursor.fetchone()
conn.close()

if not result:
    print("❌ No movies with torrents found in database")
    exit(1)

movie_id, title, torrents_json = result

# Parse torrents JSON
torrents = json.loads(torrents_json)
if not torrents:
    print("❌ No torrents available for this movie")
    exit(1)

# Get first torrent
torrent = torrents[0]
quality = torrent['quality']
torrent_hash = torrent['hash']

print(f"Found movie: {title} ({quality})")
print(f"Movie ID: {movie_id}")
print(f"Torrent hash: {torrent_hash}")

# Create magnet link
magnet_link = f"magnet:?xt=urn:btih:{torrent_hash}&dn={title.replace(' ', '+')}"
print(f"\nMagnet link: {magnet_link[:80]}...")

# Send download request to backend
print("\nSending download request to backend...")
response = requests.post(
    'http://127.0.0.1:5000/api/download/start',
    json={
        'movie_id': movie_id,
        'movie_title': title,
        'quality': quality,
        'magnet_link': magnet_link
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    print("\n✓ SUCCESS! Download started")
    print(f"Download ID (GID): {response.json().get('download_id')}")
else:
    print(f"\n✗ FAILED: {response.json().get('error', 'Unknown error')}")
