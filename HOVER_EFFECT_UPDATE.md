# Movie Card Hover Effect & Poster Loading - Update

## ✅ What Was Added

### 1. Poster Image Loading
- **Automatic download** from YTS poster URLs
- Downloads posters when you scrape/filter movies
- Shows poster images instead of just "📽️" icon
- Fallback to icon if download fails

### 2. Hover Overlay Effect (Like YTS Website)
When you hover your mouse over a movie card:
- **Dark overlay** appears with green border
- **Rating** displayed at top (⭐ 5.2 / 10)
- **Genres** shown in middle (Action, Adventure)
- **"View Details" button** at bottom (green button)
- Click anywhere on card or button to open details

### 3. Movie Info Below Cards
- **Title** displayed below poster
- **Year** shown under title
- Matches YTS website layout

## 🎨 Visual Features

### Card Design:
- **Size**: 170×250px (larger, better for posters)
- **Border**: 2px solid with rounded corners
- **Normal state**: Dark gray border
- **Hover state**: Bright green border (#6ac045)

### Overlay Design:
- **Background**: Semi-transparent black (rgba(0,0,0,180))
- **Border**: 3px green (#6ac045)
- **Rating**: Large white text with star icon
- **Genres**: White text, centered
- **Button**: Green background, white text

### Layout:
- **Grid**: 6 columns
- **Spacing**: Proper spacing between cards
- **Pagination**: 30 movies per page

## 🚀 How to Test

### The app is already running with the new design!

1. **Filter for movies with posters:**
   - Select: **Genre = Animation**, **Year = 2024**
   - Click **Filter**
   - Wait for ~113 movies to load with posters

2. **Test hover effect:**
   - Move your mouse over any movie card
   - Green border and overlay should appear
   - Shows rating, genres, and "View Details" button
   - Move mouse away - overlay disappears

3. **Test pagination:**
   - Click **Next »** at bottom
   - See next 30 movies
   - All with posters loaded

4. **Click to view details:**
   - Hover over a card
   - Click "View Details" button
   - Or click anywhere on the card
   - Movie details dialog opens

## 📁 Files Changed

### `frontend/ui/main_window.py`
**MovieCard class completely rewritten:**
- Added `load_poster()` method to download images
- Added overlay widget with rating/genres/button
- Added `enterEvent()` and `leaveEvent()` for hover
- Increased card size to 170×250px
- Added poster downloading via requests

**MainWindow changes:**
- `display_movies()` now adds title/year labels below cards
- Each movie takes 2 grid rows (card + info)
- Better spacing and alignment

### New Imports Added:
```python
from io import BytesIO
import requests
from PyQt6.QtGui import QImage
```

## 🎯 Expected Behavior

### On Load:
1. Cards show "📽️ Loading..." initially
2. Posters download automatically from YTS URLs
3. Posters appear as they load
4. Title and year appear below each card

### On Hover:
1. Green border appears around card
2. Dark overlay slides over poster
3. Rating shows at top (⭐ X / 10)
4. Genres show in middle
5. Green "View Details" button at bottom
6. Cursor changes to pointer

### On Click:
1. Click card or "View Details" button
2. Movie details dialog opens
3. Can download torrents from there

## 🐛 Troubleshooting

### If posters don't load:
- Check internet connection
- YTS might be slow to respond
- Fallback icon (📽️) will show
- Hover overlay still works

### If hover doesn't work:
- Make sure frontend was restarted
- Check terminal for errors
- Try hovering slowly over card

### If cards look wrong:
- Restart frontend: Close GUI and run `python -m frontend.main`
- Clear cache if needed

## 🔄 Quick Restart

If you need to restart after this update:
```powershell
# Close current frontend window, then:
cd "E:\Softwares\projects\movie project"
python -m frontend.main
```

Backend doesn't need restart (no changes).

## 📸 Matching YTS Website Design

Your app now looks like the YTS website:
- ✅ Poster images load automatically
- ✅ Hover shows green border
- ✅ Overlay with rating/genres/button
- ✅ Title and year below card
- ✅ Clean, modern design
- ✅ Pagination for many results

**Try it now - hover over any movie card!**
