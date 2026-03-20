# YTS Movie Monitor - Installation & Run Guide

## ⚠️ Current Issue: Python Not Found

The script detected you're using the **Microsoft Store Python stub** instead of a real Python installation.

**The stub at:**
```
C:\Users\LOTUS\AppData\Local\Microsoft\WindowsApps\python.exe
```
**won't run the backend server.**

---

## ✅ Quick Fix (5 minutes)

### Option 1: Install Real Python (RECOMMENDED)

1. **Download Python:**
   - Visit: https://www.python.org/downloads/
   - Click "Download Python 3.12.x" (latest stable)

2. **Install (IMPORTANT!):**
   - Run the installer
   - ✅ **CHECK "Add Python to PATH"** at the bottom
   - Click "Install Now"
   - Wait for completion

3. **Verify:**
   Open a **NEW** PowerShell window:
   ```powershell
   python --version
   ```
   Should show: `Python 3.12.x`

4. **Install Dependencies:**
   ```powershell
   cd "E:\Softwares\projects\movie project"
   pip install -r requirements.txt
   ```

5. **Run the Project:**
   ```powershell
   .\scripts\start_services.ps1
   python -m frontend.main
   ```

---

### Option 2: Disable Windows Store Alias

1. Press `Win + I` → **Apps** → **Advanced app execution aliases**
2. Turn **OFF**:
   - `python.exe`
   - `python3.exe`
3. Follow **Option 1** above to install real Python

---

## 📋 What You'll Get

Once Python is installed correctly, the script will:

✅ Start **aria2c** (download manager)  
✅ Start **Flask backend** (API server on port 5000)  
✅ Poll health endpoint and verify connectivity  
✅ Show green success messages when ready  
✅ Let you launch the **PyQt6 GUI frontend**

---

## 🎨 New Features Implemented

✅ **Year filter includes 2025 & 2026** (starts at 2026)  
✅ **Modern Dark/Light theme toggle** (custom ToggleSwitch widget)  
✅ **aria2 as default downloader** (no qBittorrent popup)  
✅ **Real download flow** (sends .torrent/magnet to backend)  
✅ **Refined UI colors/sizing** (purple accent theme)

---

## 🚀 After Installation

### Start Services
```powershell
.\scripts\start_services.ps1
```

**Expected output:**
```
Starting YTS Movie Monitor...
Cleaning up existing processes...
Starting aria2c daemon...
  aria2c started (PID: XXXX)
Starting Flask backend...
  Using python executable: C:\Users\...\Python312\python.exe
  Backend started (PID: XXXX)
Testing connectivity...
  Backend is healthy ✅
  aria2 version X.XX.X is running ✅
```

### Launch Frontend GUI
```powershell
python -m frontend.main
```

The PyQt6 window will open with:
- Search bar & filters (Genre, Year, Quality)
- Movie grid with hover effects
- Theme toggle switch (top-right)
- Downloads tab with progress tracking

---

## 📂 Project Structure

```
movie project/
├── backend/           # Flask API + aria2 integration
├── frontend/          # PyQt6 GUI application
├── scripts/
│   └── start_services.ps1  # Startup script (improved)
├── bin/
│   └── aria2c.exe     # Download manager binary
└── requirements.txt   # Python dependencies
```

---

## 🛠️ Troubleshooting

### "Backend health check failed"
- Port 5000 already in use:
  ```powershell
  netstat -ano | Select-String ':5000'
  Stop-Process -Id XXXX -Force
  ```

### "Module not found"
```powershell
pip install -r requirements.txt
```

### Stop all services
```powershell
Stop-Process -Name aria2c,python -Force
```

---

## 📍 Downloads Location
Default: `E:\movie_downloads`

To change, edit `scripts\start_services.ps1` line 16:
```powershell
--dir=YOUR_PATH_HERE
```

---

**Need help?** The startup script now shows detailed error messages and resolution steps automatically.
