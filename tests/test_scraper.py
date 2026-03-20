"""
Unit tests for YTS scraper
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.scraper import YTSScraper


@pytest.fixture
def scraper():
    """Create scraper instance for testing"""
    return YTSScraper()


@pytest.fixture
def sample_browse_html():
    """Sample HTML from browse page"""
    return '''
    <html>
        <body>
            <div class="browse-movie-wrap">
                <a class="browse-movie-title" href="/movies/test-movie-2024">Test Movie</a>
                <div class="browse-movie-year">2024</div>
                <div class="rating">8.5 / 10</div>
                <div class="genre">Action</div>
                <figure><img src="/assets/poster.jpg" /></figure>
            </div>
            <div class="browse-movie-wrap">
                <a class="browse-movie-title" href="/movies/another-movie-2023">Another Movie</a>
                <div class="browse-movie-year">2023</div>
                <div class="rating">7.2 / 10</div>
                <div class="genre">Comedy</div>
                <figure><img src="https://example.com/poster2.jpg" /></figure>
            </div>
        </body>
    </html>
    '''


@pytest.fixture
def sample_detail_html():
    """Sample HTML from movie detail page"""
    return '''
    <html>
        <body>
            <div id="synopsis">
                <p>This is a test movie description with lots of detail about the plot.</p>
            </div>
            <div class="genres">
                <span>Action</span>
                <span>Adventure</span>
                <span>Thriller</span>
            </div>
            <p class="quality-size">
                <span class="quality-tag">1080p</span>
                <span class="quality-size">2.5GB</span>
                <a href="magnet:?xt=urn:btih:test123">Magnet</a>
                <a class="download-torrent" href="/torrent/download/test.torrent">Torrent</a>
            </p>
            <p class="quality-size">
                <span class="quality-tag">720p</span>
                <span class="quality-size">1.2GB</span>
                <a href="magnet:?xt=urn:btih:test456">Magnet</a>
            </p>
        </body>
    </html>
    '''


class TestYTSScraper:
    """Test suite for YTS scraper"""
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly"""
        assert scraper.base_url is not None
        assert scraper.session is not None
        assert scraper.last_request_time == 0
    
    def test_uses_curl_cffi_impersonate(self, scraper, sample_browse_html):
        """Test that scraper uses curl_cffi with impersonate parameter"""
        with patch.object(scraper.session, 'get') as mock_get:
            # Mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = sample_browse_html.encode()
            mock_get.return_value = mock_response
            
            # Make request
            scraper._make_request('http://test.com')
            
            # Verify impersonate parameter used
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert 'impersonate' in call_kwargs
            assert call_kwargs['impersonate'] == 'chrome110'
    
    def test_scrape_browse_page_success(self, scraper, sample_browse_html):
        """Test successful browse page scraping"""
        with patch.object(scraper.session, 'get') as mock_get:
            # Mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = sample_browse_html.encode()
            mock_get.return_value = mock_response
            
            # Scrape
            movies = scraper.scrape_browse_page(page=1)
            
            # Verify
            assert len(movies) == 2
            assert movies[0]['title'] == 'Test Movie'
            assert movies[0]['year'] == '2024'
            assert movies[0]['rating'] == 8.5
            assert movies[0]['genres'] == ['Action']
            assert movies[1]['title'] == 'Another Movie'
            assert movies[1]['year'] == '2023'
            assert movies[1]['rating'] == 7.2
    
    def test_parse_movie_card_with_absolute_url(self, scraper, sample_browse_html):
        """Test parsing movie card with absolute poster URL"""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = sample_browse_html.encode()
            mock_get.return_value = mock_response
            
            movies = scraper.scrape_browse_page(page=1)
            
            # Second movie has absolute URL
            assert movies[1]['poster_url'].startswith('http')
    
    def test_scrape_movie_details(self, scraper, sample_detail_html):
        """Test scraping movie detail page"""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = sample_detail_html.encode()
            mock_get.return_value = mock_response
            
            details = scraper.scrape_movie_details('http://test.com/movie')
            
            # Verify description
            assert 'This is a test movie description' in details['description']
            
            # Verify genres
            assert len(details['genres']) == 3
            assert 'Action' in details['genres']
            assert 'Adventure' in details['genres']
            assert 'Thriller' in details['genres']
            
            # Verify torrents
            assert len(details['torrents']) == 2
            assert details['torrents'][0]['quality'] == '1080p'
            assert details['torrents'][0]['size'] == '2.5GB'
            assert 'magnet:' in details['torrents'][0]['magnet_link']
            assert details['torrents'][1]['quality'] == '720p'
    
    def test_403_error_retry(self, scraper):
        """Test retry logic on 403 error"""
        with patch.object(scraper.session, 'get') as mock_get:
            # First two calls fail, third succeeds
            mock_get.side_effect = [
                Exception("403 Forbidden"),
                Exception("403 Forbidden"),
                Mock(status_code=200, content=b'<html></html>')
            ]
            
            with patch('time.sleep'):  # Don't actually sleep during test
                soup = scraper._make_request('http://test.com', max_retries=3)
            
            # Should retry and eventually succeed
            assert soup is not None
            assert mock_get.call_count == 3
    
    def test_max_retries_exceeded(self, scraper):
        """Test that scraper gives up after max retries"""
        with patch.object(scraper.session, 'get') as mock_get:
            # Always fail
            mock_get.side_effect = Exception("Network error")
            
            with patch('time.sleep'):  # Don't actually sleep during test
                soup = scraper._make_request('http://test.com', max_retries=3)
            
            # Should return None after max retries
            assert soup is None
            assert mock_get.call_count == 3
    
    def test_rate_limiting(self, scraper):
        """Test that rate limiting delays requests"""
        with patch('time.time') as mock_time, \
             patch('time.sleep') as mock_sleep:
            
            # Simulate time passing
            mock_time.side_effect = [0, 0.5, 2.5]  # 0.5s elapsed, need to wait 1.5s more
            
            scraper.last_request_time = 0
            scraper._rate_limit(delay=2.0)
            
            # Should have called sleep with remaining time
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert sleep_time > 0
    
    def test_download_poster(self, scraper, tmp_path):
        """Test poster download"""
        with patch.object(scraper.session, 'get') as mock_get:
            # Mock image data
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'fake_image_data'
            mock_get.return_value = mock_response
            
            # Download to temp file
            save_path = tmp_path / "test_poster.jpg"
            result = scraper.download_poster('http://test.com/poster.jpg', str(save_path))
            
            # Verify
            assert result is True
            assert save_path.exists()
            assert save_path.read_bytes() == b'fake_image_data'
            
            # Verify curl_cffi impersonate used
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['impersonate'] == 'chrome110'
    
    def test_scrape_empty_page(self, scraper):
        """Test scraping page with no movies"""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<html><body></body></html>'
            mock_get.return_value = mock_response
            
            movies = scraper.scrape_browse_page(page=1)
            
            # Should return empty list, not crash
            assert movies == []
    
    def test_build_browse_url_with_filters(self, scraper):
        """Test URL building with filters"""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<html><body></body></html>'
            mock_get.return_value = mock_response
            
            scraper.scrape_browse_page(page=2, genre='action', quality='1080p', year='2024')
            
            # Check URL contains filters
            called_url = mock_get.call_args[0][0]
            assert 'page=2' in called_url
            assert 'genre=action' in called_url
            assert 'quality=1080p' in called_url
            assert 'year=2024' in called_url
