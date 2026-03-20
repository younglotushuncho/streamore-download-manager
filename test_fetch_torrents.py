"""Test the fetch-torrents API endpoint"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from frontend.utils.api_client import APIClient

def test_fetch_torrents():
    api = APIClient()
    
    # Check health
    if not api.health_check():
        print("❌ Backend not available")
        return
    
    print("✓ Backend connected")
    
    # Get first movie
    movies = api.get_movies(limit=1)
    if not movies:
        print("❌ No movies in database")
        return
    
    movie = movies[0]
    movie_id = movie['id']
    title = movie['title']
    
    print(f"\n📽️  Testing with: {title} (ID: {movie_id})")
    print(f"   Current torrents: {len(movie.get('torrents', []))}")
    
    # Fetch fresh torrents
    print("\n🔄 Fetching fresh torrents from YTS...")
    result = api.fetch_movie_torrents(movie_id)
    
    if not result:
        print("❌ Failed to fetch torrents")
        return
    
    torrents = result.get('torrents', [])
    print(f"✓ Fetched {len(torrents)} torrents")
    
    for t in torrents:
        quality = t.get('quality', 'Unknown')
        size = t.get('size', 'Unknown')
        has_magnet = bool(t.get('magnet_link'))
        has_torrent = bool(t.get('torrent_url'))
        
        print(f"   - {quality} ({size})")
        print(f"     Magnet: {'✓' if has_magnet else '✗'}")
        print(f"     Torrent file: {'✓' if has_torrent else '✗'}")
        
        if has_magnet:
            magnet = t.get('magnet_link')
            print(f"     Magnet preview: {magnet[:60]}...")

if __name__ == '__main__':
    test_fetch_torrents()
