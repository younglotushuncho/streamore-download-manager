import sqlite3
from pathlib import Path
import shutil
import time
import glob

# Titles to remove
EXCLUDE_TITLES = [
    "DuckTales the Movie: Treasure of the Lost Lamp",
    "The Rip",
    "Rip Up the Road",
]

# Candidate DB locations relative to project
CANDIDATES = [
    Path("data/movies.db"),
    Path("backend/movies.db"),
    Path("backend/data/movies.db"),
    Path("movies.db"),
]

ROOT = Path(__file__).parent


def find_db():
    # check explicit candidates
    for p in CANDIDATES:
        full = (ROOT / p).resolve()
        if full.exists():
            return full
    # fallback: search for any .db file in repo
    hits = list(ROOT.rglob("*.db"))
    if hits:
        # pick the largest file (likely the main DB)
        hits.sort(key=lambda p: p.stat().st_size, reverse=True)
        return hits[0]
    return None


def find_movie_table(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    # prefer table with 'movie' in name
    for t in tables:
        if 'movie' in t.lower():
            return t
    return tables[0] if tables else None


def backup_db(db_path: Path) -> Path:
    ts = time.strftime('%Y%m%d-%H%M%S')
    bak = db_path.with_suffix(db_path.suffix + f'.bak-{ts}')
    shutil.copy2(db_path, bak)
    return bak


def remove_titles(db_path: Path):
    print(f"Using DB: {db_path}")
    bak = backup_db(db_path)
    print(f"Backup created: {bak}")
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    table = find_movie_table(conn)
    if not table:
        print("No tables found in DB.")
        return
    # check columns
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1].lower() for r in cur.fetchall()]
    if 'title' not in cols:
        print(f"No 'title' column in table {table}. Columns: {cols}")
        return

    # Count matching rows
    placeholders = ','.join('?' for _ in EXCLUDE_TITLES)
    cur.execute(f"SELECT id, title FROM {table} WHERE title IN ({placeholders})", EXCLUDE_TITLES)
    rows = cur.fetchall()
    if not rows:
        print("No matching titles found. Nothing to delete.")
        return

    print(f"Found {len(rows)} matching rows to delete:")
    for r in rows:
        print(f"  - {r[1]} (id={r[0]})")

    confirm = input('Proceed to delete these rows from DB? [y/N]: ').strip().lower()
    if confirm != 'y':
        print('Aborted by user. No changes made.')
        return

    cur.execute(f"DELETE FROM {table} WHERE title IN ({placeholders})", EXCLUDE_TITLES)
    conn.commit()
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE title IN ({placeholders})", EXCLUDE_TITLES)
    remaining = cur.fetchone()[0]
    print(f"Deleted {len(rows) - remaining} rows. Remaining matches: {remaining}")
    conn.close()


if __name__ == '__main__':
    db = find_db()
    if not db:
        print('No .db file found in repository. If your DB is elsewhere, edit this script to point to it.')
    else:
        remove_titles(db)
