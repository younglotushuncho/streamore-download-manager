"""Check if .torrent file was downloaded"""
import os
from pathlib import Path
import time

downloads_folder = Path.home() / "Downloads"

print(f"🔍 Checking Downloads folder: {downloads_folder}\n")
print("=" * 60)
print("Looking for recent .torrent files...\n")

# Get all .torrent files
torrent_files = list(downloads_folder.glob("*.torrent"))

if not torrent_files:
    print("❌ No .torrent files found in Downloads folder")
    print("\nPossible reasons:")
    print("  1. Browser blocked the download")
    print("  2. Browser is asking for permission (check browser window)")
    print("  3. File downloaded to different location")
    print("  4. YTS website blocked the download")
    print("\n💡 Try opening this URL manually in browser:")
    print("  https://yts.bz/torrent/download/4ECA6CD134DA7DCEA2B3B844E2AA0D1FFE9D05111")
else:
    print(f"✓ Found {len(torrent_files)} .torrent file(s):\n")
    
    # Sort by modification time (newest first)
    torrent_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    for i, file in enumerate(torrent_files[:5], 1):  # Show last 5
        stat = file.stat()
        mod_time = time.ctime(stat.st_mtime)
        size = stat.st_size
        
        # Check if file is recent (within last 5 minutes)
        age_seconds = time.time() - stat.st_mtime
        is_recent = age_seconds < 300  # 5 minutes
        
        status = "🆕 RECENT!" if is_recent else ""
        print(f"{i}. {file.name} {status}")
        print(f"   Modified: {mod_time}")
        print(f"   Size: {size:,} bytes")
        print(f"   Age: {int(age_seconds)} seconds ago")
        print()
    
    print("=" * 60)
    print("\n💡 To add to qBittorrent:")
    print("  1. Find the .torrent file above")
    print("  2. Double-click it OR drag to qBittorrent window")
    print("  3. Click OK in 'Add torrent' dialog")
    print("  4. Movie starts downloading!")
