from backend.database import Database

db = Database()
movie = db.get_movie('dfb4a60e1b4b')  # Super Shark ID

if movie:
    print(f"Movie: {movie.title}")
    print(f"YTS URL: {movie.yts_url}")
    print(f"Torrents: {len(movie.torrents)}")
    
    for t in movie.torrents:
        print(f"\n  Quality: {t.quality}")
        print(f"  Size: {t.size}")
        print(f"  Torrent URL: {t.torrent_url}")
        if t.torrent_url:
            hash_part = t.torrent_url.split('/')[-1]
            print(f"  Hash: {hash_part}")
            print(f"  Hash length: {len(hash_part)}")
else:
    print("Movie not found in database")
