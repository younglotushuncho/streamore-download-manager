# 🎬 Quick Start Guide - Download Movies

## ⚡ 3-Step Setup

### 1. Start Backend
```powershell
python backend/app.py
```
Wait for: `Running on http://127.0.0.1:5000`

### 2. Start Frontend
```powershell
python frontend/main.py
```

### 3. Download a Movie!
1. Click any movie poster
2. Select quality (720p, 1080p, etc.)
3. Click **"Download Selected"** or **double-click**
4. Your torrent client opens automatically! 🎉

---

## 🎯 Features You Can Use

### In Movie Details Dialog:

| Button | What It Does |
|--------|-------------|
| **Download Selected** | Opens magnet in your torrent client + tracks download |
| **Copy Magnet Link** | Copies magnet to clipboard for manual use |
| **Open Magnet** | Opens magnet directly in torrent client |
| **Download .torrent** | Downloads the .torrent file to your computer |
| **🔄 Refresh Torrents** | Fetches fresh torrent data from YTS website |

### Pro Tips:
- **Double-click** any quality for instant download
- If no torrents show, click **🔄 Refresh Torrents**
- Magnet preview appears at bottom when you select a quality
- Check **Downloads tab** to see your download list

---

## ❓ Troubleshooting

### "No quality options available"
→ Click the **🔄 Refresh Torrents** button to fetch from YTS

### "Could not open magnet link"
→ Install a torrent client:
- **qBittorrent** (recommended, free, open-source)
- uTorrent
- Transmission
- Deluge

### "Backend not available"
→ Make sure backend is running: `python backend/app.py`

### "Failed to fetch torrents"
→ Check internet connection and YTS website accessibility

---

## 🎥 Example Workflow

```
1. App shows movie grid
2. Click "Inception" poster
3. Dialog opens, shows:
   - Title: "Inception Synopsis"
   - Description: "A thief who steals..."
   - Available Qualities:
     ✓ 720p - 850MB
     ✓ 1080p - 1.8GB
     ✓ 2160p 4K - 6.2GB
4. Click "1080p - 1.8GB"
5. Preview shows: magnet:?xt=urn:btih:ABC123...
6. Click "Download Selected"
7. qBittorrent opens with movie
8. Status: "✓ Started download: 1080p"
9. Check Downloads tab → see "Inception — 1080p — started"
```

---

## 📝 Requirements

✅ Python 3.8+
✅ PyQt6 (for GUI)
✅ Flask (for backend)
✅ curl_cffi (for web scraping)
✅ **A torrent client** (qBittorrent, uTorrent, etc.)

---

**Enjoy downloading movies! 🍿**
