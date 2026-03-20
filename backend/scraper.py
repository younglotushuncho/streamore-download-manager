"""
YTS Scraper using curl_cffi (FREE Cloudflare bypass)
"""
from curl_cffi import requests  # IMPORTANT: from curl_cffi, not regular requests!
from bs4 import BeautifulSoup
import time
import hashlib
import os
from typing import List, Dict, Optional
import logging

from backend.config import Config
from shared.constants import YTS_SELECTORS
from shared.models import Movie, Torrent

logger = logging.getLogger(__name__)


class YTSScraper:
    """
    Free YTS scraper using curl_cffi to bypass Cloudflare
    """
    
    def __init__(self):
        self.base_url = Config.YTS_BASE_URL
        self.last_request_time = 0
        
        # Session with browser impersonation (FREE Cloudflare bypass!)
        self.session = requests.Session()
        logger.info(f"YTSScraper initialized with base URL: {self.base_url}")
    
    def _rate_limit(self, delay: float = None):
        """Wait between requests to be polite"""
        delay = delay or Config.REQUEST_DELAY
        elapsed = time.time() - self.last_request_time
        if elapsed < delay:
            wait_time = delay - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, max_retries: int = None) -> Optional[BeautifulSoup]:
        """
        Make request with curl_cffi (impersonates Chrome to bypass Cloudflare).
        Uses a fresh session per request to avoid stale cookies causing wrong results.
        """
        max_retries = max_retries or Config.MAX_RETRIES
        self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching: {url} (attempt {attempt + 1}/{max_retries})")
                
                # Fresh session each request prevents stale cookies/state returning wrong pages
                from curl_cffi import requests as cffi_requests
                with cffi_requests.Session() as sess:
                    response = sess.get(
                        url,
                        impersonate=Config.BROWSER_IMPERSONATE,
                        timeout=Config.REQUEST_TIMEOUT
                    )
                
                response.raise_for_status()
                logger.debug(f"Success: {url} (status {response.status_code})")

                # Cap content size at 4MB before parsing to prevent MemoryError
                # on very broad searches that return huge HTML pages
                MAX_CONTENT_BYTES = 4 * 1024 * 1024  # 4 MB
                content = response.content
                if len(content) > MAX_CONTENT_BYTES:
                    logger.warning(f"Response too large ({len(content)//1024}KB), truncating to {MAX_CONTENT_BYTES//1024}KB")
                    content = content[:MAX_CONTENT_BYTES]

                return BeautifulSoup(content, 'html.parser')
                
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} attempts: {url}")
                    return None
    
    def _build_browse_url(self, keyword='0', quality='all', genre='all', rating='0', order_by='latest', year='0', language='en'):
        """Build path-based YTS browse URL matching the website's own URL format.
        
        Uses language='en' which is confirmed to work (returns full results).
        e.g. https://yts.bz/browse-movies/0/720p/all/0/latest/2026/en
        """
        from urllib.parse import quote
        keyword = quote(keyword) if keyword and keyword != '0' else '0'
        quality = quality.lower()
        genre = genre.lower()
        year = str(year) if year not in ('all', '0', '') else '0'
        
        # Map sort/order options to YTS path keywords
        order_map = {
            'date_added': 'latest',
            'latest': 'latest',
            'rating': 'rating',
            'year': 'year',
            'title': 'alphabetical',
            'alphabetical': 'alphabetical',
            'seeds': 'seeds',
            'peers': 'peers',
            'oldest': 'oldest'
        }
        order_by = order_map.get(order_by.lower(), 'latest')
        
        # Path format: /browse-movies/[keywords]/[quality]/[genre]/[rating]/[order_by]/[year]/[language]
        return f"{self.base_url}/browse-movies/{keyword}/{quality}/{genre}/{rating}/{order_by}/{year}/{language}"

    def scrape_browse_page(self,
                          page: int = 1,
                          genre: str = 'all',
                          quality: str = 'all',
                          year: str = 'all',
                          sort_by: str = 'date_added') -> List[Dict]:
        """
        Scrape movies from browse page using path-based filtering
        
        Args:
            page: Page number (1-indexed)
            genre: Genre filter (e.g., 'action', 'comedy', 'all')
            quality: Quality filter (e.g., '720p', '1080p', 'all')
            year: Year filter (e.g., '2024', 'all')
            sort_by: Sort order ('date_added', 'year', 'rating', 'title')
        
        Returns:
            List of movie dictionaries
        """
        # Build URL using the path-based structure
        url = self._build_browse_url(
            quality=quality,
            genre=genre,
            year=year,
            order_by=sort_by
        )
        url += f"?page={page}"
        
        logger.info(f"Scraping browse page {page} with URL: {url}")
        soup = self._make_request(url)
        
        if not soup:
            logger.warning("Failed to get browse page")
            return []
        
        movies = []
        movie_cards = soup.select(YTS_SELECTORS['movie_cards'])
        
        logger.info(f"Found {len(movie_cards)} movie cards on page {page}")
        
        for card in movie_cards:
            try:
                movie_data = self._parse_movie_card(card)
                if movie_data:
                    movies.append(movie_data)
            except Exception as e:
                logger.error(f"Error parsing movie card: {e}", exc_info=True)
                continue
        
        return movies

    # Maximum movies to return from a single search to avoid MemoryError on
    # broad queries (e.g. "dea" matching thousands of pages)
    MAX_SEARCH_RESULTS = 40

    def scrape_search(self, query: str, page: int = 1) -> List[Dict]:
        """
        Scrape YTS search results using the path-based URL:
          /browse-movies/{keyword}/all/all/0/latest/0/all
        This is server-side rendered and returns accurate keyword-filtered results.
        The ?keyword= query-param form is JS-only and ignores the keyword server-side.
        """
        try:
            from urllib.parse import quote
            q = quote(query)
            url = f"{self.base_url}/browse-movies/{q}/all/all/0/latest/0/all"
            logger.info(f"Scraping search URL: {url}")
            soup = self._make_request(url)
            if not soup:
                return []

            movies = []
            movie_cards = soup.select(YTS_SELECTORS['movie_cards'])
            logger.info(f"Found {len(movie_cards)} movie cards for search '{query}'")

            for card in movie_cards[:self.MAX_SEARCH_RESULTS]:
                try:
                    movie_data = self._parse_movie_card(card)
                    if movie_data:
                        movies.append(movie_data)
                except Exception as e:
                    logger.error(f"Error parsing movie card in search: {e}", exc_info=True)
                    continue

            # Sort results so title matches come first, metadata-only matches last.
            # YTS search matches on descriptions too, causing off-topic results.
            query_words = query.lower().split()
            def relevance_score(m):
                title = m.get('title', '').lower()
                # 0 = title contains full query, 1 = all words in title,
                # 2 = any word in title, 3 = no title match (metadata only)
                if query.lower() in title:
                    return 0
                if all(w in title for w in query_words):
                    return 1
                if any(w in title for w in query_words):
                    return 2
                return 3
            movies.sort(key=relevance_score)

            return movies
        except MemoryError:
            logger.error(f"MemoryError scraping search '{query}' — query too broad")
            return []
        except Exception as e:
            logger.error(f"Error in scrape_search: {e}", exc_info=True)
            return []

    def scrape_browse_filtered(self, keyword: str = '', quality: str = 'all', genre: str = 'all',
                               rating: int = 0, year: str = '0', order_by: str = 'latest',
                               page: int = 1, max_pages: int = 1) -> List[Dict]:
        """
        Scrape YTS browse page with filters matching the website URL pattern.
        
        Example URL: https://www.yts-official.top/browse-movies?keyword=&quality=720p&genre=action&rating=0&year=2024&order_by=latest
        
        Args:
            keyword: Search keyword (optional)
            quality: Quality filter (e.g., '720p', '1080p', '2160p', 'all')
            genre: Genre filter (e.g., 'action', 'comedy', 'all')
            rating: Minimum rating (0-9, default 0 for any)
            year: Year filter (e.g., '2024', '0' for all years)
            order_by: Sort order ('latest', 'rating', 'year', 'title')
            page: Starting page number (default 1)
            max_pages: Maximum number of pages to scrape (default 1, set to 10+ for all results)
        
        Returns:
            List of parsed movie dicts from all pages (does not save to DB)
        """
        try:
            from urllib.parse import quote, urlencode
            
            all_movies = []
            current_page = page
            
            while current_page <= (page + max_pages - 1):
                # Build path-based URL
                url = self._build_browse_url(
                    keyword=keyword,
                    quality=quality,
                    genre=genre,
                    rating=str(rating),
                    order_by=order_by,
                    year=year
                )
                url += f"?page={current_page}"
                
                logger.info(f"Scraping filtered browse page {current_page}/{page + max_pages - 1}: {url}")
                
                soup = self._make_request(url)
                if not soup:
                    logger.warning(f"Failed to get page {current_page}, stopping pagination")
                    break
                
                movies = []
                movie_cards = soup.select(YTS_SELECTORS['movie_cards'])
                logger.info(f"Found {len(movie_cards)} movie cards on page {current_page} (genre={genre}, quality={quality}, year={year})")
                
                # If no movies found, we've reached the end
                if len(movie_cards) == 0:
                    logger.info(f"No more movies found on page {current_page}, stopping pagination")
                    break
                
                for card in movie_cards:
                    try:
                        movie_data = self._parse_movie_card(card)
                        if movie_data:
                            movies.append(movie_data)
                    except Exception as e:
                        logger.error(f"Error parsing movie card: {e}", exc_info=True)
                        continue
                
                all_movies.extend(movies)
                current_page += 1
            
            logger.info(f"Scraped total of {len(all_movies)} movies across {current_page - page} pages")
            return all_movies
            
        except Exception as e:
            logger.error(f"Error in scrape_browse_filtered: {e}", exc_info=True)
            return []
    
    def _parse_movie_card(self, card: BeautifulSoup) -> Optional[Dict]:
        """Parse individual movie card from browse page"""
        try:
            # Title and URL
            title_elem = card.select_one(YTS_SELECTORS['title'])
            if not title_elem:
                logger.warning("No title element found in card")
                return None
            
            title = title_elem.text.strip()
            movie_path = title_elem.get('href', '')
            
            # Make full URL
            if movie_path.startswith('http'):
                movie_url = movie_path
            else:
                movie_url = self.base_url + movie_path
            
            # Year - Robustly extract 4-digit year
            year_elem = card.select_one(YTS_SELECTORS['year'])
            year_text = year_elem.text.strip() if year_elem else 'Unknown'
            # Extract first 4-digit number found in text
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
            year = year_match.group(0) if year_match else year_text[:4] if year_text[:4].isdigit() else 'Unknown'
            
            # Rating - Robustly extract numeric rating
            rating_elem = card.select_one(YTS_SELECTORS['rating'])
            rating_text = rating_elem.text.strip() if rating_elem else '0'
            try:
                # Handle formats like "8.5 / 10", "8.5★", or malformed "8.5 class="...
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                rating = float(rating_match.group(1)) if rating_match else 0.0
            except:
                rating = 0.0
            
            # Genres - collect all non-rating h4 tags
            genre_elems = card.select(YTS_SELECTORS['genre'])
            genres_list = []
            for g in genre_elems:
                g_text = g.text.strip()
                if g_text and g_text.lower() != 'unknown' and not any(char.isdigit() for char in g_text):
                    genres_list.append(g_text)

            # Poster
            img_elem = card.select_one(YTS_SELECTORS['poster'])
            poster_url = img_elem.get('src', '') if img_elem else ''
            
            # Make sure poster URL is absolute
            if poster_url and not poster_url.startswith('http'):
                poster_url = self.base_url + poster_url
            
            # Generate ID from title + year
            movie_id = hashlib.md5(f"{title}{year}".encode()).hexdigest()[:12]
            
            return {
                'id': movie_id,
                'title': title,
                'year': year,
                'rating': rating,
                'genres': genres_list,
                'description': '',
                'poster_url': poster_url,
                'poster_local': None,
                'yts_url': movie_url,
                'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'torrents': []
            }
            
        except Exception as e:
            logger.error(f"Error in _parse_movie_card: {e}", exc_info=True)
            return None
    
    def scrape_movie_details(self, movie_url: str) -> Optional[Dict]:
        """
        Scrape detailed information from movie page
        
        Args:
            movie_url: Full URL to movie detail page
        
        Returns:
            Dictionary with description, genres, and torrents
        """
        logger.info(f"Scraping movie details: {movie_url}")
        soup = self._make_request(movie_url)
        
        if not soup:
            logger.warning(f"Failed to get movie details: {movie_url}")
            return None
        
        try:
            details = {}
            
            # Description
            synopsis_elem = soup.select_one(YTS_SELECTORS['synopsis'])
            if synopsis_elem:
                details['description'] = synopsis_elem.get_text(strip=True)
            
            # Rating fallback (in case browse page missed it)
            rating_elem = soup.select_one('span[itemprop="ratingValue"]')
            if rating_elem:
                try:
                    details['rating'] = float(rating_elem.text.strip())
                except:
                    pass

            
            # Genres — the page puts year and genre as back-to-back plain <h2>s
            # inside div.hidden-xs; filter out the 4-digit year to get genres only
            genre_elems = soup.select(YTS_SELECTORS['genres_detail'])
            genres_found = []
            for g in genre_elems:
                raw = g.text.strip()
                if not raw or raw.isdigit() or len(raw) <= 2:
                    continue
                # Split "Action / Comedy / Crime" (with possible non-breaking spaces)
                parts = [p.strip().replace('\xa0', '').strip() for p in raw.replace('\u00a0', ' ').split('/')]
                genres_found.extend([p for p in parts if p and not p.isdigit()])
            # Deduplicate (two divs contain the same info) while preserving order
            seen = set()
            unique_genres = []
            for g in genres_found:
                if g.lower() not in seen:
                    seen.add(g.lower())
                    unique_genres.append(g)
            if unique_genres:
                details['genres'] = unique_genres
            
            # Torrents
            torrents = self._extract_torrents(soup)
            details['torrents'] = torrents
            
            logger.info(f"Extracted details: {len(torrents)} torrents found")
            return details
            
        except Exception as e:
            logger.error(f"Error scraping details from {movie_url}: {e}", exc_info=True)
            return None
    
    def _extract_torrents(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract torrent information from movie detail page"""
        torrents = []
        
        # YTS uses modal-torrent divs containing all torrent info
        modal_sections = soup.select('div.modal-torrent')
        logger.debug(f"Found {len(modal_sections)} modal-torrent divs")
        
        for modal in modal_sections:
            try:
                # Quality - in div.modal-quality > span
                quality_elem = modal.select_one('div.modal-quality span')
                if not quality_elem:
                    logger.warning("No quality element found in modal")
                    continue
                quality = quality_elem.text.strip()
                
                # Size - in <p> tags, format is "File size" then "X.XX GB"
                size = 'Unknown'
                p_tags = modal.select('p')
                for i, p in enumerate(p_tags):
                    if 'File size' in p.text:
                        # Next p tag should have the size
                        if i + 1 < len(p_tags):
                            size = p_tags[i + 1].text.strip()
                        break
                
                # Magnet link
                magnet_elem = modal.select_one('a[href^="magnet:"]')
                magnet_link = magnet_elem.get('href', '') if magnet_elem else ''
                
                # Torrent file URL
                torrent_elem = modal.select_one('a.download-torrent')
                torrent_url = torrent_elem.get('href', '') if torrent_elem else ''
                
                if magnet_link or torrent_url:
                    # Ensure full URL for torrent file
                    if torrent_url and not torrent_url.startswith('http'):
                        torrent_url = f"{self.base_url}{torrent_url}"
                    
                    # Fix: Ensure torrent hash is exactly 40 characters
                    # Sometimes extra characters get appended
                    if torrent_url and '/torrent/download/' in torrent_url:
                        parts = torrent_url.split('/torrent/download/')
                        if len(parts) == 2:
                            base = parts[0]
                            hash_part = parts[1]
                            # BitTorrent info-hash must be exactly 40 hex characters
                            if len(hash_part) > 40:
                                hash_part = hash_part[:40]
                                torrent_url = f"{base}/torrent/download/{hash_part}"
                                logger.debug(f"Trimmed torrent hash to 40 chars: {hash_part}")
                    
                    torrents.append({
                        'quality': quality,
                        'size': size,
                        'magnet_link': magnet_link,
                        'torrent_url': torrent_url
                    })
                    logger.debug(f"Extracted torrent: {quality} - {size}")
                    
            except Exception as e:
                logger.error(f"Error parsing torrent: {e}", exc_info=True)
                continue
        
        logger.info(f"Total torrents extracted: {len(torrents)}")
        return torrents
    
    def download_poster(self, url: str, save_path: str) -> bool:
        """
        Download poster image using curl_cffi
        
        Args:
            url: Poster image URL
            save_path: Local path to save the image
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading poster: {url}")
            
            # Create directory if needed
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            response = self.session.get(
                url,
                impersonate=Config.BROWSER_IMPERSONATE,
                timeout=10
            )
            
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded poster to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download poster: {e}")
            return False


# Test function
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = YTSScraper()
    print("Testing YTS scraper with curl_cffi (FREE)...")
    
    movies = scraper.scrape_browse_page(page=1)
    print(f"✓ Found {len(movies)} movies")
    
    if movies:
        print(f"\nFirst movie: {movies[0]['title']} ({movies[0]['year']})")
        print(f"Rating: {movies[0]['rating']}")
        print(f"URL: {movies[0]['yts_url']}")
        
        # Test details
        print("\nFetching movie details...")
        details = scraper.scrape_movie_details(movies[0]['yts_url'])
        if details and details.get('torrents'):
            print(f"✓ Found {len(details['torrents'])} torrents")
            for t in details['torrents']:
                print(f"  - {t['quality']}: {t['size']}")
        else:
            print("  No torrents found")
    else:
        print("✗ No movies found - check site accessibility")
