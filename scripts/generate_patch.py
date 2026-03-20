"""
Generate a delta patch ZIP for a release.

Compares the current code against the previous version tag in git and creates
a small ZIP containing ONLY the changed .py / asset files.

Usage:
    python scripts/generate_patch.py --version 1.0.12 --prev-version 1.0.11

What it produces:
    packaging/dist/patch_v1.0.12.zip   (only changed source files)
    manifest.signed.json               (updated with patch_url / patch_sha256 / patch_files)

How it fits in the release workflow:
    1.  Build the full installer as normal (PyInstaller + Inno Setup).
    2.  Run this script to generate the patch ZIP.
    3.  Upload both the installer AND the patch ZIP to the GitHub release.
    4.  Clients that already have the app download <1 MB instead of 90 MB.
"""

import argparse
import hashlib
import hmac as _hmac
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

# Force UTF-8 stdout so Unicode characters (→ arrows etc.) never crash on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
PATCH_OUT_DIR = REPO_ROOT / "packaging" / "dist"
MANIFEST_PATH = REPO_ROOT / "manifest.signed.json"

# Directories whose .py files can be patched (relative to REPO_ROOT)
PATCHABLE_DIRS = ("backend", "frontend", "shared", "updater", "scripts")

# HMAC key for manifest signing (same key used by scripts/sign_manifest.py)
_DEFAULT_HMAC_KEY = os.environ.get(
    "MANIFEST_HMAC_KEY",
    "7c068aac6ba16bf68d135f4607cb98036bcd85e4bccd32a7a259a0fbee679ad2",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sign_manifest(manifest: dict, key: bytes) -> str:
    payload = json.dumps(
        {k: v for k, v in manifest.items() if k != "signature"},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return _hmac.new(key, payload, "sha256").hexdigest()


def get_changed_files(prev_tag: str) -> list[str]:
    """Return list of repo-relative paths that changed since prev_tag."""
    result = subprocess.run(
        ["git", "diff", "--name-only", prev_tag, "HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"[warn] git diff failed: {result.stderr.strip()}")
        print("[warn] Falling back to listing all patchable .py files")
        # Fallback: include all .py files in patchable dirs
        all_py = []
        for d in PATCHABLE_DIRS:
            dir_path = REPO_ROOT / d
            for f in dir_path.rglob("*.py"):
                if "__pycache__" not in str(f):
                    all_py.append(str(f.relative_to(REPO_ROOT)).replace("\\", "/"))
        return all_py

    all_changed = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    # Keep only .py files in patchable directories (skip __pycache__, tests, etc.)
    filtered = []
    for path in all_changed:
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized:
            continue
        if not normalized.endswith(".py"):
            continue
        if any(normalized.startswith(d + "/") for d in PATCHABLE_DIRS):
            if (REPO_ROOT / normalized).exists():
                filtered.append(normalized)

    return filtered


def create_patch_zip(changed_files: list[str], version: str) -> Path:
    PATCH_OUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = PATCH_OUT_DIR / f"patch_v{version}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel_path in changed_files:
            abs_path = REPO_ROOT / rel_path
            if abs_path.exists():
                zf.write(abs_path, rel_path)
                print(f"  + {rel_path}")
            else:
                print(f"  [skip missing] {rel_path}")
        
        # No extra files needed - core libraries are handled by the main EXE bundle.
        pass

    return zip_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate manifest and optional delta patch ZIP")
    parser.add_argument("--version", required=True, help="New version string (e.g. 1.0.12)")
    parser.add_argument("--prev-version", help="Previous version tag (e.g. 1.0.11). If omitted, patch generation is skipped.")
    parser.add_argument("--setup-exe", help="Path to the setup installer exe")
    parser.add_argument("--portable-zip", help="Path to the portable zip")
    args = parser.parse_args()

    version = args.version
    repo_owner = "younglotushuncho"
    repo_name = "moviedownloader"
    tag = f"v{version}"

    print(f"\n=== Manifest Generation for {tag} ===\n")

    # 1. Start with basic manifest
    manifest = {
        "version": version,
        "assets": []
    }

    # 2. Handle assets (Setup and Portable)
    for path_str in [args.portable_zip, args.setup_exe]:
        if not path_str:
            continue
        path = Path(path_str)
        if not path.exists():
            print(f"[warn] Asset not found: {path}")
            continue
        
        name = str(path.name)
        sha_val = str(sha256_file(path))
        url = f"https://github.com/{repo_owner}/{repo_name}/releases/download/{tag}/{name}"
        manifest["assets"].append({
            "name": name,
            "url": url,
            "sha256": sha_val
        })
        print(f"  Asset: {name} ({sha_val})")

    # 3. Optional Patch generation
    patch_files = []
    if args.prev_version:
        prev_tag = f"v{args.prev_version}"
        print(f"\nComparing against {prev_tag} for delta patch...")
        
        changed = get_changed_files(prev_tag)
        if not changed:
            print("[!] No .py files changed — skipping patch ZIP.")
        else:
            print(f"  Found {len(changed)} changed files. Creating ZIP...")
            zip_path = create_patch_zip(changed, version)
            size_kb = zip_path.stat().st_size / 1024
            
            patch_url = f"https://github.com/{repo_owner}/{repo_name}/releases/download/{tag}/{zip_path.name}"
            manifest["patch_url"] = patch_url
            manifest["patch_sha256"] = sha256_file(zip_path)
            manifest["patch_files"] = changed
            print(f"  Patch ZIP: {zip_path.name} ({size_kb:.1f} KB)")
    else:
        print("\n[info] No --prev-version provided; skipping delta patch generation.")

    # 4. Hash Sync Manifest (ALL files)
    print("\nGenerating Full Source Manifest (Hash Sync)...")
    all_files = {}
    source_files_to_zip = []
    for d in PATCHABLE_DIRS:
        dir_path = REPO_ROOT / d
        if not dir_path.exists():
            continue
        for f in dir_path.rglob("*.py"):
            if "__pycache__" in str(f):
                continue
            rel = str(f.relative_to(REPO_ROOT)).replace("\\", "/")
            all_files[rel] = sha256_file(f)
            source_files_to_zip.append(rel)
    
    manifest["files"] = all_files
    
    # Create a full source ZIP for this version
    source_zip_path = PATCH_OUT_DIR / f"source_v{version}.zip"
    with zipfile.ZipFile(source_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in source_files_to_zip:
            zf.write(REPO_ROOT / rel, rel)
    
    source_url = f"https://github.com/{repo_owner}/{repo_name}/releases/download/{tag}/{source_zip_path.name}"
    manifest["source_url"] = source_url
    manifest["source_sha256"] = sha256_file(source_zip_path)
    print(f"  Source ZIP: {source_zip_path.name} ({source_zip_path.stat().st_size/1024:.1f} KB)")

    # 5. Sign and Save
    key = _DEFAULT_HMAC_KEY.encode() if isinstance(_DEFAULT_HMAC_KEY, str) else _DEFAULT_HMAC_KEY
    manifest["signature"] = sign_manifest(manifest, key)
    
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n✓ Saved signed manifest to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
