import os
import json
import hashlib
import hmac
from pathlib import Path

# Directories whose .py files we track
TRACKED_DIRS = ["backend", "frontend", "shared", "updater", "scripts"]
REPO_ROOT = Path(__file__).resolve().parent.parent
HMAC_KEY = os.getenv('MANIFEST_HMAC_KEY', '7c068aac6ba16bf68d135f4607cb98036bcd85e4bccd32a7a259a0fbee679ad2').encode()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def generate_manifest(version: str, repo_info: str):
    print(f"Generating full manifest for v{version}...")
    file_map = {}
    
    for d in TRACKED_DIRS:
        dir_path = REPO_ROOT / d
        if not dir_path.exists():
            continue
            
        for f in dir_path.rglob("*.py"):
            if "__pycache__" in str(f):
                continue
            rel_path = f.relative_to(REPO_ROOT).as_posix()
            file_map[rel_path] = sha256_file(f)
    
    # We also include a link to the full source ZIP for this version
    # Users can download the whole ZIP to recover their "dirty" files
    source_url = f"https://github.com/{repo_info}/releases/download/v{version}/source_v{version}.zip"
    
    manifest = {
        "version": version,
        "mode": "hash_sync",
        "source_url": source_url,
        "files": file_map
    }
    
    # Sign it
    payload = json.dumps(manifest, separators=(',', ':'), sort_keys=True).encode()
    sig = hmac.new(HMAC_KEY, payload, hashlib.sha256).hexdigest()
    manifest["signature"] = sig
    
    return manifest

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--repo", default="younglotushuncho/moviedownloader")
    parser.add_argument("--output", default="manifest.signed.json")
    args = parser.parse_args()
    
    m = generate_manifest(args.version, args.repo)
    with open(REPO_ROOT / args.output, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)
    print(f"Full Hash Sync manifest saved to {args.output}")
