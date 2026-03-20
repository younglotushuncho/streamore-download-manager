"""
Configuration settings for YTS Movie Monitor
"""
import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Base paths
if getattr(sys, 'frozen', False):
    # For frozen app, the true base is where the .exe lives
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # For development, use the directory containing this file's root
    BASE_DIR = Path(__file__).resolve().parent.parent

# If we are running from a delta patch folder (e.g. _src_patches), 
# the BASE_DIR detection above might point into it. We must ensure 
# it points to the REAL project root/install dir.
_parts = list(BASE_DIR.parts)
if '_src_patches' in _parts:
    idx = _parts.index('_src_patches')
    BASE_DIR = Path(*_parts[:idx])

def _is_actually_writable(path: Path) -> bool:
    test_file = path / f".write_test_{os.getpid()}"
    try:
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError, PermissionError):
        return False

# Determine writable directory locations
DATA_DIR = BASE_DIR / 'data'
DOWNLOADS_DIR = BASE_DIR / 'downloads'

if not _is_actually_writable(BASE_DIR) or 'Program Files' in str(BASE_DIR):
    _local = os.getenv('LOCALAPPDATA')
    if _local:
        _app_data = Path(_local) / 'Streamore'
        DATA_DIR = _app_data / 'data'
        _user_home = Path(os.path.expanduser('~'))
        DOWNLOADS_DIR = _user_home / 'Downloads' / 'Streamore'
    else:
        _home = Path(os.path.expanduser('~'))
        DATA_DIR = _home / '.streamore' / 'data'
        DOWNLOADS_DIR = _home / 'Downloads' / 'Streamore'

CACHE_DIR = DATA_DIR / 'cache' / 'posters'

# Ensure directories exist
def _ensure_dirs():
    global DATA_DIR, CACHE_DIR, DOWNLOADS_DIR
    for d in [DATA_DIR, CACHE_DIR, DOWNLOADS_DIR]:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create directory {d}: {e}")
            import tempfile
            _tmp = Path(tempfile.gettempdir()) / 'Streamore'
            DATA_DIR = _tmp / 'data'
            CACHE_DIR = DATA_DIR / 'cache'
            DOWNLOADS_DIR = _tmp / 'downloads'
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
            break

_ensure_dirs()

class Config:
    """Application configuration"""
    
    # Application version
    try:
        from shared.version import __version__ as _v
    except Exception:
        _v = '0.1.0'
    VERSION = _v

    # Auto-update manifest URL
    UPDATE_MANIFEST_URL = os.getenv('UPDATE_MANIFEST_URL', 'https://github.com/younglotushuncho/moviedownloader/releases/latest/download/manifest.signed.json')
    
    # Database
    DATABASE_PATH = str(DATA_DIR / 'movies.db')
    
    # YTS Website
    YTS_BASE_URL = os.getenv('YTS_BASE_URL', 'https://yts.bz')
    
    # Scraping
    USE_CURL_CFFI = True
    BROWSER_IMPERSONATE = 'chrome110'
    REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', '1.0'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '15'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    
    # Poster Cache
    POSTER_CACHE_DIR = str(CACHE_DIR)
    MAX_CACHE_SIZE_MB = int(os.getenv('MAX_CACHE_SIZE_MB', '500'))
    
    # Scraping Schedule
    SCRAPE_INTERVAL_MINUTES = int(os.getenv('SCRAPE_INTERVAL_MINUTES', '30'))
    
    # Downloads
    DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH', str(DOWNLOADS_DIR))
    MAX_CONCURRENT_DOWNLOADS = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '5'))
    DOWNLOAD_POLL_INTERVAL_SECONDS = int(os.getenv('DOWNLOAD_POLL_INTERVAL_SECONDS', '5'))
    
    # Flask API
    FLASK_HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    # Use a dedicated localhost port to avoid collisions with other local dev servers.
    FLASK_PORT = int(os.getenv('FLASK_PORT', '58432'))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Notifications
    ENABLE_NOTIFICATIONS = os.getenv('ENABLE_NOTIFICATIONS', 'True').lower() == 'true'
    MANAGED_GENRES = ['Action', 'Cartoons', 'Comedy', 'Drama', 'Horror', 'Romance']
    GENRE_CANONICAL_MAP = {
        'adventure': 'Action', 'crime': 'Action', 'fantasy': 'Action', 'sci-fi': 'Action',
        'scifi': 'Action', 'war': 'Action', 'animation': 'Cartoons', 'animated': 'Cartoons',
        'biography': 'Drama', 'documentary': 'Drama', 'family': 'Drama', 'film-noir': 'Drama',
        'history': 'Drama', 'mystery': 'Drama', 'sport': 'Drama', 'western': 'Drama', 'musical': 'Romance'
    }

# Constants for easy import
REQUEST_DELAY = Config.REQUEST_DELAY
REQUEST_TIMEOUT = Config.REQUEST_TIMEOUT
MAX_RETRIES = Config.MAX_RETRIES
