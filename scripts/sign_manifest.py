"""Simple manifest signing tool using HMAC-SHA256.

Usage:
  Set the environment variable MANIFEST_HMAC_KEY to a secret (hex or raw).
  Then run: `python scripts/sign_manifest.py manifest.json > manifest.signed.json`

This writes a copy of the manifest with a `signature` field containing the
HMAC-SHA256 hex digest computed over the canonical JSON payload.

For production use, replace this with an asymmetric signing step (RSA/ECDSA)
and keep the private key offline.
"""

import os
import sys
import json
import hmac
import hashlib


def sign_manifest(manifest_path: str, key: bytes) -> dict:
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    payload = json.dumps({k: v for k, v in manifest.items() if k != 'signature'}, separators=(',', ':'), sort_keys=True).encode()
    sig = hmac.new(key, payload, hashlib.sha256).hexdigest()
    manifest['signature'] = sig
    return manifest


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/sign_manifest.py manifest.json', file=sys.stderr)
        sys.exit(2)
    key_env = os.environ.get('MANIFEST_HMAC_KEY')
    if not key_env:
        print('MANIFEST_HMAC_KEY environment variable not set', file=sys.stderr)
        sys.exit(2)
    key = key_env.encode()
    signed = sign_manifest(sys.argv[1], key)
    json.dump(signed, sys.stdout, indent=2)
