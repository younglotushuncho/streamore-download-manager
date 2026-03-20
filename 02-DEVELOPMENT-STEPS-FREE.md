# 🆓 FREE VERSION: Development Steps with curl_cffi

## Phase 2: Web Scraper (FREE with curl_cffi)

### STEP 2.1: Create Base Scraper (FREE VERSION)

**Cursor Prompt**:
```
Create a web scraper for YTS website (yts-official.top) using curl_cffi for FREE Cloudflare bypass.

File: backend/scraper.py

CRITICAL: Use curl_cffi (100% FREE) instead of cloudscraper:
- Import: from curl_cffi import requests
- NOT: import requests (regular requests library)
- curl_cffi is FREE and open source (MIT license)

Requirements:
1. Imports:
   from curl_cffi import requests  # Special import!
   from bs4 import BeautifulSoup
   import time
   import hashlib
   import logging

2. Create YTSScraper class with __init__:
   - self.base_url = 'https://www.yts-official.top'
   - self.session = requests.Session()  # curl_cffi session
   - self.last_request_time = 0

3. Method: scrape_browse_movies(page=1, genre='all', quality='all', year='all', sort_by='date_added'):
   - Build URL: f"{self.base_url}/browse-movies?page={page}"
   - Add filters as query parameters
   - Make request: response = self.session.get(url, impersonate="chrome110", timeout=15)
   - Parse with BeautifulSoup
   - Find movie cards: soup.select('div.browse-movie-wrap')
   - Extract from each card:
     * Title: a.browse-movie-title
     * Year: div.browse-movie-year
     * Rating: div.rating
     * Genre: div.genre
     * Poster: figure img src
     * URL: title link href
   - Return list of movie dicts

4. Method: scrape_movie_details(movie_url):
   - Use self.session.get(movie_url, impersonate="chrome110")
   - Extract description from #synopsis
   - Extract genres from .genres span
   - Call _extract_torrents(soup)
   - Return dict with description, genres, torrents

5. Method: _extract_torrents(soup):
   - Find all quality sections: p.quality-size
   - For each section extract:
     * quality: span.quality-tag
     * size: span.quality-size
     * magnet_link: a[href^="magnet:"]
     * torrent_url: a.download-torrent
   - Return list of torrent dicts

6. Method: _make_request(url, max_retries=3):
   - Call _rate_limit() first
   - Try/except for retries:
     * response = self.session.get(url, impersonate="chrome110", timeout=15)
     * response.raise_for_status()
     * return BeautifulSoup(response.content, 'html.parser')
   - On error: exponential backoff (2^attempt seconds)
   - Log all attempts and errors
   - Return None after max retries

7. Method: _rate_limit(delay=2.0):
   - Check elapsed time since last_request_time
   - Sleep if < delay seconds
   - Update last_request_time

8. Method: download_poster(url, save_path):
   - Use self.session.get(url, impersonate="chrome110", timeout=10)
   - Write response.content to save_path in binary mode
   - Return True on success, False on error

9. Error handling:
   - Try/except around all network operations
   - Handle 403/503 with retries
   - Handle timeout errors
   - Log all errors with context
   - Never crash, return empty/None on failure

10. Logging:
    - logger = logging.getLogger(__name__)
    - Log each request URL
    - Log number of movies found
    - Log all errors with details

Constants:
- REQUEST_DELAY = 2.0
- REQUEST_TIMEOUT = 15
- MAX_RETRIES = 3

IMPORTANT: 
- Always use impersonate="chrome110" in session.get()
- This makes curl_cffi pretend to be Chrome browser
- Bypasses Cloudflare for FREE!
- Do NOT use regular requests.get()

Example usage in docstring:
```python
from backend.scraper import YTSScraper
scraper = YTSScraper()
movies = scraper.scrape_browse_page(page=1)
print(f"Found {len(movies)} movies")
```
```

**Expected Output**: `backend/scraper.py` with FREE curl_cffi scraper

**Test Command**:
```python
import logging
from backend.scraper import YTSScraper

logging.basicConfig(level=logging.INFO)

print("Testing FREE curl_cffi scraper...")
scraper = YTSScraper()

# Test browse page
movies = scraper.scrape_browse_page(page=1)
print(f"✓ Found {len(movies)} movies")

if movies:
    movie = movies[0]
    print(f"\n✓ First movie: {movie['title']} ({movie['year']})")
    print(f"  Rating: {movie['rating']}")
    print(f"  Poster: {movie['poster_url']}")
    
    # Test movie details
    print(f"\n✓ Fetching details for {movie['title']}...")
    details = scraper.scrape_movie_details(movie['yts_url'])
    
    if details:
        print(f"  Description: {details.get('description', '')[:100]}...")
        
        if details.get('torrents'):
            print(f"\n✓ Found {len(details['torrents'])} torrents:")
            for torrent in details['torrents']:
                print(f"    - {torrent['quality']}: {torrent['size']}")
        else:
            print("  No torrents found")
else:
    print("✗ No movies found - check site accessibility")

print("\n✓ Scraper test complete!")
```

---

### STEP 2.2: Add Poster Caching (FREE VERSION)

**Cursor Prompt**:
```
Add poster caching to the scraper using curl_cffi for downloads.

Update: backend/scraper.py

Add PosterCache class:

class PosterCache:
    def __init__(self, cache_dir, max_size_mb=500):
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_filename(self, url):
        # Generate MD5 hash of URL
        hash_str = hashlib.md5(url.encode()).hexdigest()
        return f"{hash_str}.jpg"
    
    def get_cached_path(self, url):
        # Check if poster exists in cache
        filename = self.get_cache_filename(url)
        filepath = os.path.join(self.cache_dir, filename)
        if os.path.exists(filepath):
            return filepath
        return None
    
    def add_to_cache(self, url, image_data):
        # Save image to cache
        filename = self.get_cache_filename(url)
        filepath = os.path.join(self.cache_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Check cache size and clean if needed
        if self.get_cache_size() > self.max_size_mb:
            self.clean_old_posters()
        
        return filepath
    
    def get_cache_size(self):
        # Calculate total cache size in MB
        total_size = 0
        for filename in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.isfile(filepath):
                total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # Convert to MB
    
    def clean_old_posters(self):
        # Remove oldest files until under max_size
        files = []
        for filename in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.isfile(filepath):
                files.append((filepath, os.path.getmtime(filepath)))
        
        # Sort by modification time (oldest first)
        files.sort(key=lambda x: x[1])
        
        # Delete oldest files
        while self.get_cache_size() > self.max_size_mb and files:
            filepath, _ = files.pop(0)
            os.remove(filepath)
            logger.info(f"Removed old poster: {filepath}")

Update YTSScraper class:
- Add self.poster_cache = PosterCache('data/cache/posters') in __init__
- Update download_poster(url, save_path):
  * Check cache first: cached = self.poster_cache.get_cached_path(url)
  * If cached, copy to save_path and return True
  * If not cached, download with curl_cffi
  * Add to cache after download
  * Return local path

Use curl_cffi for downloads:
- response = self.session.get(url, impersonate="chrome110", timeout=10)
- image_data = response.content
- self.poster_cache.add_to_cache(url, image_data)
```

**Expected Output**: Updated scraper with caching

---

### STEP 2.3: Add Tests (FREE VERSION)

**Cursor Prompt**:
```
Create unit tests for YTS scraper using curl_cffi.

File: tests/test_scraper.py

Use pytest and unittest.mock to mock curl_cffi responses.

IMPORTANT: Mock curl_cffi.requests, not regular requests!

Test cases:

1. test_scraper_initialization():
   - Assert session is curl_cffi.requests.Session
   - Assert base_url correct
   - Assert rate limiting vars initialized

2. test_scrape_browse_page_success():
   - Mock self.session.get to return sample HTML
   - Verify movies parsed correctly
   - Check movie data structure

3. test_scrape_with_impersonate():
   - Verify that session.get() called with impersonate="chrome110"
   - This is critical for Cloudflare bypass

4. test_403_error_retry():
   - Mock 403 response
   - Verify retry logic works
   - Verify exponential backoff

5. test_rate_limiting():
   - Mock time.time()
   - Verify proper delays between requests

6. test_download_poster():
   - Mock image download
   - Verify curl_cffi used (not regular requests)

Example test:
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.scraper import YTSScraper

@pytest.fixture
def scraper():
    return YTSScraper()

def test_uses_curl_cffi_impersonate(scraper):
    # Mock curl_cffi session
    with patch.object(scraper.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html></html>'
        mock_get.return_value = mock_response
        
        scraper._make_request('http://test.com')
        
        # Verify impersonate parameter used
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert 'impersonate' in call_kwargs
        assert call_kwargs['impersonate'] == 'chrome110'
```
```

---

## Updated Requirements (100% FREE)

### backend/requirements.txt

```txt
# Web Framework
Flask==3.0.0

# Web Scraping - ALL FREE!
curl-cffi==0.6.2       # FREE Cloudflare bypass (MIT license)
beautifulsoup4==4.12.2
lxml==4.9.3

# Torrent
libtorrent==2.0.9

# Database
SQLAlchemy==2.0.23

# Utilities
python-dotenv==1.0.0
Pillow==10.1.0

# Notifications
plyer==2.1.0

# Logging
colorlog==6.8.0

# Scheduling
APScheduler==3.10.4

# Testing - ALL FREE!
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
```

### Installation
```bash
pip install -r backend/requirements.txt

# Or individually:
pip install curl-cffi beautifulsoup4 lxml
```

---

## Configuration Updates

### backend/config.py
```python
class Config:
    # YTS Website
    YTS_BASE_URL = os.getenv('YTS_BASE_URL', 'https://www.yts-official.top')
    
    # Scraping with curl_cffi (FREE!)
    USE_CURL_CFFI = True  # Use FREE curl_cffi
    BROWSER_IMPERSONATE = 'chrome110'  # Browser to impersonate
    REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', 2.0))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 15))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
```

### .env
```ini
# YTS Website
YTS_BASE_URL=https://www.yts-official.top

# Scraping (FREE with curl_cffi)
REQUEST_DELAY=2.0
REQUEST_TIMEOUT=15
MAX_RETRIES=3
```

---

## Why curl_cffi is the BEST FREE Option

### Comparison: FREE Options

| Feature | curl_cffi | cloudscraper | Playwright |
|---------|-----------|--------------|------------|
| **Cost** | FREE ✅ | FREE ✅ | FREE ✅ |
| **License** | MIT | MIT | Apache 2.0 |
| **Size** | 20MB | 5MB | 150MB |
| **Speed** | Fast ⚡ | Fast ⚡ | Slow 🐌 |
| **Cloudflare** | ✅ Excellent | ⚠️ Good | ✅ Excellent |
| **Maintenance** | Active 2024 | Sometimes breaks | Active |
| **Complexity** | Easy | Easy | Hard |
| **YTS Works?** | ✅ Yes | ⚠️ Maybe | ✅ Yes |

**Winner: curl_cffi** 🏆

### Why curl_cffi Wins:
1. ✅ **100% FREE** (MIT license - use anywhere!)
2. ✅ **Best Cloudflare bypass** (browser impersonation)
3. ✅ **Lightweight** (only 20MB)
4. ✅ **Fast** (1-2 seconds per page)
5. ✅ **Actively maintained** (2024 updates)
6. ✅ **Easy to use** (same API as requests)
7. ✅ **Reliable** (98% success rate)
8. ✅ **No browser download** (unlike Playwright)

### Why NOT the Others:
- **cloudscraper**: Sometimes breaks with Cloudflare updates
- **Playwright**: Too heavy (150MB), slow, complex deployment
- **requests-html**: Outdated, unreliable
- **Selenium**: Very slow, large size

---

## Cost Comparison

| Solution | Setup Cost | Monthly Cost | Deployment Cost |
|----------|-----------|--------------|-----------------|
| **curl_cffi** | $0 | $0 | $0 |
| cloudscraper | $0 | $0 | $0 |
| Playwright | $0 | $0 | $0 |
| ScraperAPI | $0 | $49+ | N/A |
| Bright Data | $0 | $500+ | N/A |

**All coding solutions are FREE!** No paid services needed. 🎉

---

## Final Summary

### Use curl_cffi because:
✅ Completely FREE (MIT license)  
✅ Best Cloudflare bypass  
✅ Lightweight & fast  
✅ Easy to deploy  
✅ Actively maintained  
✅ Perfect for YTS  
✅ No costs ever  

### Total Project Cost: $0
- Python: FREE
- curl_cffi: FREE
- BeautifulSoup: FREE
- PyQt6: FREE
- libtorrent: FREE
- **Everything is FREE!** 🎉

---

**FREE Guide Version**: 1.0  
**Cost**: $0 (100% Free)  
**Library**: curl-cffi  
**License**: MIT (use anywhere)  
**Best For**: YTS Movie Monitor
