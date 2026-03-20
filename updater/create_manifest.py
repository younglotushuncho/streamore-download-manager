"""Create a signed manifest for GitHub releases.

This script now supports multiple assets so the manifest can list both the
portable ZIP and the Windows installer EXE.
"""
import json
import hmac
import hashlib
import os
from pathlib import Path

# Get HMAC key from environment or use default for development
HMAC_KEY = os.getenv('MANIFEST_HMAC_KEY', 'your-secret-key-change-in-production').encode()


def sha256_file(filepath: Path) -> str:
    """Calculate SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def create_manifest(version: str, assets: list) -> dict:
    """Create a signed manifest dict from a version and list of asset dicts.

    Each asset dict must have keys: name, url, sha256
    """
    manifest = {
        'version': version,
        'assets': assets,
    }
    payload = json.dumps(manifest, separators=(',', ':'), sort_keys=True).encode()
    sig = hmac.new(HMAC_KEY, payload, hashlib.sha256).hexdigest()
    manifest['signature'] = sig
    return manifest


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Create a signed manifest for a release')
    p.add_argument('--version', required=True, help='Release version (e.g., 1.0.6)')
    p.add_argument('--asset', required=True, nargs='+', help='Path(s) to release asset file(s)')
    p.add_argument('--output', default='manifest.signed.json', help='Output manifest file')
    p.add_argument('--export-key', action='store_true', help='Export the HMAC key to a companion file for uploading')
    args = p.parse_args()

    asset_paths = [Path(pth) for pth in args.asset]
    for pth in asset_paths:
        if not pth.exists():
            print(f"Error: Asset file not found: {pth}")
            exit(1)

    assets = []
    for asset_path in asset_paths:
        print(f"Calculating SHA256 of {asset_path}...")
        sha256 = sha256_file(asset_path)
        print(f"SHA256: {sha256}")
        asset_url = f"https://github.com/younglotushuncho/moviedownloader/releases/download/v{args.version}/{asset_path.name}"
        assets.append({
            'name': asset_path.name,
            'url': asset_url,
            'sha256': sha256,
        })

    manifest = create_manifest(args.version, assets)

    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest created: {output_path}")
    print(f"Upload this file to: https://github.com/younglotushuncho/moviedownloader/releases/tag/v{args.version}")

    if args.export_key:
        key_path = Path(f"manifest-{args.version}.hmac.txt")
        with open(key_path, 'wb') as kf:
            kf.write(HMAC_KEY)
        print(f"Exported HMAC key to: {key_path} (upload this as a release asset named 'manifest.hmac' or similar)")
