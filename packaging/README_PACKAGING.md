Packaging steps — backend + aria2 + installer

1. Prepare environment

- Activate virtualenv (already active in your terminal).
- Ensure `bin/aria2c.exe` exists. See `ARIA2_SETUP.md`.

2. Build backend EXE (one-dir)

Run in PowerShell:

```powershell
.\packaging\build_backend.ps1
```

This creates `dist\YTS-Downloader-Backend\` containing `YTS-Downloader-Backend.exe` and the bundled `bin` folder.

3. Create installer (requires Inno Setup installed)

- Open `packaging\installer.iss` in Inno Setup and compile, or run `ISCC packaging\installer.iss`.

Notes
- The installer currently copies the one-dir output into Program Files and creates shortcuts.
- It does not register a Windows service. If you want the backend to run as a service, I can add NSSM or a service installer step.
