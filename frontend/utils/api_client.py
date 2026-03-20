"""
API client for communicating with Flask backend
"""
import requests
import logging
import os
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class APIClient:
    """Client for YTS Movie Monitor API"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.is_online = True
        self.cache_dir: Optional[Path] = None
        
        # Determine a safe persistent directory for the API cache
        import sys
        if getattr(sys, 'frozen', False):
            # In PyInstaller, the executable directory is the correct place to save data, 
            # NOT the _MEIPASS Temp extract folder.
            cache_base = Path(os.path.dirname(sys.executable)).joinpath('data', 'api_cache')
            try:
                cache_base.mkdir(parents=True, exist_ok=True)
                self.cache_dir = cache_base
            except Exception:
                # Fallback to LocalAppData if installation dir is read-only
                self.cache_dir = Path(os.environ.get('LOCALAPPDATA', '')).joinpath('Streamore Monitor', 'data', 'api_cache')
        else:
            self.cache_dir = Path(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'api_cache')).resolve()

        if self.cache_dir is not None:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                logger.exception('Failed to create api cache dir')
                self.cache_dir = None

        # responses older than this will still be returned on failure but considered stale
        self.cache_ttl = 60 * 60  # 1 hour
        logger.info(f"APIClient initialized: {base_url}, cache_dir={self.cache_dir}")
    
    # Endpoints whose responses must never be cached — they are live scrapes
    # whose results change every request and depend on backend-side YTS fetches.
    _NO_CACHE_ENDPOINTS = {
        '/api/browse/scrape',
        '/api/search/scrape',
        '/api/movie/details-by-url',
    }

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request to API with fallback to disk cache on connection failure.
        
        Live-scrape endpoints (/api/browse/scrape, /api/search/scrape) are never
        cached — calling them always hits the backend fresh.
        """
        url = f"{self.base_url}{endpoint}"
        method = method.upper()
        use_cache = method == 'GET' and endpoint not in self._NO_CACHE_ENDPOINTS
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            self.is_online = True
            
            try:
                data = response.json()
                # Save to disk-cache only for cacheable endpoints
                if use_cache and self.cache_dir is not None and isinstance(data, (dict, list)):
                    cache_path = self._cache_path(url, kwargs.get('params') or kwargs.get('json') or {})
                    if cache_path:
                        try:
                            # Write to temp file first then rename to ensure atomic write
                            temp_path = f"{cache_path}.tmp"
                            with open(temp_path, 'w', encoding='utf-8') as fh:
                                json.dump({'ts': int(time.time()), 'data': data}, fh)
                            os.replace(temp_path, cache_path)
                        except Exception:
                            logger.debug('Failed to write api cache')
                return data
            except ValueError:
                return None
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                requests.exceptions.ConnectTimeout) as e:
            self.is_online = False
            logger.debug(f"Backend offline or unreachable ({method} {url}): {e}")
            
            # For cacheable GET requests, try to serve from cache even if stale
            if use_cache and self.cache_dir is not None:
                try:
                    cache_path = self._cache_path(url, kwargs.get('params') or kwargs.get('json') or {})
                    if cache_path and os.path.exists(cache_path):
                        with open(cache_path, 'r', encoding='utf-8') as fh:
                            cached = json.load(fh)
                            ts = cached.get('ts', 0)
                            data = cached.get('data')
                            age = int(time.time()) - int(ts)
                            if data is not None:
                                logger.info(f"Serving stale cached response for {endpoint} (age={age}s)")
                                return data
                except Exception:
                    logger.debug('Failed to read api cache on failure')
            return None
            
        except requests.exceptions.RequestException as e:
            # Other HTTP errors (4xx, 5xx)
            logger.error(f"API request failed: {method} {url} - {e}")
            return None

    def _cache_path(self, url: str, params: dict) -> str:
        """Return a filesystem path for caching the response for given URL+params."""
        try:
            key = url
            if params:
                # stable representation of params
                try:
                    key += json.dumps(params, sort_keys=True, default=str)
                except Exception:
                    key += str(params)
            h = hashlib.sha1(key.encode('utf-8')).hexdigest()
            if self.cache_dir is None:
                return ""
            return str(self.cache_dir.joinpath(f"{h}.json"))
        except Exception:
            return None
    
    def health_check(self) -> bool:
        """Check if API is healthy"""
        result = self._request('GET', '/api/health')
        return result is not None and result.get('status') == 'healthy'
    
    def get_stats(self) -> Optional[Dict]:
        """Get application statistics"""
        return self._request('GET', '/api/stats')
    
    def get_movies(self,

                   genre: str = 'All',
                   year: str = 'All',
                   quality: str = 'All',
                   min_rating: float = 0.0,
                   sort_by: str = 'scraped_at',
                   limit: int = 500,
                   offset: int = 0,
                   search: Optional[str] = None,
                   added_within_days: Optional[int] = None) -> Optional[List[Dict]]:
        """Get movies with filters"""
        params = {
            'genre': genre,
            'year': year,
            'quality': quality,
            'min_rating': min_rating,
            'sort_by': sort_by,
            'limit': limit,
            'offset': offset
        }
        if search:
            params['search'] = search
        if added_within_days is not None:
            try:
                params['added_within_days'] = int(added_within_days)
            except Exception:
                pass
        
        result = self._request('GET', '/api/movies', params=params)
        if result and result.get('success'):
            return result.get('movies', [])
        return None
    
    def get_movie(self, movie_id: str) -> Optional[Dict]:
        """Get a specific movie"""
        result = self._request('GET', f'/api/movie/{movie_id}')
        if result and result.get('success'):
            return result.get('movie')
        return None
    
    def fetch_movie_torrents(self, movie_id: str) -> Optional[Dict]:
        """Fetch fresh torrent data from YTS website for a specific movie"""
        result = self._request('POST', f'/api/movie/{movie_id}/fetch-torrents')
        if result and result.get('success'):
            return result
        return None
    
    def scrape_movies(self,
                      page: int = 1,
                      genre: str = 'all',
                      quality: str = 'all',
                      year: str = 'all',
                      fetch_details: bool = False) -> Optional[Dict]:
        """Trigger movie scraping"""
        data = {
            'page': page,
            'genre': genre,
            'quality': quality,
            'year': year,
            'fetch_details': fetch_details
        }
        return self._request('POST', '/api/scrape', json=data)

    def search_scrape(self, query: str, page: int = 1) -> Optional[List[Dict]]:
        """Call backend to scrape YTS search results for a query (does not save to DB)"""
        params = {'q': query, 'page': page}
        result = self._request('GET', '/api/search/scrape', params=params)
        if result and result.get('success'):
            return result.get('movies', [])
        return None

    def get_movie_details_by_url(self, yts_url: str) -> Optional[Dict]:
        """Scrape full movie details (description, genres, torrents) from a YTS page URL.
        Does not require the movie to be saved in the database."""
        result = self._request('GET', '/api/movie/details-by-url', params={'yts_url': yts_url})
        if result and result.get('success'):
            return result
        return None

    def browse_scrape(self, keyword: str = '', quality: str = 'all', genre: str = 'all',
                     rating: int = 0, year: str = '0', order_by: str = 'latest',
                     page: int = 1, max_pages: int = 10) -> Optional[List[Dict]]:
        """
        Call backend to scrape YTS browse page with filters (does not save to DB).
        
        Args match YTS website pattern:
            keyword: search keyword
            quality: '720p', '1080p', '2160p', 'all'
            genre: 'action', 'comedy', etc. or 'all'
            rating: minimum rating 0-9
            year: year or '0'/'all' for all years
            order_by: 'latest', 'rating', 'year', 'title'
            page: starting page number
            max_pages: maximum pages to scrape (default 10 to get all results)
        """
        params = {
            'keyword': keyword,
            'quality': quality,
            'genre': genre,
            'rating': rating,
            'year': year,
            'order_by': order_by,
            'page': page,
            'max_pages': max_pages
        }
        result = self._request('GET', '/api/browse/scrape', params=params)
        if result and result.get('success'):
            return result.get('movies', [])
        return None
    
    def get_downloads(self, state: Optional[str] = None) -> Optional[List[Dict]]:
        """Get all downloads"""
        params = {}
        if state:
            params['state'] = state
        result = self._request('GET', '/api/downloads', params=params)
        # result may be:
        # - None on error
        # - dict with {'success': True, 'downloads': [...]}
        # - sometimes the endpoint may return a raw list (handle that)
        if result is None:
            return None
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and result.get('success'):
            return result.get('downloads', [])
        return None
    
    def get_download(self, download_id: str) -> Optional[Dict]:
        """Get a specific download"""
        result = self._request('GET', f'/api/download/{download_id}')
        if result and result.get('success'):
            return result.get('download')
        return None
    
    def start_download(self, movie_id: str, movie_title: str, quality: str, magnet_link: str, organize_by_genre: bool = True, genres: Optional[list] = None) -> Optional[str]:
        """Start a new download"""
        logger.info(f"API: start_download called - movie_id={movie_id}, title={movie_title}, quality={quality}, organize={organize_by_genre}")
        if magnet_link:
            logger.debug(f"API: magnet_link={magnet_link[:80]}...")
        
        data = {
            'movie_id': movie_id,
            'movie_title': movie_title,
            'quality': quality,
            'magnet_link': magnet_link,
            'organize_by_genre': organize_by_genre,
            'genres': genres or []
        }
        
        logger.info(f"API: Sending POST /api/download/start with data keys: {list(data.keys())}")
        result = self._request('POST', '/api/download/start', json=data)
        
        if result and result.get('success'):
            download_id = result.get('download_id')
            logger.info(f"API: Download started successfully, download_id={download_id}")
            return download_id
        else:
            logger.warning(f"API: Download failed, result={result}")
            return None
    
    def pause_download(self, download_id: str) -> bool:
        """Pause a download"""
        result = self._request('POST', f'/api/download/{download_id}/pause')
        return result is not None and result.get('success', False)
    
    def resume_download(self, download_id: str) -> bool:
        """Resume a download"""
        result = self._request('POST', f'/api/download/{download_id}/resume')
        return result is not None and result.get('success', False)
    
    def cancel_download(self, download_id: str, delete_files: bool = False) -> bool:
        """Cancel a download. Option to delete files from disk."""
        data = {'delete_files': delete_files}
        result = self._request('POST', f'/api/download/{download_id}/cancel', json=data)
        return result is not None and result.get('success', False)

    def get_settings(self) -> Optional[Dict]:
        """Get application settings from backend"""
        result = self._request('GET', '/api/settings')
        if result and result.get('success'):
            return result.get('settings')
        return None

    def update_settings(self, settings: Dict) -> bool:
        """Update application settings in backend"""
        result = self._request('POST', '/api/settings', json=settings)
        return result is not None and result.get('success', False)
    def get_torrent_settings(self) -> Optional[Dict]:
        """Get torrent/aria2 settings from backend"""
        result = self._request('GET', '/api/torrent-settings')
        if result and result.get('success'):
            return result.get('settings')
        return None

    def update_torrent_settings(self, settings: Dict) -> bool:
        """Update torrent/aria2 settings in backend and apply to running aria2"""
        result = self._request('POST', '/api/torrent-settings', json=settings)
        return result is not None and result.get('success', False)