"""
Poster cache manager - caches downloaded poster images
"""
import os
import hashlib
import logging
from pathlib import Path
from typing import Optional

from backend.config import Config

logger = logging.getLogger(__name__)


class PosterCache:
    """Manages poster image caching with size limits"""
    
    def __init__(self, cache_dir: str = None, max_size_mb: int = None):
        self.cache_dir = cache_dir or Config.POSTER_CACHE_DIR
        self.max_size_mb = max_size_mb or Config.MAX_CACHE_SIZE_MB
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"PosterCache initialized: {self.cache_dir} (max {self.max_size_mb}MB)")
    
    def get_cache_filename(self, url: str) -> str:
        """
        Generate cache filename from URL using MD5 hash
        
        Args:
            url: Poster image URL
        
        Returns:
            Filename (hash.jpg)
        """
        hash_str = hashlib.md5(url.encode()).hexdigest()
        return f"{hash_str}.jpg"
    
    def get_cached_path(self, url: str) -> Optional[str]:
        """
        Check if poster exists in cache
        
        Args:
            url: Poster image URL
        
        Returns:
            Full path to cached file if exists, None otherwise
        """
        filename = self.get_cache_filename(url)
        filepath = os.path.join(self.cache_dir, filename)
        
        if os.path.exists(filepath):
            logger.debug(f"Cache HIT: {url}")
            return filepath
        
        logger.debug(f"Cache MISS: {url}")
        return None
    
    def add_to_cache(self, url: str, image_data: bytes) -> str:
        """
        Save image to cache
        
        Args:
            url: Poster image URL
            image_data: Image binary data
        
        Returns:
            Full path to saved file
        """
        filename = self.get_cache_filename(url)
        filepath = os.path.join(self.cache_dir, filename)
        
        # Write image
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        logger.info(f"Added to cache: {filename} ({len(image_data)} bytes)")
        
        # Check cache size and clean if needed
        current_size = self.get_cache_size()
        if current_size > self.max_size_mb:
            logger.warning(f"Cache size {current_size:.1f}MB exceeds limit {self.max_size_mb}MB")
            self.clean_old_posters()
        
        return filepath
    
    def get_cache_size(self) -> float:
        """
        Calculate total cache size in MB
        
        Returns:
            Total size in MB
        """
        total_size = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.error(f"Error calculating cache size: {e}")
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def clean_old_posters(self, target_mb: float = None):
        """
        Remove oldest files until cache is under target size
        
        Args:
            target_mb: Target size in MB (defaults to 80% of max_size_mb)
        """
        target_mb = target_mb or (self.max_size_mb * 0.8)
        
        logger.info(f"Cleaning cache to {target_mb}MB...")
        
        # Get all files with modification times
        files = []
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    mtime = os.path.getmtime(filepath)
                    files.append((filepath, mtime))
        except Exception as e:
            logger.error(f"Error listing cache files: {e}")
            return
        
        # Sort by modification time (oldest first)
        files.sort(key=lambda x: x[1])
        
        # Delete oldest files until under target
        deleted_count = 0
        while self.get_cache_size() > target_mb and files:
            filepath, _ = files.pop(0)
            try:
                os.remove(filepath)
                deleted_count += 1
                logger.debug(f"Removed old poster: {os.path.basename(filepath)}")
            except Exception as e:
                logger.error(f"Error removing file {filepath}: {e}")
        
        final_size = self.get_cache_size()
        logger.info(f"Cache cleaned: removed {deleted_count} files, now {final_size:.1f}MB")
    
    def clear_cache(self):
        """Remove all cached files"""
        logger.warning("Clearing entire poster cache...")
        deleted_count = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    deleted_count += 1
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
        
        logger.info(f"Cache cleared: removed {deleted_count} files")
    
    def get_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        try:
            file_count = len([f for f in os.listdir(self.cache_dir) 
                            if os.path.isfile(os.path.join(self.cache_dir, f))])
            size_mb = self.get_cache_size()
            
            return {
                'file_count': file_count,
                'size_mb': round(size_mb, 2),
                'max_size_mb': self.max_size_mb,
                'usage_percent': round((size_mb / self.max_size_mb) * 100, 1)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'file_count': 0,
                'size_mb': 0,
                'max_size_mb': self.max_size_mb,
                'usage_percent': 0
            }


# Singleton instance
_poster_cache_instance = None

def get_poster_cache() -> PosterCache:
    """Get poster cache singleton instance"""
    global _poster_cache_instance
    if _poster_cache_instance is None:
        _poster_cache_instance = PosterCache()
    return _poster_cache_instance
