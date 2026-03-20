"""
SQLite database module for YTS Movie Monitor
"""
import sqlite3
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

from backend.config import Config
from shared.models import Movie, Torrent, Download

logger = logging.getLogger(__name__)


class Database:
    """SQLite database wrapper"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Movies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    year TEXT,
                    rating REAL,
                    genres TEXT,
                    description TEXT,
                    poster_url TEXT,
                    poster_local TEXT,
                    yts_url TEXT,
                    scraped_at TEXT,
                    torrents TEXT
                )
            ''')
            
            # Downloads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    id TEXT PRIMARY KEY,
                    movie_id TEXT,
                    movie_title TEXT,
                    quality TEXT,
                    magnet_link TEXT,
                    state TEXT,
                    progress REAL,
                    download_rate REAL,
                    upload_rate REAL,
                    eta INTEGER,
                    size_total INTEGER,
                    size_downloaded INTEGER,
                    num_peers INTEGER,
                    num_seeds INTEGER,
                    save_path TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    FOREIGN KEY (movie_id) REFERENCES movies (id)
                )
            ''')
            
            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Scrape history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scrape_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scraped_at TEXT,
                    movies_found INTEGER,
                    success BOOLEAN
                )
            ''')
            
            # Download history (persistent record even after removal)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS download_history (
                    id TEXT PRIMARY KEY,
                    movie_id TEXT,
                    movie_title TEXT,
                    quality TEXT,
                    size_total INTEGER,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT  -- 'completed', 'cancelled', 'error'
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies(rating DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_state ON downloads(state)')
            
            # Watchlist table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS watchlist (
                    movie_id TEXT PRIMARY KEY,
                    added_at TEXT,
                    FOREIGN KEY (movie_id) REFERENCES movies (id)
                )
            ''')

            # Speed history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS speed_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gid TEXT NOT NULL,
                    speed REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_speed_history_gid ON speed_history(gid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_speed_history_time ON speed_history(timestamp)')

            # Global Bandwidth Tracking (Aggregate per day)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_bandwidth (
                    date TEXT PRIMARY KEY,
                    bytes_downloaded INTEGER DEFAULT 0
                )
            ''')
            
            logger.info(f"Database initialized at {self.db_path}")
    
    # Movie operations
    def add_movie(self, movie: Movie):
        """Add or update a movie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO movies 
                (id, title, year, rating, genres, description, poster_url, 
                 poster_local, yts_url, scraped_at, torrents)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                movie.id,
                movie.title,
                movie.year,
                movie.rating,
                json.dumps(movie.genres),
                movie.description,
                movie.poster_url,
                movie.poster_local,
                movie.yts_url,
                movie.scraped_at,
                json.dumps([t.to_dict() for t in movie.torrents])
            ))
            logger.debug(f"Added/updated movie: {movie.title}")
    
    def get_movie(self, movie_id: str) -> Optional[Movie]:
        """Get a movie by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM movies WHERE id = ?', (movie_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_movie(row)
            return None
    
    def get_all_movies(self, 
                       genre: str = None, 
                       year: str = None, 
                       quality: str = None,
                       min_rating: float = 0.0,
                       sort_by: str = 'scraped_at',
                       limit: int = 100,
                       offset: int = 0,
                       added_within_days: Optional[int] = None) -> List[Movie]:
        """Get movies with optional filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM movies WHERE rating >= ?'
            params = [min_rating]
            
            if genre and genre != 'All':
                query += ' AND genres LIKE ?'
                params.append(f'%{genre}%')
            
            if year and year != 'All':
                query += ' AND year = ?'
                params.append(year)

            # Optional time-based filter: only include movies scraped within last N days
            if added_within_days is not None:
                try:
                    days = int(added_within_days)
                    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                    query += ' AND scraped_at >= ?'
                    params.append(cutoff)
                except Exception:
                    pass
            
            # Sort
            sort_column = sort_by if sort_by in ['title', 'year', 'rating', 'scraped_at'] else 'scraped_at'

            # When quality filter is active we must fetch all matching rows first
            # (quality is stored as JSON inside the torrents column — can't filter in SQL)
            # then apply quality filter in Python, then honour limit/offset.
            if quality and quality != 'All':
                query += f' ORDER BY {sort_column} DESC'
                cursor.execute(query, params)
                rows = cursor.fetchall()
                movies = [self._row_to_movie(row) for row in rows]
                movies = [m for m in movies if any(t.quality == quality for t in m.torrents)]
                return movies[offset: offset + limit]
            else:
                query += f' ORDER BY {sort_column} DESC LIMIT ? OFFSET ?'
                params.extend([limit, offset])
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [self._row_to_movie(row) for row in rows]
    
    def search_movies(self, query: str, limit: int = 50) -> List[Movie]:
        """Search movies by title - matches YTS behavior (OR-based search)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if not query or not query.strip():
                return []
            
            query = query.strip()
            
            # Tokenize and search for movies containing ANY of the words (OR logic)
            # This matches YTS website behavior
            tokens = [t.strip() for t in query.split() if t.strip()]
            if not tokens:
                return []
            
            # Build OR-based query
            or_clauses = []
            params = []
            for t in tokens:
                or_clauses.append('title LIKE ? COLLATE NOCASE')
                params.append(f'%{t}%')
            
            or_sql = ' OR '.join(or_clauses)
            sql = f"SELECT * FROM movies WHERE ({or_sql}) ORDER BY rating DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_movie(row) for row in rows]
    
    def delete_movie(self, movie_id: str):
        """Delete a movie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM movies WHERE id = ?', (movie_id,))
            logger.debug(f"Deleted movie: {movie_id}")
    
    # Download operations
    def add_download(self, download: Download):
        """Add or update a download"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO downloads
                (id, movie_id, movie_title, quality, magnet_link, state, progress,
                 download_rate, upload_rate, eta, size_total, size_downloaded,
                 num_peers, num_seeds, save_path, started_at, completed_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                download.id,
                download.movie_id,
                download.movie_title,
                download.quality,
                download.magnet_link,
                download.state,
                download.progress,
                download.download_rate,
                download.upload_rate,
                download.eta,
                download.size_total,
                download.size_downloaded,
                download.num_peers,
                download.num_seeds,
                download.save_path,
                download.started_at,
                download.completed_at,
                download.error_message
            ))
    
    def get_download(self, download_id: str) -> Optional[Download]:
        """Get a download by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM downloads WHERE id = ?', (download_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_download(row)
            return None
    
    def get_all_downloads(self, state: str = None) -> List[Download]:
        """Get all downloads, optionally filtered by state"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if state:
                cursor.execute('SELECT * FROM downloads WHERE state = ? ORDER BY started_at DESC', (state,))
            else:
                cursor.execute('SELECT * FROM downloads ORDER BY started_at DESC')
            
            rows = cursor.fetchall()
            return [self._row_to_download(row) for row in rows]
    
    def update_download_progress(self, download_id: str, progress_data: Dict[str, Any]):
        """Update download progress"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            set_clause = ', '.join([f'{k} = ?' for k in progress_data.keys()])
            query = f'UPDATE downloads SET {set_clause} WHERE id = ?'
            params = list(progress_data.values()) + [download_id]
            
            cursor.execute(query, params)
    
    def delete_download(self, download_id: str):
        """Archive to history and then delete from active downloads"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Archive before deletion
            cursor.execute('SELECT * FROM downloads WHERE id = ?', (download_id,))
            row = cursor.fetchone()
            if row:
                result = row['state']
                if result not in ('completed', 'complete', 'error'):
                    result = 'cancelled'
                
                cursor.execute('''
                    INSERT OR REPLACE INTO download_history
                    (id, movie_id, movie_title, quality, size_total, started_at, completed_at, result)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['id'], row['movie_id'], row['movie_title'], row['quality'],
                    row['size_total'], row['started_at'], row['completed_at'] or datetime.now().isoformat(),
                    result
                ))
            
            cursor.execute('DELETE FROM downloads WHERE id = ?', (download_id,))

    def get_download_history(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Get past downloads from the history log"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM download_history ORDER BY started_at DESC LIMIT ?', (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Settings operations
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
    
    def set_setting(self, key: str, value: str):
        """Set a setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
    
    # Scrape history
    def add_scrape_record(self, movies_found: int, success: bool):
        """Add a scrape history record"""
        from datetime import datetime
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scrape_history (scraped_at, movies_found, success)
                VALUES (?, ?, ?)
            ''', (datetime.now().isoformat(), movies_found, success))
    
    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM movies')
            total_movies = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM downloads')
            total_downloads = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM downloads WHERE state = 'completed'")
            completed_downloads = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM downloads WHERE state = 'downloading'")
            active_downloads = cursor.fetchone()['count']
            
            return {
                'total_movies': total_movies,
                'total_downloads': total_downloads,
                'completed_downloads': completed_downloads,
                'active_downloads': active_downloads
            }
    
    # Watchlist operations
    def toggle_watchlist(self, movie_id: str) -> bool:
        """Add to watchlist if not present, else remove. Returns True if now on watchlist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM watchlist WHERE movie_id = ?', (movie_id,))
            if cursor.fetchone():
                cursor.execute('DELETE FROM watchlist WHERE movie_id = ?', (movie_id,))
                return False
            else:
                cursor.execute('INSERT INTO watchlist (movie_id, added_at) VALUES (?, ?)', 
                               (movie_id, datetime.now().isoformat()))
                return True

    def get_watchlist(self) -> List[Movie]:
        """Get all movies currently on the watchlist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.* FROM movies m
                JOIN watchlist w ON m.id = w.movie_id
                ORDER BY w.added_at DESC
            ''')
            rows = cursor.fetchall()
            return [self._row_to_movie(row) for row in rows]

    def is_on_watchlist(self, movie_id: str) -> bool:
        """Check if a specific movie is on the watchlist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM watchlist WHERE movie_id = ?', (movie_id,))
            return bool(cursor.fetchone())

    # Speed history operations
    def add_speed_record(self, gid: str, speed: float):
        """Add a speed record for a download"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO speed_history (gid, speed)
                VALUES (?, ?)
            ''', (gid, speed))
            
    def get_speed_history(self, gid: str, limit: int = 120) -> List[Dict[str, Any]]:
        """Get speed history for a GID (last N records)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT speed, timestamp 
                FROM speed_history 
                WHERE gid = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (gid, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

    def cleanup_speed_history(self, max_age_hours: int = 24):
        """Remove old speed history records"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM speed_history 
                WHERE timestamp < datetime('now', ?, 'localtime')
            ''', (f'-{max_age_hours} hours',))

    # Bandwidth aggregation operations
    def record_bandwidth(self, bytes_count: int):
        """Add bytes to today's global total"""
        if bytes_count <= 0: return
        today = datetime.now().strftime('%Y-%m-%d')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO global_bandwidth (date, bytes_downloaded)
                VALUES (?, 0)
                ON CONFLICT(date) DO NOTHING
            ''', (today,))
            cursor.execute('''
                UPDATE global_bandwidth 
                SET bytes_downloaded = bytes_downloaded + ? 
                WHERE date = ?
            ''', (bytes_count, today))

    def get_bandwidth_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get total bytes downloaded per day for the last N days"""
        history = []
        for i in range(days - 1, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            history.append({'date': day, 'bytes': 0})
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                cursor.execute('''
                    SELECT date, bytes_downloaded
                    FROM global_bandwidth
                    WHERE date >= ?
                    ORDER BY date ASC
                ''', (start_date,))
                
                rows = cursor.fetchall()
                db_results = {row['date']: row['bytes_downloaded'] for row in rows}
                
                for item in history:
                    if item['date'] in db_results:
                        item['bytes'] = db_results[item['date']]
        except Exception as e:
            logger.error(f"Bandwidth trend error: {e}")
                    
        return history

    # Helper methods
    def _row_to_movie(self, row: sqlite3.Row) -> Movie:
        """Convert database row to Movie object"""
        torrents_data = json.loads(row['torrents']) if row['torrents'] else []
        torrents = [Torrent.from_dict(t) for t in torrents_data]
        
        return Movie(
            id=row['id'],
            title=row['title'],
            year=row['year'],
            rating=row['rating'],
            genres=json.loads(row['genres']) if row['genres'] else [],
            description=row['description'] or '',
            poster_url=row['poster_url'] or '',
            poster_local=row['poster_local'],
            yts_url=row['yts_url'] or '',
            scraped_at=row['scraped_at'],
            torrents=torrents
        )
    
    def _row_to_download(self, row: sqlite3.Row) -> Download:
        """Convert database row to Download object"""
        return Download(
            id=row['id'],
            movie_id=row['movie_id'],
            movie_title=row['movie_title'],
            quality=row['quality'],
            magnet_link=row['magnet_link'],
            state=row['state'],
            progress=row['progress'],
            download_rate=row['download_rate'],
            upload_rate=row['upload_rate'],
            eta=row['eta'],
            size_total=row['size_total'],
            size_downloaded=row['size_downloaded'],
            num_peers=row['num_peers'],
            num_seeds=row['num_seeds'],
            save_path=row['save_path'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            error_message=row['error_message']
        )


# Singleton instance
_db_instance = None

def get_db() -> Database:
    """Get database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def init_db():
    """Initialize database (convenience function)"""
    db = get_db()
    logger.info("Database initialized successfully")
    return db
