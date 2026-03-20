from pathlib import Path
p = Path('data/movies.db')
print('Path:', p.resolve())
print('Exists:', p.exists())
if p.exists():
    print('Size:', p.stat().st_size)
    import sqlite3
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    cur.execute("SELECT name, type FROM sqlite_master WHERE type in ('table','index','view')")
    rows = cur.fetchall()
    print('sqlite_master entries:')
    for r in rows:
        print('  ', r)
    for r in rows:
        if 'movie' in r[0].lower():
            print('\nSample rows from', r[0])
            cur.execute(f"SELECT id, title FROM {r[0]} LIMIT 10")
            for rr in cur.fetchall():
                print('   ', rr)
    conn.close()
else:
    print('data/movies.db not found')
