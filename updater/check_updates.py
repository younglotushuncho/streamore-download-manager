import os
import json
import hmac
import hashlib
import tempfile
import zipfile
import sys
import logging
from pathlib import Path
from typing import Optional

# --- PERMANENT SSL FIX ---
# Import shared.sanitize to clean stale environment variables (e.g. from old .exe runs)
# This MUST happen before `requests` is used.
try:
    import shared.sanitize
except ImportError:
    # Fallback if running in isolation - apply sanitation inline
    for _env_var in ['SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE']:
        _path = os.environ.get(_env_var)
        if _path and '_MEI' in _path and not os.path.exists(_path):
            os.environ.pop(_env_var, None)
    try:
        import certifi
        _ca = certifi.where()
        if _ca and os.path.isfile(_ca):
            os.environ.setdefault('SSL_CERT_FILE', _ca)
            os.environ.setdefault('REQUESTS_CA_BUNDLE', _ca)
    except Exception:
        pass
# --------------------------

import requests


class UpdateChecker:
    """Simple update checker that expects a JSON manifest signed with HMAC-SHA256.

    Manifest format (example):
    {
        "version": "1.2.3",
        "assets": [
            {"name": "MovieApp-1.2.3.zip", "url": "https://...", "sha256": "..."}
        ],
        "files": {"backend/app.py": "<sha256>", ...},
        "source_url": "https://.../source_v1.2.3.zip",
        "source_sha256": "<sha256>",
        "signature": "<hex-hmac>"
    }
    """

    def __init__(self, manifest_url: str, hmac_key: Optional[bytes] = None, assets: Optional[list] = None):
        self.manifest_url = manifest_url
        # Priority: explicit hmac_key param > env var > release asset > default
        env_key = os.environ.get('MANIFEST_HMAC_KEY')
        if hmac_key:
            self.hmac_key = hmac_key if isinstance(hmac_key, (bytes, bytearray)) else str(hmac_key).encode()
        elif env_key:
            self.hmac_key = env_key.encode()
        else:
            self.hmac_key = None
            if assets:
                candidates = ['manifest.hmac', 'manifest.hmac.txt', 'manifest.key', 'manifest_hmac.txt', 'manifest_hmac']
                for asset in assets:
                    name = asset.get('name', '').lower()
                    if name in candidates:
                        try:
                            url = asset.get('browser_download_url')
                            if url:
                                r = requests.get(url, timeout=10, verify=self._ca_bundle())
                                r.raise_for_status()
                                txt = r.text.strip()
                                if txt:
                                    self.hmac_key = txt.encode()
                                    break
                        except Exception:
                            continue
            if not self.hmac_key:
                # Default HMAC key matching the release scripts
                self.hmac_key = b'7c068aac6ba16bf68d135f4607cb98036bcd85e4bccd32a7a259a0fbee679ad2'

    @staticmethod
    def _ca_bundle():
        """Return best available CA bundle path, or True (system default)."""
        ca = os.environ.get('SSL_CERT_FILE') or os.environ.get('REQUESTS_CA_BUNDLE')
        if ca and os.path.isfile(ca):
            return ca
        try:
            import certifi
            return certifi.where()
        except Exception:
            return True

    def fetch_manifest(self) -> dict:
        r = requests.get(self.manifest_url, timeout=10, verify=self._ca_bundle())
        r.raise_for_status()
        return r.json()

    def verify_manifest(self, manifest: dict) -> bool:
        sig = manifest.get('signature')
        if not sig:
            return False
        payload = json.dumps(
            {k: v for k, v in manifest.items() if k != 'signature'},
            separators=(',', ':'), sort_keys=True
        ).encode()
        if not self.hmac_key:
            raise RuntimeError('HMAC key not configured for manifest verification')
        expected = hmac.new(self.hmac_key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def download_asset(self, url: str, dest: Path, progress_callback=None) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=60, verify=self._ca_bundle()) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(downloaded, total)
        return dest

    @staticmethod
    def sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def check_file_integrity(self, app_root: Path, manifest_files: dict) -> list:
        """Compare local files against manifest hashes. Returns list of mismatched/missing files."""
        mismatched = []
        for rel_path, expected_sha in manifest_files.items():
            abs_path = app_root / rel_path
            if not abs_path.exists():
                mismatched.append(rel_path)
                continue
            if self.sha256_file(abs_path) != expected_sha:
                mismatched.append(rel_path)
        return mismatched

    def check_and_download(self, current_version: str, download_dir: str = None,
                           manifest: dict = None, progress_callback=None) -> Optional[dict]:
        log = logging.getLogger(__name__)

        if manifest is None:
            manifest = self.fetch_manifest()

        if not self.verify_manifest(manifest):
            log.warning('Manifest signature verification failed — skipping update')
            return None

        manifest_files = manifest.get('files')
        source_url = manifest.get('source_url')
        latest = manifest.get('version')

        # NOTE: Delta/Hash-Sync update paths have been disabled to simplify
        # update behavior and ensure clients always download the full
        # installer asset. This avoids partial-patch edge cases where a
        # manifest could point to small patch ZIPs or source archives that
        # leave the installed application in an inconsistent state.
        # (If needed, this behaviour can be re-enabled behind a feature flag.)

        # Fallback: standard version check
        if not latest or latest == current_version:
            return None

        if not manifest.get('assets'):
            return None

        asset = manifest['assets'][0]
        url = asset['url']
        expected_sha = asset.get('sha256')
        name = asset.get('name') or os.path.basename(url)
        dest_dir = Path(download_dir) if download_dir else Path(tempfile.gettempdir())
        dest = dest_dir / name
        self.download_asset(url, dest, progress_callback=progress_callback)

        got_sha = self.sha256_file(dest)
        if expected_sha and got_sha != expected_sha:
            dest.unlink(missing_ok=True)
            raise RuntimeError('Downloaded asset SHA256 mismatch')

        exe_path = dest
        if name.lower().endswith('.zip'):
            extract_dir = dest_dir / f"StreamoreMonitor-{latest}"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(dest, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            exe_files = list(extract_dir.glob('*.exe'))
            if exe_files:
                exe_path = exe_files[0]

        return {'version': latest, 'path': str(dest), 'exe_path': str(exe_path)}


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True)
    p.add_argument('--current', default='0.0.0')
    args = p.parse_args()
    checker = UpdateChecker(args.manifest)
    try:
        out = checker.check_and_download(args.current)
        print('Result:', out)
    except Exception as e:
        print('Error:', e)
