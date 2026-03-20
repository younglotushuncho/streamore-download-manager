"""Smoke test for the updater system.

Creates a small zip asset and a signed manifest, serves them over HTTP,
runs the update checker to download the asset, then runs the installer to
install into a temporary target directory and verifies the file was copied.
"""
import os
import zipfile
import hashlib
import json
import hmac
import tempfile
import threading
import time
from pathlib import Path

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / 'updater' / 'test_assets'
ASSET_DIR.mkdir(parents=True, exist_ok=True)

ZIP_NAME = 'MovieApp-test.zip'
ZIP_PATH = ASSET_DIR / ZIP_NAME

MANIFEST_PATH = ROOT / 'updater' / 'test_manifest.json'

HMAC_KEY = b'testkey'

# Make sure repo root is on sys.path so package imports succeed when running
import sys
sys.path.insert(0, str(ROOT))


def build_test_zip():
    with zipfile.ZipFile(ZIP_PATH, 'w') as z:
        # create a dummy exe file inside zip
        z.writestr('MovieApp.exe', 'dummy-binary-content')


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(version='1.0.1'):
    asset_url = f'http://127.0.0.1:8001/updater/test_assets/{ZIP_NAME}'
    manifest = {
        'version': version,
        'assets': [
            {'name': ZIP_NAME, 'url': asset_url, 'sha256': sha256_file(ZIP_PATH)}
        ]
    }
    payload = json.dumps(manifest, separators=(',', ':'), sort_keys=True).encode()
    sig = hmac.new(HMAC_KEY, payload, hashlib.sha256).hexdigest()
    manifest['signature'] = sig
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f)


def start_server():
    # Serve from repository root so paths match
    cwd = os.getcwd()
    os.chdir(str(ROOT))
    handler = SimpleHTTPRequestHandler
    httpd = ThreadingHTTPServer(('127.0.0.1', 8001), handler)

    def serve():
        try:
            httpd.serve_forever()
        finally:
            pass

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    # give server a moment
    time.sleep(0.3)
    return httpd, cwd


def run_test():
    build_test_zip()
    # start server
    httpd, cwd = start_server()
    try:
        write_manifest()

        # set env key for UpdateChecker
        os.environ['MANIFEST_HMAC_KEY'] = HMAC_KEY.decode()

        # run frontend check_for_updates
        from frontend.utils.update_client import check_for_updates

        print('Checking for updates...')
        res = check_for_updates(manifest_url=f'http://127.0.0.1:8001/updater/test_manifest.json')
        print('Result:', res)
        if not res:
            raise RuntimeError('No update found when one expected')

        # run installer to a temp target
        from updater.updater_installer import install
        target = Path(tempfile.mkdtemp(prefix='movieapp_target_'))
        print('Installing to', target)
        install(Path(res['path']), target)

        installed = (target / 'MovieApp.exe').exists()
        print('Installed file exists:', installed)
        if not installed:
            raise RuntimeError('Installer did not copy expected file')

        print('Smoke test succeeded')
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass
        os.chdir(cwd)


if __name__ == '__main__':
    run_test()
