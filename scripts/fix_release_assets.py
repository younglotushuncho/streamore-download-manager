"""
Fix v1.0.9 GitHub release:
  1. Update manifest.signed.json on the published release (ID=288706983)
  2. Upload MovieApp-1.0.9.exe from local disk 
  3. Delete the draft duplicate release (ID=288706061)
"""
import subprocess, requests, sys
from pathlib import Path

token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
if not token:
    print('ERROR: no gh token'); sys.exit(1)

headers       = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
REPO          = 'younglotushuncho/moviedownloader'
PUBLISH_ID    = 288706983   # real published v1.0.9 release
DRAFT_ID      = 288706061   # duplicate draft to delete
MANIFEST_PATH = Path(r'F:\Softwares\projects\movie project\manifest.signed.json')
EXE_PATH      = Path(r'F:\Softwares\projects\movie project\packaging\dist\MovieApp.exe')

def log(msg): print(msg.encode('ascii', 'replace').decode('ascii'), flush=True)

# ── Step 1: Replace manifest on published release ────────────────────────────
log('\n[1] Updating manifest.signed.json on published release...')
r = requests.get(f'https://api.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets',
                 headers=headers, timeout=10)
for asset in r.json():
    if asset['name'] == 'manifest.signed.json':
        log(f'    Deleting old manifest (id={asset["id"]})...')
        requests.delete(f'https://api.github.com/repos/{REPO}/releases/assets/{asset["id"]}',
                        headers=headers)

upload_url = f'https://uploads.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets?name=manifest.signed.json'
uheaders   = {**headers, 'Content-Type': 'application/json'}
with open(MANIFEST_PATH, 'rb') as f:
    resp = requests.post(upload_url, headers=uheaders, data=f, timeout=30)
if resp.status_code in (200, 201):
    log(f'    manifest.signed.json uploaded OK -> {resp.json()["browser_download_url"]}')
else:
    log(f'    ERROR uploading manifest: {resp.status_code} {resp.text[:200]}')

# ── Step 2: Upload EXE to published release ──────────────────────────────────
log(f'\n[2] Uploading {EXE_PATH.name} ({EXE_PATH.stat().st_size/1024/1024:.1f} MB) to published release...')

# Remove any existing EXE asset first
r2 = requests.get(f'https://api.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets',
                  headers=headers, timeout=10)
for asset in r2.json():
    if asset['name'] == 'MovieApp-1.0.9.exe':
        log(f'    Deleting existing EXE asset (id={asset["id"]})...')
        requests.delete(f'https://api.github.com/repos/{REPO}/releases/assets/{asset["id"]}',
                        headers=headers)

exe_url     = f'https://uploads.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets?name=MovieApp-1.0.9.exe'
exe_headers = {**headers, 'Content-Type': 'application/octet-stream'}
with open(EXE_PATH, 'rb') as f:
    resp2 = requests.post(exe_url, headers=exe_headers, data=f, timeout=600)
if resp2.status_code in (200, 201):
    log(f'    EXE uploaded OK -> {resp2.json()["browser_download_url"]}')
else:
    log(f'    ERROR uploading EXE: {resp2.status_code} {resp2.text[:200]}')

# ── Step 3: Delete draft duplicate ───────────────────────────────────────────
log(f'\n[3] Deleting draft duplicate release (id={DRAFT_ID})...')
rd = requests.delete(f'https://api.github.com/repos/{REPO}/releases/{DRAFT_ID}',
                     headers=headers, timeout=10)
log(f'    Delete draft: {rd.status_code}')

# ── Step 4: Final asset list ─────────────────────────────────────────────────
r3 = requests.get(f'https://api.github.com/repos/{REPO}/releases/{PUBLISH_ID}/assets',
                  headers=headers, timeout=10)
log(f'\n[4] Final assets on v1.0.9 published release:')
for a in r3.json():
    log(f'    {a["name"]} ({a["size"]/1024/1024:.1f} MB) -> {a["browser_download_url"]}')

log('\nDone.')
with open(r'C:\Temp\fix_release_result.txt', 'w') as out:
    out.write('DONE\n')
