# Movie Details Dialog - Simplified Version

## Implementation Summary

### What's Displayed
The dialog now shows **only** the following information:

1. **Title Header**: Movie name followed by " Synopsis" (e.g., "Symbol Synopsis")
2. **Description**: Full movie synopsis/description
3. **Available Qualities**: List showing each quality option with its size

### Format
- **Quality List Items**: `QUALITY — SIZE` (e.g., "720p — 850MB", "1080p — 1.8GB")
- **Header**: Shows available quality types (e.g., "Available Qualities: 720p, 1080p, 2160p")

### Features Removed
To match your requirements, the following were removed:
- Movie poster
- Year, rating, runtime, language
- Cast information
- Genre tags
- IMDb/Trailer/YTS buttons
- Download and magnet link actions

### Dark Theme
- Background: Dark gray (#1e1e1e, #2b2b2b)
- Text: White and light gray
- Borders: Subtle dark borders (#3a3a3a)

## Files Changed
- `frontend/ui/movie_details.py` - Simplified to show only title, synopsis, and qualities/sizes

## Testing
```powershell
# Terminal 1 - Backend
cd "e:\Softwares\projects\movie project"
python backend/app.py

# Terminal 2 - Test Dialog
cd "e:\Softwares\projects\movie project"
python test_movie_details.py
```

Or run the full app and click any movie card:
```powershell
# Terminal 1 - Backend
python backend/app.py

# Terminal 2 - Frontend
python frontend/main.py
```

## Screenshot Match
The dialog now matches your screenshot:
- Bold "Symbol Synopsis" header
- Full description text
- Clean list of quality options with sizes
- Dark theme throughout
