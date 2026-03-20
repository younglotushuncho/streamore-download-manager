"""
Fix torrent URLs in database - trim hashes to exactly 40 characters
"""
from backend.database import Database
import re

db = Database()

print("Scanning database for movies with incorrect torrent hashes...")
print("=" * 80)

fixed_count = 0
movies = db.get_all_movies()

for movie in movies:
    movie_fixed = False
    
    for torrent in movie.torrents:
        if torrent.torrent_url and '/torrent/download/' in torrent.torrent_url:
            # Extract hash
            parts = torrent.torrent_url.split('/torrent/download/')
            if len(parts) == 2:
                hash_part = parts[1]
                
                if len(hash_part) != 40:
                    print(f"\n{movie.title} - {torrent.quality}")
                    print(f"  Current hash ({len(hash_part)} chars): {hash_part}")
                    
                    # Fix it
                    correct_hash = hash_part[:40]
                    correct_url = f"{parts[0]}/torrent/download/{correct_hash}"
                    
                    print(f"  Correct hash (40 chars): {correct_hash}")
                    print(f"  Old URL: {torrent.torrent_url}")
                    print(f"  New URL: {correct_url}")
                    
                    # Update in database
                    torrent.torrent_url = correct_url
                    movie_fixed = True
                    fixed_count += 1

    if movie_fixed:
        # Save changes
        db.add_movie(movie)
        print(f"  ✓ Updated {movie.title}")

print("\n" + "=" * 80)
print(f"Fixed {fixed_count} torrent URLs")

# Verify Super Shark
print("\nVerifying Super Shark:")
movie = db.get_movie('dfb4a60e1b4b')
if movie:
    for t in movie.torrents:
        print(f"  {t.quality}: {t.torrent_url}")
        hash_part = t.torrent_url.split('/')[-1]
        print(f"    Hash length: {len(hash_part)} ({'✓ OK' if len(hash_part) == 40 else '❌ WRONG'})")
