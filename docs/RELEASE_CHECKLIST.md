# Quick Deployment Checklist

Use this checklist when publishing a new release.

## Pre-Release Setup (One-Time)

- [ ] Generate HMAC key: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Add `MANIFEST_HMAC_KEY` secret in **GitHub Settings → Secrets → Actions**
- [ ] Update `UPDATE_MANIFEST_URL` in `backend/config.py` with your GitHub release URL
- [ ] Copy `.env.example` to `.env` and set `MANIFEST_HMAC_KEY` (same as GitHub secret)
- [ ] Test local build: `pyinstaller --clean packaging/pyinstaller.spec`

## Releasing a New Version

- [ ] Update version in `backend/config.py`: `VERSION = '1.X.Y'`
- [ ] Commit changes: `git add . && git commit -m "Release v1.X.Y"`
- [ ] Push to main: `git push origin main`
- [ ] Create tag: `git tag v1.X.Y`
- [ ] Push tag: `git push origin v1.X.Y`
- [ ] Watch CI build in **GitHub Actions** tab
- [ ] Verify release assets uploaded:
  - `MovieApp-v1.X.Y.zip`
  - `manifest.signed.json`
- [ ] Download and test the release ZIP

## Testing Updates

- [ ] Build an older version locally (set `APP_VERSION=0.9.0`)
- [ ] Run the app: `venv\Scripts\python.exe frontend/main.py`
- [ ] Verify update dialog appears after 2 seconds
- [ ] Confirm new version downloads successfully

## Distribution

Share the download link with users:
```
https://github.com/YOUR_USERNAME/YOUR_REPO/releases/latest
```

Users download and extract the ZIP, then run `MovieApp.exe`.

---

## Common Commands

**Generate HMAC Key:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Build Locally:**
```powershell
pyinstaller --clean packaging/pyinstaller.spec
```

**Sign Manifest Locally:**
```powershell
$env:MANIFEST_HMAC_KEY = "your_key_here"
python scripts/sign_manifest.py manifest.json > manifest.signed.json
```

**Create Release:**
```powershell
git tag v1.0.0
git push origin v1.0.0
```

---

## Troubleshooting

**CI fails with "ModuleNotFoundError":**
- Ensure `requirements.txt` includes all dependencies
- Check Python version in workflow matches your dev environment

**Update check fails:**
- Verify `UPDATE_MANIFEST_URL` is accessible (check browser)
- Confirm `MANIFEST_HMAC_KEY` matches in client and CI
- Check app logs for error details

**Windows Defender blocks executable:**
- Code-sign your executable with a trusted certificate
- Or add virus scan exemption during testing

---

## Next Release Workflow

1. Fix bugs / add features
2. Update `VERSION` in `backend/config.py`
3. Commit + push
4. Create + push tag
5. CI builds and publishes automatically
6. Users get update notification on next app launch
