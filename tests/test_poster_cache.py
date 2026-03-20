"""
Unit tests for poster cache
"""
import pytest
import os
from pathlib import Path
from backend.poster_cache import PosterCache


@pytest.fixture
def temp_cache(tmp_path):
    """Create temporary cache for testing"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return PosterCache(cache_dir=str(cache_dir), max_size_mb=1)  # 1MB limit for testing


class TestPosterCache:
    """Test suite for poster cache"""
    
    def test_cache_initialization(self, temp_cache):
        """Test cache initializes correctly"""
        assert os.path.exists(temp_cache.cache_dir)
        assert temp_cache.max_size_mb == 1
    
    def test_get_cache_filename(self, temp_cache):
        """Test filename generation from URL"""
        url1 = "http://example.com/poster1.jpg"
        url2 = "http://example.com/poster2.jpg"
        
        filename1 = temp_cache.get_cache_filename(url1)
        filename2 = temp_cache.get_cache_filename(url2)
        
        # Should be different hashes
        assert filename1 != filename2
        
        # Should be consistent
        assert filename1 == temp_cache.get_cache_filename(url1)
        
        # Should end with .jpg
        assert filename1.endswith('.jpg')
    
    def test_cache_miss(self, temp_cache):
        """Test cache miss returns None"""
        url = "http://example.com/nonexistent.jpg"
        result = temp_cache.get_cached_path(url)
        assert result is None
    
    def test_add_to_cache(self, temp_cache):
        """Test adding image to cache"""
        url = "http://example.com/poster.jpg"
        image_data = b"fake_image_data_12345"
        
        filepath = temp_cache.add_to_cache(url, image_data)
        
        # Should return path
        assert filepath is not None
        assert os.path.exists(filepath)
        
        # Should be able to read back
        with open(filepath, 'rb') as f:
            assert f.read() == image_data
    
    def test_cache_hit(self, temp_cache):
        """Test cache hit returns correct path"""
        url = "http://example.com/poster.jpg"
        image_data = b"fake_image_data"
        
        # Add to cache
        temp_cache.add_to_cache(url, image_data)
        
        # Should get cache hit
        cached_path = temp_cache.get_cached_path(url)
        assert cached_path is not None
        assert os.path.exists(cached_path)
    
    def test_get_cache_size(self, temp_cache):
        """Test cache size calculation"""
        # Empty cache
        assert temp_cache.get_cache_size() == 0
        
        # Add some data
        url1 = "http://example.com/poster1.jpg"
        image_data1 = b"x" * 1024  # 1KB
        temp_cache.add_to_cache(url1, image_data1)
        
        size_mb = temp_cache.get_cache_size()
        assert size_mb > 0
        assert size_mb < 0.01  # Should be ~0.001MB
    
    def test_clean_old_posters(self, temp_cache):
        """Test cleaning old posters when cache exceeds limit"""
        # Add multiple files to exceed 1MB limit
        for i in range(5):
            url = f"http://example.com/poster{i}.jpg"
            image_data = b"x" * (300 * 1024)  # 300KB each = 1.5MB total
            temp_cache.add_to_cache(url, image_data)
        
        # Cache should have cleaned itself
        size_mb = temp_cache.get_cache_size()
        assert size_mb < temp_cache.max_size_mb
        
        # Should have fewer than 5 files
        file_count = len(os.listdir(temp_cache.cache_dir))
        assert file_count < 5
    
    def test_clear_cache(self, temp_cache):
        """Test clearing entire cache"""
        # Add some files
        for i in range(3):
            url = f"http://example.com/poster{i}.jpg"
            temp_cache.add_to_cache(url, b"data")
        
        # Clear cache
        temp_cache.clear_cache()
        
        # Should be empty
        assert len(os.listdir(temp_cache.cache_dir)) == 0
        assert temp_cache.get_cache_size() == 0
    
    def test_get_stats(self, temp_cache):
        """Test cache statistics"""
        # Add some files
        for i in range(3):
            url = f"http://example.com/poster{i}.jpg"
            temp_cache.add_to_cache(url, b"x" * 100000)  # ~100KB each
        
        stats = temp_cache.get_stats()
        
        assert stats['file_count'] == 3
        assert stats['size_mb'] > 0
        assert stats['max_size_mb'] == 1
        assert 0 <= stats['usage_percent'] <= 100
