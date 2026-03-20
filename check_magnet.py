import sqlite3

conn = sqlite3.connect('backend/movies.db')
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables:", tables)

# Check movie_torrents table
cursor.execute("SELECT movie_id, quality, magnet_link FROM movie_torrents WHERE movie_id='dfb4a60e1b4b'")
rows = cursor.fetchall()

for row in rows:
    movie_id, quality, magnet = row
    print(f"\n{quality}:")
    print(f"Magnet length: {len(magnet)}")
    print(f"First 100 chars: {magnet[:100]}")
    print(f"Last 100 chars: {magnet[-100:]}")
    
    # Check if it's a valid magnet
    if magnet.startswith('magnet:?xt=urn:btih:'):
        info_hash = magnet.split('magnet:?xt=urn:btih:')[1].split('&')[0]
        print(f"Info-hash: {info_hash}")
        print(f"Info-hash length: {len(info_hash)}")
    else:
        print("WARNING: Doesn't start with proper magnet format!")

conn.close()
