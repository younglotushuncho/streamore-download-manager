# Download System Updated - .torrent File Priority

## Date: February 5, 2026

## What Changed

### BEFORE:
- Clicking "Download Selected" only opened magnet links
- Magnet links caused "unsupported URL protocol" errors in qBittorrent
- No way to download .torrent files directly

### AFTER:
- **Priority 1**: Downloads .torrent file (opens download URL in browser)
- **Priority 2**: Falls back to magnet link if .torrent unavailable
- Status messages show which method is being used

## How It Works Now

### When You Click "Download Selected":

```
1. Check if .torrent file URL exists
   ├─ YES → Open download URL in browser
   │        → Browser downloads .torrent file
   │        → You drag .torrent to qBittorrent
   │        → Status: "✓ Started download: 720p (.torrent file)"
   │
   └─ NO → Try magnet link
            → Opens in qBittorrent directly
            → Status: "✓ Started download: 720p (magnet)"
```

## Why .torrent Files Are Better

### Advantages:
✅ **No Protocol Handler Issues**
   - Works on all Windows configurations
   - No "unsupported URL protocol [libtorrent:24]" errors
   
✅ **Faster Add to Client**
   - qBittorrent reads .torrent instantly
   - No need to fetch metadata from trackers
   
✅ **Includes Extra Files**
   - Subtitles (.srt files)
   - YTS branding images
   - Readme files
   
✅ **More Reliable**
   - Direct download, no protocol associations needed
   - Works even if magnet handler is broken

### Example .torrent File Contents:
```
We Bury the Dead (2024) [720p] [WEBRip] [YTS.BZ].torrent
├── We.Bury.The.Dead.2024.720p.WEBRip.x264.AAC-[YTS.BZ].mp4 (914 MB)
├── We.Bury.The.Dead.2024.720p.WEBRip.x264.AAC-[YTS.BZ].srt (64 KB)
├── YTS.BZ - Official site.jpg (38 KB)
└── YTSYifyUP... (TOR).txt (840 bytes)
```

## Testing

### Test Data (Super Shark):
- **1080p**: 
  - .torrent URL: `https://yts.bz/torrent/download/648CAF...`
  - Magnet: `magnet:?xt=urn:btih:648CAF...`
  - **Will use**: .torrent file ✓

- **720p**:
  - .torrent URL: `https://yts.bz/torrent/download/5826DC...`
  - Magnet: `magnet:?xt=urn:btih:5826DC...`
  - **Will use**: .torrent file ✓

### To Test:
1. Launch frontend: `python -m frontend.main`
2. Click any movie
3. Select a quality
4. Click "Download Selected"
5. **Expected**: Browser downloads .torrent file
6. Drag .torrent file to qBittorrent
7. Movie starts downloading ✓

## Button Functions Updated

| Button | Old Behavior | New Behavior |
|--------|-------------|--------------|
| **Download Selected** | Opens magnet | **Opens .torrent URL** → fallback to magnet |
| Copy Magnet Link | Copies magnet | *(unchanged)* |
| Open Magnet | Opens magnet | *(unchanged)* |
| Download .torrent | Opens torrent URL | *(unchanged)* |

## Status Messages

The dialog now shows which method is being used:

- `"Downloading .torrent file for 720p..."` - Download starting
- `"✓ Started download: 720p (.torrent file)"` - .torrent success (green)
- `"⚠ .torrent failed, trying magnet..."` - Fallback warning (orange)
- `"✓ Started download: 720p (magnet)"` - Magnet fallback (blue)
- `"❌ Failed to start download"` - Both failed (red)

## Files Modified

1. `frontend/ui/movie_details.py`
   - Updated `on_download_clicked()` method
   - Added .torrent priority logic
   - Improved status messages

## Next Steps

1. **Test with real frontend** - Make sure .torrent downloads work
2. **Check browser behavior** - Should auto-download or prompt
3. **Verify qBittorrent** - Can add downloaded .torrent files

## Quick Start Command

```powershell
# Start backend (in separate window)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'e:\Softwares\projects\movie project' ; python -m backend.app"

# Start frontend
cd "e:\Softwares\projects\movie project"
python -m frontend.main
```

## Troubleshooting

### If .torrent download doesn't start:
- Check browser download settings
- Some browsers block auto-downloads
- Manually click the download in browser

### If .torrent opens in text editor:
- Windows doesn't know .torrent files
- Right-click → Open with → qBittorrent
- Set qBittorrent as default for .torrent files

### If both methods fail:
- Copy the magnet link manually
- Add to qBittorrent: File → Add torrent link (Ctrl+U)
