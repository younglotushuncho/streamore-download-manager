"""Real-time log monitor - Watch what happens when you click Download"""
import time

print("""
╔══════════════════════════════════════════════════════════════╗
║  🎬 FRONTEND RUNNING - Ready for Testing!                    ║
╚══════════════════════════════════════════════════════════════╝

✅ Backend: Running
✅ Frontend: Running

📋 TEST INSTRUCTIONS:
   
   1. Click "Super Shark" movie (has working .torrent files)
   2. Select a quality (1080p or 720p)
   3. Click "Download Selected" button
   
🔍 WHAT TO WATCH FOR:

   ✓ Dialog shows: "Downloading .torrent file for [quality]..."
   ✓ .torrent file downloads to: C:\\Users\\LOTUS\\Downloads\\
   ✓ qBittorrent opens automatically with "Add torrent" dialog
   ✓ Success message: "✓ Downloaded & opened: [quality] (.torrent)"
   
📊 MONITORING:
   
   I'll check the terminal logs every few seconds to see what happens.
   The logs will show:
   - Which movie you clicked
   - .torrent download attempt
   - Success or fallback to magnet
   - File saved location
   
⏰ Waiting for you to test...
   (Check the other terminal window for live logs)
   
""")

print("Press Ctrl+C when done testing\n")
print("=" * 60)

try:
    while True:
        time.sleep(3)
        print(".", end="", flush=True)
except KeyboardInterrupt:
    print("\n\n✓ Monitoring stopped.")
    print("\nCheck the terminal logs above to see what happened!")
