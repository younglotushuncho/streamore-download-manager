# Packaging

This folder contains packaging scripts for building Streamore Monitor on Windows.

---

## Option A — Windows Setup Installer (recommended for distribution)

Produces a proper `StreamoreMonitor-X.X.X-Setup.exe` that:
- Installs to `C:\Program Files\MovieApp\`
- Creates a **desktop shortcut**
- Creates a **Start Menu** entry
- Registers an **uninstaller** in Add/Remove Programs

### Requirements

1. [Inno Setup 6](https://jrsoftware.org/isdl.php) — free, install with defaults
2. Python venv at `venv\` or `env\` with `pyinstaller` installed

### One-command build

```powershell
# From the repository root:
.\packaging\build_installer.ps1
```

This will:
1. Build `dist\MovieApp.exe` with PyInstaller
2. Compile `packaging\installer.iss` with Inno Setup
3. Output `dist\StreamoreMonitor-1.0.6-Setup.exe`

**Skip PyInstaller** (if the exe is already built):
```powershell
.\packaging\build_installer.ps1 -SkipPyInstaller
```

### Manual Inno Setup compile

```powershell
# After PyInstaller build:
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
```

---

## Option B — Portable ZIP (for manual installs / updates)

```powershell
# 1. Build the single-file exe
python -m PyInstaller packaging\pyinstaller.spec --noconfirm

# 2. Zip it
Compress-Archive -Path dist\StreamoreMonitor.exe -DestinationPath dist\StreamoreMonitor-1.0.6.zip -Force
```

---

## Adding a Custom App Icon

Place a 256×256 `.ico` file at `packaging\app_icon.ico`, then update `installer.iss`:

```ini
SetupIconFile=..\packaging\app_icon.ico
```

And update `pyinstaller.spec`:

```python
icon='packaging/app_icon.ico',
```

---

## Notes

- The installer GUID `{A3F2B8C1-4D7E-4F9A-B2E5-1C8D3A6F0E72}` must never change between versions — this is how Windows tracks upgrades.
- Code signing with a certificate is recommended to avoid Windows SmartScreen warnings.
- The app stores its database in `{installdir}\data\` — the user needs write permission there, or change the app to use `%APPDATA%` for portability.
