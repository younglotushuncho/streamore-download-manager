from pathlib import Path
import sqlite3

p = Path('backend/movies.db')
print('DB path:', p.resolve())
print('Exists:', p.exists())
if p.exists():
    print('Size bytes:', p.stat().st_size)
    with p.open('rb') as f:
        hdr = f.read(100)
    print('Header (first 100 bytes):', hdr[:16])
    try:
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT name, type FROM sqlite_master WHERE type in ('table','index','view')")
        rows = cur.fetchall()
        print('sqlite_master entries:')
        for r in rows:
            print('  ', r)
        conn.close()
    except Exception as e:
        print('Error opening DB with sqlite3:', e)
