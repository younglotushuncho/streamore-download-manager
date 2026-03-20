# YTS Movie Monitor - Multi-Page Scraping & Pagination Update

## What Was Fixed

### Problem
- App was only showing 20 movies (first page) when filtering
- YTS website shows 110+ movies across multiple pages
- No way to navigate through results in the app

### Solution
1. **Backend: Multi-page scraping**
   - Added `max_pages` parameter to `scrape_browse_filtered()`
   - Automatically loops through pages until no more movies found
   - Default: scrapes up to 10 pages (200+ movies)

2. **Frontend: Pagination UI**
   - Added "Previous" and "Next" buttons
   - Shows "Page X of Y (Z total movies)"
   - Displays 30 movies per page (5 rows × 6 columns)
   - All movies are fetched at once, then paginated locally

## How to Restart the App

### Method 1: Double-click the restart script
```
restart_app.bat
```

### Method 2: Manual restart
**Terminal 1 - Backend:**
```powershell
cd "E:\Softwares\projects\movie project"
python -m backend.app
```

**Terminal 2 - Frontend:**
```powershell
cd "E:\Softwares\projects\movie project"
python -m frontend.main
```

## How to Test

1. **Start both services** (use restart_app.bat or manual method)

2. **Test multi-page scraping:**
   - Select: Genre = Animation, Year = 2024, Quality = 720p
   - Click **Filter** button
   - Wait 30-60 seconds (scraping multiple pages)
   - Expected: ~110 movies loaded

3. **Test pagination:**
   - Bottom of window shows: "Page 1 of 4 (110 total)"
   - Click **Next »** to see next 30 movies
   - Click **« Previous** to go back
   - Page info updates as you navigate

4. **Verify all pages scraped:**
   - Check status bar at bottom: "✓ Loaded 110 movies"
   - Use Next button to browse through all 4 pages
   - Each page shows up to 30 movies

## Files Changed

### Backend
- `backend/scraper.py` - Added multi-page loop in `scrape_browse_filtered()`
- `backend/app.py` - Added `max_pages` parameter to API endpoint

### Frontend
- `frontend/utils/api_client.py` - Added `max_pages` parameter
- `frontend/ui/main_window.py`:
  - Added pagination buttons (Previous/Next)
  - Added page info label
  - Added `display_current_page()`, `prev_page()`, `next_page()` methods
  - Stores all movies in `self.all_fetched_movies`
  - Shows 30 movies per page

## Expected Behavior

### Before (OLD):
- Filter: Animation/720p/2024
- Result: 20 movies (only page 1)
- No pagination

### After (NEW):
- Filter: Animation/720p/2024
- Result: ~110 movies (all pages scraped)
- Pagination: Page 1 of 4 (110 total)
- Can navigate with Previous/Next buttons

## Troubleshooting

### If still showing only 20 movies:
1. **Close all Python processes** (both backend and frontend)
2. Run `restart_app.bat` to start fresh
3. Wait for "Backend connection successful" in logs
4. Try the filter again

### If scraping is slow:
- Multi-page scraping takes time (rate limiting between pages)
- Status bar shows: "Fetching all pages from YTS..."
- Wait 30-60 seconds for all pages to load
- Once loaded, pagination is instant (local)

### Backend logs to check:
```
Scraping filtered browse page 1/6
Found 20 movie cards on page 1
Scraping filtered browse page 2/6
Found 20 movie cards on page 2
...
Scraped total of 110 movies across 6 pages
```

## Test Script

Run this to test backend multi-page scraping:
```powershell
python test_multipage_scrape.py
```

Expected output:
```
✓ Total movies scraped: 110
First 15 titles:
 1. ME (2024) - 0.0/10
 2. The Lost Tiger (2024) - 0.0/10
 ...
... and 95 more movies
```
