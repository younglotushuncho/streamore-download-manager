import sqlite3
p='backend/movies.db'
conn=sqlite3.connect(p)
cur=conn.cursor()
cur.execute("SELECT name, type FROM sqlite_master WHERE type in ('table','index','view')")
rows=cur.fetchall()
print('sqlite_master entries:')
for r in rows:
    print(r[0], r[1])
conn.close()
