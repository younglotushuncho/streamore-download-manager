import sqlite3
from pathlib import Path
p = Path(r"e:\Softwares\projects\movie project\data\movies.db")
print('path', p)
print('exists', p.exists())
print('size', p.stat().st_size)
conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','index')")
for r in cur.fetchall():
    print(r)

# show first 5 rows from movies-like table if exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%movie%'")
row = cur.fetchone()
if row:
    tbl = row[0]
    print('table', tbl)
    cur.execute(f"PRAGMA table_info({tbl})")
    print('columns:', cur.fetchall())
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    print('count', cur.fetchone()[0])
    cur.execute(f"SELECT title FROM {tbl} LIMIT 10")
    for r in cur.fetchall():
        print('title:', r[0])
else:
    print('no movie-like table found')
conn.close()
