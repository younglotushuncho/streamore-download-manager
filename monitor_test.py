"""Monitor frontend logs in real-time"""
import time

print("""
╔══════════════════════════════════════════════════════════╗
║  📊 MONITORING FRONTEND - Testing Download Priority      ║
╚══════════════════════════════════════════════════════════╝

✅ Frontend is running!

📝 INSTRUCTIONS:
   1. Click any movie with torrents (e.g., Super Shark)
   2. Select a quality (720p or 1080p)
   3. Click "Download Selected" button
   
🔍 WATCH FOR:
   → "Downloading .torrent file: https://yts.bz/torrent/download/..."
   → "Successfully opened .torrent file for download"
   → Browser should open and download .torrent file
   
⏱️  Monitoring logs for next 60 seconds...
   (Check the other terminal for live log output)
""")

print("Waiting for you to test the download button...")
print("Press Ctrl+C when done.\n")

try:
    for i in range(60):
        time.sleep(1)
        print(f"\rMonitoring... {60-i}s remaining", end="", flush=True)
except KeyboardInterrupt:
    print("\n\n✓ Monitoring stopped.")

print("""
╔══════════════════════════════════════════════════════════╗
║  📋 EXPECTED LOG ENTRIES                                  ║
╚══════════════════════════════════════════════════════════╝

When you click "Download Selected":

1. "Downloading .torrent file: https://yts.bz/torrent/download/..."
2. "Opening target via os.startfile: https://yts.bz/torrent/..."
3. "Successfully opened .torrent file for download: 1080p"
4. "Notified backend: Super Shark - 1080p"
5. "Added to downloads list: Super Shark - 1080p"

If you see these logs → .torrent download worked! ✓
If you see "fallback to magnet" → .torrent failed, trying magnet

Check the other terminal window for actual log output.
""")
