import sqlite3

conn = sqlite3.connect('data/movies.db')
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check movies table schema
print("\nMovies table schema:")
cursor.execute("PRAGMA table_info(movies)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
