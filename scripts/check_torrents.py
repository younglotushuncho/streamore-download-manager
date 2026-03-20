import sqlite3, json

conn = sqlite3.connect('data/movies.db')
cursor = conn.cursor()

cursor.execute('SELECT id, title, torrents FROM movies LIMIT 10')
rows = cursor.fetchall()

print("Sample movies:")
for r in rows:
    torrents_str = r[2][:80] + "..." if r[2] and len(r[2]) > 80 else r[2] or "NULL"
    print(f"  {r[0]}: {r[1]}")
    print(f"    Torrents: {torrents_str}")
    
    # Parse if not null
    if r[2]:
        try:
            torrents = json.loads(r[2])
            if torrents:
                print(f"    First torrent keys: {list(torrents[0].keys())}")
                print(f"    First torrent: {torrents[0]}")
        except:
            pass
    print()

conn.close()
