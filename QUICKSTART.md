# YTS Movie Monitor - Quick Start

A desktop application that monitors YTS for new movie releases with integrated torrent downloads.

## ✨ Features

- 🎬 Browse and search YTS movies
- 🔍 Filter by genre, year, quality, rating
- ⬇️ Integrated downloads (stub - libtorrent can be added)
- 🌐 FREE Cloudflare bypass using curl_cffi
- 🎨 Modern dark-themed UI (PyQt6)
- 💾 Poster caching
- 📊 Statistics tracking

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (tested on 3.12)
- Windows 10/11

### Installation

```powershell
# 1. Clone or download this project
cd "E:\Softwares\projects\movie project"

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Install frontend dependencies  
pip install -r frontend/requirements.txt
```

### Running the Application

**Terminal 1 - Start Backend API:**
```powershell
cd "E:\Softwares\projects\movie project"
python backend/app.py
```

The backend will start on `http://127.0.0.1:5000`

**Terminal 2 - Start Frontend UI:**
```powershell
cd "E:\Softwares\projects\movie project"
python frontend/main.py
```

The desktop app will open.

## 📖 Usage

### First Time Setup

1. **Start Backend** - Run `python backend/app.py`
2. **Start Frontend** - Run `python frontend/main.py`
3. **Scrape Movies** - Click "Scrape YTS" button to fetch initial movies
4. **Browse** - Use filters and search to find movies

### Scraping Movies

Click **"Scrape YTS"** button to:
- Fetch latest movies from YTS
- Download and cache posters
- Save to local database

### Filtering Movies

Use the top bar to filter by:
- **Genre** - Action, Comedy, Drama, etc.
- **Year** - 2024, 2023, etc.
- **Quality** - 720p, 1080p, 2160p
- **Search** - Type movie title

### Downloading Movies (Stub)

Currently shows placeholder - full torrent manager requires libtorrent:
```powershell
pip install libtorrent
```

Then implement real download logic in `backend/torrent_manager.py`

## 🗂️ Project Structure

```
movie project/
├── backend/                 # Flask API server
│   ├── app.py              # Main API endpoints
│   ├── scraper.py          # YTS scraper (curl_cffi)
│   ├── poster_cache.py     # Poster caching
│   ├── database.py         # SQLite operations
│   ├── torrent_manager.py  # Download manager (stub)
│   ├── config.py           # Configuration
│   └── requirements.txt
│
├── frontend/               # PyQt6 desktop app
│   ├── main.py            # Entry point
│   ├── ui/
│   │   └── main_window.py # Main window UI
│   ├── utils/
│   │   └── api_client.py  # API client
│   └── requirements.txt
│
├── shared/                 # Shared code
│   ├── models.py          # Data models
│   └── constants.py       # Constants
│
├── tests/                  # Unit tests
│   ├── test_scraper.py
│   └── test_poster_cache.py
│
├── data/                   # Runtime data (created automatically)
│   ├── movies.db          # SQLite database
│   └── cache/             # Cached posters
│
└── downloads/             # Downloaded movies (configurable)
```

## 🧪 Running Tests

```powershell
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_scraper.py -v

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=html
```

## ⚙️ Configuration

Copy `.env.example` to `.env` and customize:

```ini
# YTS Website
YTS_BASE_URL=https://www.yts-official.top

# Scraping
REQUEST_DELAY=2.0
REQUEST_TIMEOUT=15
MAX_RETRIES=3

# Downloads
DOWNLOAD_PATH=E:\Downloads\Movies
MAX_CONCURRENT_DOWNLOADS=3

# API
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```

## 🔧 Technology Stack

### Backend
- **Flask** - REST API
- **curl_cffi** - FREE Cloudflare bypass ⭐
- **BeautifulSoup** - HTML parsing
- **SQLite** - Database
- **SQLAlchemy** - ORM

### Frontend
- **PyQt6** - Desktop GUI
- **requests** - HTTP client

## 📝 Key Features Explained

### FREE Cloudflare Bypass

Uses `curl_cffi` to impersonate Chrome browser:
```python
from curl_cffi import requests

session = requests.Session()
response = session.get(url, impersonate="chrome110")
```

This bypasses Cloudflare **for FREE** without paid proxy services!

### Poster Caching

- Downloads posters once
- Stores with MD5 hash filenames
- Auto-cleans when cache exceeds 500MB
- Serves from cache on subsequent loads

### Rate Limiting

- 2-second delay between requests
- Exponential backoff on errors
- Respects site resources

## 🚧 Known Limitations

1. **Torrent Manager** - Stub implementation only
   - Full libtorrent integration requires additional setup
   - Windows libtorrent binaries can be tricky
   
2. **Movie Details Dialog** - Coming soon
   - Currently shows basic info message
   
3. **Settings Panel** - Coming soon
   - Will allow changing download path, etc.

## 🐛 Troubleshooting

### Backend won't start
```powershell
# Check if dependencies installed
pip list | Select-String "Flask|curl-cffi|beautifulsoup4"

# Reinstall if needed
pip install -r backend/requirements.txt
```

### Frontend won't start
```powershell
# Check PyQt6 installation
pip list | Select-String "PyQt6"

# Reinstall if needed
pip install PyQt6
```

### "Backend Not Available" error
- Make sure backend is running first (`python backend/app.py`)
- Check if port 5000 is available
- Check firewall settings

### No movies showing
- Click "Scrape YTS" to fetch movies first
- Check backend terminal for scraping logs
- Verify YTS site is accessible

### Import errors
```powershell
# Make sure you're in the project root
cd "E:\Softwares\projects\movie project"

# Run from project root
python frontend/main.py
```

## 📊 API Endpoints

See full API documentation (coming soon) or check `backend/app.py`:

- `GET /api/health` - Health check
- `GET /api/stats` - Statistics
- `GET /api/movies` - List movies (with filters)
- `GET /api/movie/<id>` - Get movie details
- `POST /api/scrape` - Trigger scraping
- `GET /api/downloads` - List downloads
- `POST /api/download/start` - Start download

## 🎯 Next Steps

1. **Add libtorrent** - Real torrent downloads
2. **Movie Details Dialog** - Full movie info popup
3. **Settings Panel** - Configurable options
4. **Auto-scraping** - Background scraping every 30 minutes
5. **Notifications** - Desktop alerts
6. **Build Executable** - PyInstaller packaging

## 🔒 Legal Notice

⚠️ **For personal use only**
- Users are responsible for compliance with local laws
- This app does not host or distribute copyrighted content
- Only download content you have legal rights to
- Use a VPN when downloading torrents

## 📧 Support

Check the documentation files:
- `02-DEVELOPMENT-STEPS-FREE.md` - Full build guide
- `CURSOR-GUIDE.md` - Cursor AI usage
- `FREE-CLOUDFLARE-BYPASS.md` - curl_cffi details

## 🎉 Success!

You now have a working YTS Movie Monitor! 

**Current Status:**
- ✅ Database and models
- ✅ YTS scraper with curl_cffi
- ✅ Poster caching
- ✅ Flask REST API
- ✅ PyQt6 desktop UI
- ✅ Movie browsing and filtering
- ⏳ Torrent downloads (stub)

---

**Version**: 1.0.0  
**Date**: February 2026  
**Total Cost**: $0 (100% FREE!)
