"""Upload MovieApp.exe to the v1.0.9 GitHub release."""
import subprocess, requests, sys, os
from pathlib import Path

RELEASE_ID = 288706061
REPO = 'younglotushuncho/moviedownloader'
EXE_PATH = Path(r'F:\Softwares\projects\movie project\packaging\dist\MovieApp.exe')
ASSET_NAME = 'MovieApp-1.0.9.exe'

token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
if not token:
    print('ERROR: Could not get gh token')
    sys.exit(1)

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github+json',
    'Content-Type': 'application/octet-stream',
}

# Delete existing asset with same name if present
r = requests.get(f'https://api.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets', headers=headers, timeout=10)
for asset in r.json():
    if asset['name'] == ASSET_NAME:
        print(f'Deleting existing asset {ASSET_NAME} (id={asset["id"]})...')
        requests.delete(f'https://api.github.com/repos/{REPO}/releases/assets/{asset["id"]}', headers=headers)

upload_url = f'https://uploads.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets?name={ASSET_NAME}'
print(f'Uploading {EXE_PATH.name} ({EXE_PATH.stat().st_size / 1024 / 1024:.1f} MB) as {ASSET_NAME}...')

with open(EXE_PATH, 'rb') as f:
    resp = requests.post(upload_url, headers=headers, data=f, timeout=600)

if resp.status_code in (200, 201):
    asset = resp.json()
    print(f'SUCCESS: {asset["name"]} uploaded ({asset["size"] / 1024 / 1024:.1f} MB)')
    print(f'URL: {asset["browser_download_url"]}')
    with open(r'C:\Temp\upload_result.txt', 'w') as out:
        out.write(f'SUCCESS: {asset["browser_download_url"]}\n')
else:
    print(f'FAILED: {resp.status_code} {resp.text[:300]}')
    with open(r'C:\Temp\upload_result.txt', 'w') as out:
        out.write(f'FAILED: {resp.status_code}\n')
    sys.exit(1)
