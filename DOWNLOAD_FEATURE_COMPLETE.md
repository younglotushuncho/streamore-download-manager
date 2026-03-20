# YTS Movie Monitor - Download Feature Implementation

## ✅ COMPLETED FEATURES

### 1. **Backend API Enhancement**
- **New Endpoint**: `/api/movie/<movie_id>/fetch-torrents` (POST)
  - Fetches fresh torrent data from YTS website in real-time
  - Scrapes the movie detail page to get latest magnet links and torrent files
  - Updates database with fresh torrent information
  - Returns torrent quality, size, magnet_link, and torrent_url

### 2. **Frontend API Client**
- Added `fetch_movie_torrents(movie_id)` method
- Connects to backend to retrieve real-time torrent data

### 3. **Movie Details Dialog Enhancements**

#### UI Components:
- ✅ Title + Synopsis display
- ✅ Description text area
- ✅ Available qualities list with sizes
- ✅ **4 Action Buttons**:
  1. **Download Selected** - Opens magnet in torrent client + notifies backend
  2. **Copy Magnet Link** - Copies magnet to clipboard
  3. **Open Magnet** - Opens magnet directly in system torrent client
  4. **Download .torrent** - Downloads .torrent file (with magnet fallback)
- ✅ **🔄 Refresh Torrents Button** - Fetches fresh data from YTS website
- ✅ Status label with color-coded feedback
- ✅ Magnet link preview (truncated for readability)

#### Functionality:
- ✅ **Auto-fetch torrents**: If movie has no torrents in DB, automatically fetch from YTS
- ✅ **Manual refresh**: Click 🔄 button to get latest torrents from website
- ✅ **Smart quality selection**: 
  - Click any quality to select it
  - Double-click to immediately start download
  - Buttons enable/disable based on selection
- ✅ **Magnet link extraction**: Pulls magnet links from YTS in real-time
- ✅ **System integration**: Opens magnets/torrents with default torrent client
- ✅ **Download tracking**: Notifies backend when download starts
- ✅ **Downloads tab integration**: Adds entry to Downloads list when download starts

#### Error Handling:
- ✅ Connection errors with backend
- ✅ Missing torrent data
- ✅ Failed YTS scraping
- ✅ System client not installed
- ✅ Invalid/missing magnet links

### 4. **Downloads Tab**
- ✅ Downloads list widget
- ✅ Refresh button to fetch from backend
- ✅ Clear completed button
- ✅ Auto-refresh on app startup
- ✅ Real-time updates when downloads start from dialog

## 🔄 WORKFLOW

### User clicks a movie → Opens dialog:
1. Dialog loads movie from database
2. If no torrents found → **Auto-fetch from YTS website**
3. Display list of available qualities with sizes
4. User selects a quality (720p, 1080p, 4K, etc.)
5. Magnet link preview appears at bottom

### User wants to download:
**Option 1: Quick download**
- Double-click the quality → Immediately opens in torrent client

**Option 2: Explicit actions**
- Click "Download Selected" → Opens magnet + tracks in backend
- Click "Open Magnet" → Opens magnet directly
- Click "Download .torrent" → Downloads .torrent file
- Click "Copy Magnet Link" → Copies to clipboard for manual use

### Fresh torrent data:
- Click **🔄 Refresh Torrents** button
- Scrapes YTS website in real-time
- Updates quality list with latest torrents
- Shows status: "✓ Loaded X torrents from YTS"

## 🎯 KEY FEATURES

### Real-Time Scraping
- Uses curl_cffi with browser impersonation to bypass Cloudflare
- Fetches torrents directly from YTS website
- No reliance on stale database data
- Updates database automatically

### Smart Fallbacks
- No torrents in DB? → Auto-fetch from website
- No .torrent file? → Use magnet link
- Torrent client fails? → Show helpful error message

### User Experience
- Color-coded status messages (blue=info, green=success, orange=warning, red=error)
- Tooltips on buttons
- Magnet preview (first 80 chars)
- Disabled buttons when no selection
- Double-click for quick download

## 📁 FILES MODIFIED

1. **backend/app.py**
   - Added `/api/movie/<movie_id>/fetch-torrents` endpoint
   - Integrates with YTS scraper for real-time data

2. **frontend/utils/api_client.py**
   - Added `fetch_movie_torrents()` method

3. **frontend/ui/movie_details.py**
   - Complete rewrite with clean, well-indented code
   - Added all download buttons and handlers
   - Implemented auto-fetch and manual refresh
   - Enhanced error handling and UX feedback

4. **frontend/ui/main_window.py**
   - Fixed indentation in downloads tab
   - Added downloads list widget
   - Implemented refresh/clear handlers

## 🚀 USAGE INSTRUCTIONS

### For Users:
1. **Start Backend**: `python backend/app.py`
2. **Start Frontend**: `python frontend/main.py`
3. **Click any movie** to open details
4. **Select a quality** from the list
5. **Click Download Selected** or double-click quality
6. **Your torrent client opens automatically!**

### Requirements:
- Python 3.8+
- PyQt6
- Flask
- curl_cffi (for Cloudflare bypass)
- A torrent client installed (qBittorrent, uTorrent, Transmission, etc.)

## 🔧 TECHNICAL DETAILS

### Magnet Link Format:
```
magnet:?xt=urn:btih:[HASH]&dn=[NAME]&tr=[TRACKERS]
```

### System Commands:
- **Windows**: `start magnet:...` or `start http://...`
- **macOS**: `open magnet:...` or `open http://...`
- **Linux**: `xdg-open magnet:...` or `xdg-open http://...`

### API Endpoint Example:
```python
POST /api/movie/dfb4a60e1b4b/fetch-torrents

Response:
{
  "success": true,
  "torrents": [
    {
      "quality": "1080p",
      "size": "1.8GB",
      "magnet_link": "magnet:?xt=urn:btih:...",
      "torrent_url": "https://yts.mx/torrent/download/..."
    }
  ],
  "movie": { ... }
}
```

## ✨ HIGHLIGHTS

- ✅ **Zero configuration** - Works out of the box
- ✅ **Real-time data** - Always fetches latest torrents
- ✅ **Smart fallbacks** - Never leaves user stuck
- ✅ **Cross-platform** - Windows, macOS, Linux
- ✅ **Clean UI** - Dark theme, intuitive controls
- ✅ **Robust error handling** - Clear user feedback
- ✅ **Integration ready** - Backend tracking for future features

## 🎬 DEMO SCENARIO

1. User opens app → sees movie grid
2. Clicks "Super Shark" → dialog opens
3. Dialog auto-fetches: "Fetching torrents from YTS..."
4. Shows: "✓ Loaded 2 torrents from YTS"
5. Quality list displays:
   - 720p - 850MB
   - 1080p - 1.8GB
6. User selects "1080p"
7. Preview shows: `magnet:?xt=urn:btih:ABC123...`
8. User clicks "Download Selected"
9. qBittorrent opens with the torrent
10. Status: "Started download: 1080p"
11. Downloads tab shows: "Super Shark — 1080p — started"

## 🔮 FUTURE ENHANCEMENTS (Not Yet Implemented)

- Progress tracking in Downloads tab
- Pause/resume/cancel downloads
- Download speed monitoring
- Automatic subtitle download
- Quality preference saving
- Batch downloads
- Integration with media library managers

---

**Status**: ✅ FULLY FUNCTIONAL AND TESTED
**Last Updated**: February 4, 2026
