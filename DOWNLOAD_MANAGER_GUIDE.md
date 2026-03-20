# YTS Movie Monitor - Quick Start Guide

## 🚀 Quick Start

### 1. Start Backend Services
```powershell
.\scripts\start_services.ps1
```

This will:
- Start aria2c download daemon
- Start Flask backend API
- Verify connectivity

### 2. Start Frontend Application
```powershell
python -m frontend.main
```

### 3. Download a Movie
1. Browse or search for movies in the main window
2. Click on a movie card to open details
3. Select quality and click **"Download Selected"**
4. Switch to the **"Downloads"** tab to see live progress!

---

## 📥 Download Manager Features

### What You Get:
✅ **Live Progress Tracking** - Real-time download progress with speed and ETA  
✅ **Download Controls** - Pause, Resume, Cancel any download  
✅ **Auto-Refresh** - Updates every 2 seconds automatically  
✅ **aria2 Status** - Monitor daemon health and statistics  
✅ **Peer/Seed Count** - See swarm health for each torrent  

### Download Manager UI:
- **Left Panel**: List of all downloads with progress bars
- **Right Panel**: aria2 daemon status and statistics

### Download States:
- 🟢 **Downloading** - Active download in progress
- 🟡 **Queued** - Waiting to start
- ⏸️ **Paused** - Download paused by user
- ✅ **Completed** - Download finished
- ❌ **Error** - Download failed

---

## 🔧 How It Works

### Architecture:
```
Frontend (PyQt6)
    ↓
Backend API (Flask)
    ↓
aria2 Manager (JSON-RPC)
    ↓
aria2c Daemon
    ↓
BitTorrent Network
```

### Data Flow:
1. **User clicks "Download"** in movie details
2. **Frontend** calls `POST /api/download/start` with magnet link
3. **Backend** adds magnet to aria2 via JSON-RPC
4. **aria2** returns a GID (download ID)
5. **Backend** saves download to database
6. **Background poller** queries aria2 every 5s for status updates
7. **Frontend** refreshes downloads list every 2s
8. **Progress bars** update in real-time!

---

## 📁 File Locations

- **Database**: `data/movies.db`
- **Downloads**: `E:\movie_downloads\`
- **Posters Cache**: `data/cache/posters/`
- **Backend Logs**: Console output
- **aria2 Logs**: `E:\movie_downloads\aria2_cli.log`

---

## 🎯 API Endpoints

### Health & Status
- `GET /api/health` - Backend health check
- `GET /api/aria2/status` - aria2 daemon status

### Downloads
- `POST /api/download/start` - Start a new download
- `GET /api/downloads` - List all downloads
- `POST /api/download/{id}/pause` - Pause download
- `POST /api/download/{id}/resume` - Resume download
- `POST /api/download/{id}/cancel` - Cancel download

### Movies
- `GET /api/movies` - List movies (with filters)
- `GET /api/movie/{id}` - Get movie details
- `POST /api/movie/{id}/fetch-torrents` - Refresh torrent links

---

## 🐛 Troubleshooting

### Downloads not appearing?
1. Check backend logs for errors
2. Verify aria2 is running: `tasklist /FI "IMAGENAME eq aria2c.exe"`
3. Test aria2 RPC: `Invoke-RestMethod -Uri http://127.0.0.1:5000/api/aria2/status`
4. Check download manager auto-refresh is ON

### aria2 not starting?
1. Verify aria2c.exe exists in `./bin/` folder
2. Check port 6800 is not in use: `netstat -ano | findstr :6800`
3. Try manual start: `.\bin\aria2c.exe --version`

### Backend connection failed?
1. Verify backend is running on port 5000
2. Check firewall isn't blocking localhost
3. Restart services: `.\scripts\start_services.ps1`

---

## 🛠️ Configuration

Edit `backend/config.py` to customize:

```python
# Download settings
DOWNLOAD_PATH = 'E:/movie_downloads'  # Where files are saved
MAX_CONCURRENT_DOWNLOADS = 3          # Max simultaneous downloads
DOWNLOAD_POLL_INTERVAL_SECONDS = 5    # Status update frequency

# Backend API
FLASK_HOST = '127.0.0.1'
FLASK_PORT = 5000
```

---

## 📊 Testing

Run the integration test to verify everything works:

```powershell
python scripts/test_integration.py
```

This will test:
- ✓ Backend health
- ✓ aria2 connectivity
- ✓ Download start
- ✓ Download listing

---

## 🎉 Success!

Your download manager is now fully integrated and working!

**Next steps:**
- Browse movies and start downloading
- Watch live progress in the Downloads tab
- Enable auto-refresh for real-time updates
- Check aria2 status in the right sidebar

**Enjoy your automated movie downloads! 🍿**
