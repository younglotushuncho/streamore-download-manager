# Streamore Monitor

A sleek, premium desktop application for Windows that monitors movie releases and automates your high-quality downloads.

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

- 🚀 **Delta Updates** - Lightning-fast updates. Download only the changes (50KB) instead of the full installer.
- 🎬 **Watchlist & Bookmarks** - Save movies to download later with persistent storage.
- 📉 **Speed History** - Real-time and historical download speed tracking for all active tasks.
- 🛡️ **Engine-wide Recovery** - Automatic recovery from stalled downloads and backend instability.
- 📱 **PWA Support** - Install Streamore on your mobile device or desktop for a native-like experience.
- 🔒 **Privacy-First** - GDPR compliant consent system and granular logging controls.
- 📤 **Social Sharing** - One-click sharing for movies and the app itself.
- 🌟 **Premium Tier** - UI-ready for ad-free experience and priority updates.

## 🚀 Quick Start

### For Users — Recommended: Portable ZIP
> ⚠️ **Windows SmartScreen** may block the installer because the app isn't code-signed yet.
> Use the **Portable ZIP** to avoid this entirely.

1. Go to [Latest Release](https://github.com/younglotushuncho/moviedownloader/releases/latest)
2. Download `StreamoreMonitor-3.0.0-Setup.exe` (Installer) or the Portable ZIP.
3. If using the installer, follow the prompts.
4. Launch **Streamore Monitor** from your desktop.

### For Developers

```bash
# Clone repository
git clone https://github.com/younglotushuncho/moviedownloader.git
cd moviedownloader

# Setup Environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run
python desktop/downloader_app.py
```

## 🏗️ Project Structure

```
moviedownloader/
├── backend/           # Flask API server & Aria2 Manager
├── desktop/           # PyQt6 Modern UI & Bridge
├── web/               # Next.js Web Frontend & PWA
├── shared/            # Common models and constants
├── scripts/           # Deployment and patch generation tools
└── packaging/         # Installer scripts (Inno Setup)
```

## 🛠️ Tech Stack

- **Frontend:** Next.js (Web/PWA), PyQt6 (Desktop)
- **Backend:** Flask, Python 3.11
- **Download Engine:** Aria2c
- **Database:** SQLite
- **Release System:** GitHub Actions + Delta Patching

## Local Release (R2)

Use this when you want to build and publish updates directly from your PC (no GitHub Actions).

Prereqs:
- AWS CLI installed (`aws --version`)
- Env vars set: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_BASE_URL

Command:
```
.\packaging\build_nuitka.ps1
```

Outputs:
- dist\StreamoreSetup.exe
- dist\latest.json

Quality gates (automatic in the command above):
- local smoke check: `packaging/smoke_release.ps1`
- post-publish R2 verification: `packaging/verify_r2_release.ps1`

Manual verify only:
```
.\packaging\verify_r2_release.ps1
```

### Auto Publish On Commit (Local PC)

If you want desktop updates to auto-publish whenever you commit desktop/backend changes:

1. Install the git hook once:
```
.\packaging\install_post_commit_hook.ps1
```
2. Commit your desktop changes normally.
3. Hook starts build+publish in background and writes logs to:
```
$env:TEMP\streamore-auto-release.log
```

Notes:
- Triggered only for commits touching: `desktop/`, `backend/`, `shared/`, `packaging/`, `bin/`
- Add `[skip-release]` in commit message to skip auto publish for a commit.

## 🛡️ Legal
Streamore Monitor is a tool for personal automation. Users are responsible for complying with local copyright laws.

---
**Made with ❤️ by younglotushuncho**
