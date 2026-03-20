"""Upload StreamoreMonitor-1.0.9-Setup.exe and updated manifest to v1.0.9 release."""
import subprocess, requests, sys
from pathlib import Path

token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
REPO       = 'younglotushuncho/moviedownloader'
PUBLISH_ID = 288706983
SETUP_PATH = Path(r'F:\Softwares\projects\movie project\dist\StreamoreMonitor-1.0.9-Setup.exe')
MANIFEST   = Path(r'F:\Softwares\projects\movie project\manifest.signed.json')

def log(msg): print(msg, flush=True)

# ── 1. Delete + re-upload manifest ───────────────────────────────────────────
log('[1] Replacing manifest.signed.json...')
r = requests.get(f'https://api.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets', headers=headers, timeout=10)
for a in r.json():
    if a['name'] == 'manifest.signed.json':
        requests.delete(f'https://api.github.com/repos/{REPO}/releases/assets/{a["id"]}', headers=headers)
        log(f'    Deleted old manifest')

url = f'https://uploads.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets?name=manifest.signed.json'
uheaders = {**headers, 'Content-Type': 'application/json'}
with open(MANIFEST, 'rb') as f:
    resp = requests.post(url, headers=uheaders, data=f, timeout=30)
log(f'    manifest upload: {resp.status_code}')

# ── 2. Delete existing setup asset if any, then upload ───────────────────────
log(f'[2] Uploading {SETUP_PATH.name} ({SETUP_PATH.stat().st_size/1024/1024:.1f} MB)...')
r2 = requests.get(f'https://api.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets', headers=headers, timeout=10)
for a in r2.json():
    if 'Setup' in a['name'] and a['name'].endswith('.exe'):
        log(f'    Deleting old setup asset: {a["name"]}')
        requests.delete(f'https://api.github.com/repos/{REPO}/releases/assets/{a["id"]}', headers=headers)

setup_url = f'https://uploads.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets?name={SETUP_PATH.name}'
eheaders  = {**headers, 'Content-Type': 'application/octet-stream'}
with open(SETUP_PATH, 'rb') as f:
    resp2 = requests.post(setup_url, headers=eheaders, data=f, timeout=600)
log(f'    setup upload: {resp2.status_code}')
if resp2.status_code in (200, 201):
    log(f'    URL: {resp2.json()["browser_download_url"]}')

# ── 3. List final assets ──────────────────────────────────────────────────────
r3 = requests.get(f'https://api.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets', headers=headers, timeout=10)
log('[3] Final release assets:')
for a in r3.json():
    log(f'    {a["name"]} ({a["size"]/1024/1024:.1f} MB)')

log('Done.')
with open(r'C:\Temp\setup_upload_result.txt', 'w') as f:
    f.write('DONE\n')
