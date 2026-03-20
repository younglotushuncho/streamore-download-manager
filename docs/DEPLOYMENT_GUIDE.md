# Desktop App Deployment Guide with Auto-Updates

This guide walks you through publishing your desktop app with automatic update functionality.

## Overview

The deployment pipeline:
1. **Tag a release** → triggers GitHub Actions workflow
2. **CI builds** the PyInstaller executable + creates a release ZIP
3. **CI computes SHA256** of the release artifact
4. **CI creates a GitHub release** and uploads the artifact
5. **CI generates and signs a manifest** with version, download URL, and SHA256
6. **CI uploads signed manifest** to the release
7. **Client checks manifest** on startup (every launch) and downloads updates if available

---

## Prerequisites

### 1. Repository Setup

Ensure your repository is on GitHub and you have admin access to configure secrets and create releases.

### 2. Generate HMAC Key

Generate a strong HMAC key for signing manifests:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output (64-character hex string).

### 3. Add GitHub Repository Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value | Purpose |
|------------|-------|---------|
| `MANIFEST_HMAC_KEY` | (hex string from step 2) | Signs the update manifest |

**Important:** Keep this key secret. Anyone with this key can forge update manifests.

---

## Step-by-Step Deployment

### Step 1: Set Version in Config

Edit `backend/config.py` and update the version:

```python
# Application version
VERSION = os.getenv('APP_VERSION', '1.0.0')
```

Or set an environment variable before building:

```powershell
$env:APP_VERSION = "1.0.0"
```

### Step 2: Configure Manifest URL

Set the `UPDATE_MANIFEST_URL` in `backend/config.py` to point to where your signed manifest will be hosted:

```python
# Auto-update manifest URL
UPDATE_MANIFEST_URL = os.getenv('UPDATE_MANIFEST_URL', 
    'https://github.com/YOUR_USERNAME/YOUR_REPO/releases/latest/download/manifest.signed.json')
```

Replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub username and repository name.

Alternatively, set the environment variable:

```powershell
$env:UPDATE_MANIFEST_URL = "https://github.com/YOUR_USERNAME/YOUR_REPO/releases/latest/download/manifest.signed.json"
```

### Step 3: Commit Changes

```powershell
git add .
git commit -m "Prepare for release v1.0.0"
git push origin main
```

### Step 4: Create and Push a Release Tag

```powershell
git tag v1.0.0
git push origin v1.0.0
```

**This triggers the CI workflow automatically.**

### Step 5: Monitor CI Build

1. Go to **Actions** tab in your GitHub repository
2. Watch the "Build And Release (Windows)" workflow run
3. The workflow will:
   - Install Python and dependencies
   - Build the PyInstaller executable
   - Create `release.zip` from `dist/MovieApp/`
   - Compute SHA256 of the ZIP
   - Create a GitHub release (draft=false)
   - Upload `MovieApp-v1.0.0.zip` to the release
   - Generate `manifest.json` with version, URL, and SHA256
   - Sign the manifest using `MANIFEST_HMAC_KEY`
   - Upload `manifest.signed.json` to the release

### Step 6: Verify Release Assets

After CI completes:

1. Go to **Releases** in your repository
2. Find the release `v1.0.0`
3. Verify two assets are present:
   - `MovieApp-v1.0.0.zip` (the installer/app bundle)
   - `manifest.signed.json` (the signed update manifest)

### Step 7: Download and Test the Release

Download `MovieApp-v1.0.0.zip`:

```powershell
# Extract
Expand-Archive MovieApp-v1.0.0.zip -DestinationPath MovieApp-v1.0.0
cd MovieApp-v1.0.0

# Run the app
.\MovieApp.exe
```

The app should:
- Start normally
- After 2 seconds, check for updates in the background
- If no newer version exists, log "No updates available"

---

## How Auto-Update Works

### Client Startup Flow

1. **App launches** → `frontend/main.py` reads `Config.VERSION` (e.g., `"1.0.0"`)
2. **After 2 seconds** → `check_for_updates()` runs in background (non-blocking)
3. **Fetches manifest** from `Config.UPDATE_MANIFEST_URL`
4. **Verifies signature** using `MANIFEST_HMAC_KEY` (stored in env or hardcoded)
5. **Compares versions** → if manifest version > current version:
   - Downloads the new release ZIP
   - Verifies SHA256 checksum
   - Shows a dialog: "Update available! Downloaded to: [path]"
   - User closes the app and runs the new installer

### Manifest Format

```json
{
  "version": "1.0.1",
  "assets": [
    {
      "name": "MovieApp-v1.0.1.zip",
      "url": "https://github.com/USER/REPO/releases/download/v1.0.1/MovieApp-v1.0.1.zip",
      "sha256": "abc123..."
    }
  ],
  "signature": "def456..."
}
```

---

## Testing Update Flow Locally

### 1. Build Local Version

```powershell
# Set older version
$env:APP_VERSION = "0.9.0"

# Build
pyinstaller --clean packaging/pyinstaller.spec
```

### 2. Create Test Manifest

Create `test_manifest.json`:

```json
{
  "version": "1.0.0",
  "assets": [
    {
      "name": "MovieApp-1.0.0.zip",
      "url": "https://github.com/YOUR_USERNAME/YOUR_REPO/releases/download/v1.0.0/MovieApp-v1.0.0.zip",
      "sha256": "ACTUAL_SHA256_HERE"
    }
  ]
}
```

### 3. Sign Test Manifest

```powershell
$env:MANIFEST_HMAC_KEY = "your_64_char_hex_key"
python scripts/sign_manifest.py test_manifest.json > test_manifest.signed.json
```

### 4. Host Manifest Locally

Use a simple HTTP server:

```powershell
python -m http.server 8000
```

### 5. Configure Client to Check Local Manifest

```powershell
$env:UPDATE_MANIFEST_URL = "http://localhost:8000/test_manifest.signed.json"
$env:MANIFEST_HMAC_KEY = "your_64_char_hex_key"
```

### 6. Run the App

```powershell
venv\Scripts\python.exe frontend/main.py
```

The app should:
- Detect version `0.9.0` < `1.0.0`
- Download the release
- Show update dialog

---

## Security Best Practices

### 1. Use Asymmetric Signatures (Production)

HMAC is symmetric (same key signs and verifies). For production:
- Use RSA or ECDSA signatures
- Keep private key offline or in secure CI secrets
- Embed public key in the client app

### 2. HTTPS Only

Always serve manifests and downloads over HTTPS to prevent MITM attacks.

### 3. Code Signing (Windows)

Sign your executables with a trusted certificate:

```powershell
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist/MovieApp/MovieApp.exe
```

This reduces Windows Defender false positives and increases user trust.

### 4. Rotate Keys Regularly

If your HMAC key or signing certificate is compromised, rotate immediately and publish a new client build.

---

## Troubleshooting

### CI Fails: "MANIFEST_HMAC_KEY not set"

- Ensure the secret is added in **Settings → Secrets and variables → Actions**
- Secret names are case-sensitive

### Client Shows "Manifest signature verification failed"

- Ensure `MANIFEST_HMAC_KEY` in client matches the key used to sign the manifest
- Check that the manifest JSON hasn't been modified after signing

### Update Download Fails

- Verify the asset URL in the manifest is publicly accessible
- Check network connectivity and firewall rules

### App Shows "No updates available" when there is a newer version

- Verify `Config.UPDATE_MANIFEST_URL` points to the correct manifest
- Check that the manifest `version` field is greater than `Config.VERSION`
- Review logs: app logs the current version and check result

---

## Advanced: Installer Creation (NSIS/Inno Setup)

For a better user experience, create a Windows installer rather than a ZIP:

### Option A: NSIS

Install NSIS, create `installer.nsi`:

```nsi
!define APP_NAME "MovieApp"
!define APP_VERSION "1.0.0"

OutFile "MovieApp-Setup-${APP_VERSION}.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"

Section
  SetOutPath "$INSTDIR"
  File /r "dist\MovieApp\*.*"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\MovieApp.exe"
SectionEnd
```

Build:

```powershell
makensis installer.nsi
```

### Option B: Inno Setup

Install Inno Setup, create `installer.iss`:

```ini
[Setup]
AppName=MovieApp
AppVersion=1.0.0
DefaultDirName={pf}\MovieApp
DefaultGroupName=MovieApp
OutputBaseFilename=MovieApp-Setup

[Files]
Source: "dist\MovieApp\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{commondesktop}\MovieApp"; Filename: "{app}\MovieApp.exe"
```

Build:

```powershell
iscc installer.iss
```

Update the CI workflow to build the installer and upload `MovieApp-Setup-v1.0.0.exe` instead of the ZIP.

---

## Next Steps

- [ ] Add a "Check for Updates" menu item in the app UI
- [ ] Implement silent background updates (extract and replace files)
- [ ] Add rollback mechanism if update fails
- [ ] Create macOS/Linux builds and cross-platform update logic
- [ ] Set up a CDN for faster downloads

---

## Summary

You now have a complete CI/CD pipeline for desktop app releases with auto-updates:

1. **Tag a release** → CI builds and publishes
2. **Client checks** manifest on startup
3. **User downloads** new version automatically
4. **Signature verification** ensures authenticity

Your users will always have the latest version with minimal friction!
