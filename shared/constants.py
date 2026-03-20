"""
Shared constants for YTS Movie Monitor
"""

# Movie qualities
QUALITIES = ['720p', '1080p', '2160p', '3D']

# Genres (from YTS)
GENRES = [
    'All',
    'Action',
    'Adventure',
    'Animation',
    'Biography',
    'Comedy',
    'Crime',
    'Documentary',
    'Drama',
    'Family',
    'Fantasy',
    'Film-Noir',
    'History',
    'Horror',
    'Music',
    'Musical',
    'Mystery',
    'Romance',
    'Sci-Fi',
    'Sport',
    'Thriller',
    'War',
    'Western'
]

# Sort options
SORT_OPTIONS = {
    'date_added': 'Date Added',
    'year': 'Year',
    'rating': 'Rating',
    'title': 'Title',
    'download_count': 'Downloads'
}

# Download states
DOWNLOAD_STATE_QUEUED = 'queued'
DOWNLOAD_STATE_DOWNLOADING = 'downloading'
DOWNLOAD_STATE_PAUSED = 'paused'
DOWNLOAD_STATE_COMPLETED = 'completed'
DOWNLOAD_STATE_ERROR = 'error'

DOWNLOAD_STATES = [
    DOWNLOAD_STATE_QUEUED,
    DOWNLOAD_STATE_DOWNLOADING,
    DOWNLOAD_STATE_PAUSED,
    DOWNLOAD_STATE_COMPLETED,
    DOWNLOAD_STATE_ERROR
]

# API endpoints
API_BASE = '/api'
API_MOVIES = f'{API_BASE}/movies'
API_MOVIE_DETAIL = f'{API_BASE}/movie/<movie_id>'
API_SCRAPE = f'{API_BASE}/scrape'
API_DOWNLOADS = f'{API_BASE}/downloads'
API_DOWNLOAD_START = f'{API_BASE}/download/start'
API_DOWNLOAD_PAUSE = f'{API_BASE}/download/<download_id>/pause'
API_DOWNLOAD_RESUME = f'{API_BASE}/download/<download_id>/resume'
API_DOWNLOAD_CANCEL = f'{API_BASE}/download/<download_id>/cancel'
API_STATS = f'{API_BASE}/stats'

# CSS Selectors for YTS scraping
YTS_SELECTORS = {
    'movie_cards': 'div.browse-movie-wrap',
    'title': 'a.browse-movie-title',
    'year': 'div.browse-movie-year',
    'rating': 'h4.rating',
    'genre': 'h4:not(.rating)',
    'poster': 'figure img',
    'synopsis': '#synopsis p, #synopsis',
    'genres_detail': 'div.hidden-xs h2, div#mobile-movie-info h2',

    'quality_sections': 'p.quality-size',
    'quality_tag': 'span.quality-tag',
    'quality_size': 'span.quality-size',
    'magnet_link': 'a[href^="magnet:"]',
    'torrent_link': 'a.download-torrent[href*="torrent"]'
}

# Request headers (used by curl_cffi impersonation)
DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
