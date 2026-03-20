# aria2 Download Manager Setup

This document explains how to install and configure aria2 for the YTS Movie Monitor download functionality.

## Quick Setup (Windows)

### Option 1: Automated Setup (Recommended)

Run the PowerShell setup script:

```powershell
.\setup_aria2.ps1
```

This will:
- Download the latest aria2 for Windows
- Extract `aria2c.exe` to the `./bin/` directory
- Verify the installation
- Show next steps

### Option 2: Manual Installation

1. **Download aria2:**
   - Visit: https://github.com/aria2/aria2/releases
   - Download: `aria2-{version}-win-64bit-build1.zip`

2. **Extract:**
   - Extract the downloaded ZIP file
   - Find `aria2c.exe` inside

3. **Install:**
   - Copy `aria2c.exe` to: `E:\Softwares\projects\movie project\bin\aria2c.exe`
   - Create the `bin` folder if it doesn't exist

4. **Verify:**
   ```powershell
   .\bin\aria2c.exe --version
   ```

## Configuration

### Environment Variables (Optional)

- **ARIA2_RPC_SECRET**: Set a secret token for RPC authentication
  ```powershell
  $env:ARIA2_RPC_SECRET = "your-secret-token-here"
  ```

- **DOWNLOAD_POLL_INTERVAL_SECONDS**: How often to check download status (default: 5 seconds)
  ```powershell
  $env:DOWNLOAD_POLL_INTERVAL_SECONDS = "3"
  ```

- **DOWNLOAD_PATH**: Where to save downloaded files (default: `./downloads`)
  ```powershell
  $env:DOWNLOAD_PATH = "D:\Movies"
  ```

## How It Works

1. **Backend Startup:**
   - The backend checks if `aria2c.exe` exists in `./bin/` or system PATH
   - If found, it starts aria2 with RPC enabled on port 6800
   - A background polling thread queries aria2 every 5 seconds

2. **Starting Downloads:**
   - Frontend calls `/api/download/start` with magnet link
   - Backend adds the magnet to aria2 via RPC
   - aria2 returns a GID (download ID)
   - Download is saved to database

3. **Progress Tracking:**
   - Backend poller queries aria2 for active/waiting/stopped downloads
   - Updates database with: progress, speed, peers, seeds, state
   - Frontend refreshes from database (manual or auto-refresh)

4. **Download States:**
   - `queued` - Waiting to start
   - `downloading` - Active download
   - `paused` - User paused
   - `completed` - Finished successfully
   - `error` - Failed or cancelled

## Testing Downloads

1. **Start the backend** (if not running):
   ```powershell
   python -m backend.app
   ```
   
   Look for these log messages:
   ```
   INFO - aria2 RPC is reachable
   INFO - Starting aria2 poll loop (interval=5s)
   INFO - aria2 manager initialized
   ```

2. **Start the frontend** (if not running):
   ```powershell
   python -m frontend.main
   ```

3. **Test a download:**
   - Browse movies in the main tab
   - Click on a movie card to open details
   - Click a Download button (e.g., "720p", "1080p")
   - Switch to the "Downloads" tab

4. **Monitor progress:**
   - Click "Auto Refresh: Off" to enable live updates
   - Watch progress bars update every 2 seconds
   - Use Pause/Resume/Cancel buttons to control downloads

## Troubleshooting

### aria2 RPC connection errors

**Symptoms:**
```
ERROR - aria2 RPC call failed: aria2.tellActive
[WinError 10061] No connection could be made...
```

**Solutions:**
- Verify `aria2c.exe` exists in `./bin/`
- Restart the backend server
- Check if port 6800 is available (not blocked by firewall)
- Run manually to test: `.\bin\aria2c.exe --enable-rpc`

### Downloads not starting

**Check:**
1. Backend logs show "aria2 manager initialized"
2. No RPC connection errors in logs
3. Magnet link is valid (starts with `magnet:?`)
4. Download path exists and is writable

### Progress not updating

**Solutions:**
- Enable "Auto Refresh" in Downloads tab
- Check backend logs for polling errors
- Verify aria2 is still running (not crashed)
- Try manual refresh

## Advanced Configuration

### Custom aria2 Settings

Create a file `aria2.conf` in the project root:

```conf
# Maximum concurrent downloads
max-concurrent-downloads=5

# Download speed limit (0 = unlimited)
max-download-limit=0

# Upload speed limit
max-upload-limit=50K

# Continue downloads
continue=true

# Minimum split size
min-split-size=10M

# Number of connections per server
max-connection-per-server=16

# Enable RPC
enable-rpc=true
rpc-listen-port=6800
rpc-allow-origin-all=true
```

Then modify `backend/downloader.py` to use the config file.

### Running aria2 as a Service

To keep aria2 running independently:

```powershell
# Start aria2 manually
.\bin\aria2c.exe --enable-rpc --rpc-listen-port=6800 --dir=".\downloads"
```

Then the backend will connect to the existing aria2 instance instead of starting its own.

## Security Notes

- **RPC Secret**: Set `ARIA2_RPC_SECRET` if exposing aria2 RPC to network
- **Firewall**: Only allow localhost connections (default: `--rpc-listen-all=false`)
- **Download Path**: Ensure write permissions are restricted appropriately
- **Magnet Links**: Be cautious with untrusted sources

## Support

If you encounter issues:
1. Check backend logs for detailed error messages
2. Verify aria2 version: `.\bin\aria2c.exe --version`
3. Test aria2 manually with a simple download
4. Review aria2 documentation: https://aria2.github.io/
