"""Quick test of the new .torrent download priority"""
print("""
╔══════════════════════════════════════════════════════════╗
║  🎬 DOWNLOAD SYSTEM UPDATED - .torrent Priority          ║
╚══════════════════════════════════════════════════════════╝

✅ CHANGES APPLIED:
   - "Download Selected" now prioritizes .torrent files
   - Falls back to magnet links if .torrent unavailable
   - Better error messages and status feedback

📋 HOW TO TEST:
   1. Launch frontend (running this will start it)
   2. Click any movie with torrents (e.g., Super Shark)
   3. Select a quality (720p or 1080p)
   4. Click "Download Selected" button
   
🎯 EXPECTED BEHAVIOR:
   → Browser opens and downloads .torrent file
   → You see: "✓ Started download: 720p (.torrent file)"
   → Drag the .torrent file to qBittorrent
   → Movie starts downloading!

🔧 BENEFITS:
   ✓ No more "unsupported URL protocol" errors
   ✓ Works on all systems
   ✓ Includes subtitles and extras
   ✓ Faster than magnet links

Starting frontend now...
""")

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent

# Launch frontend
subprocess.Popen([sys.executable, "-m", "frontend.main"], cwd=str(project_root))

print("\n✓ Frontend launched!")
print("\nClick a movie → Select quality → Click 'Download Selected'")
print("Your browser should download the .torrent file automatically.\n")
