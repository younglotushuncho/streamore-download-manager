"""Simple updater installer script.

Usage (developer):
    python updater_installer.py --archive /path/to/MovieApp-vX.Y.Z.zip --target "C:\path\to\app" --restart-cmd "\"C:\path\to\MovieApp.exe\""

The script extracts the archive to a temp folder, copies files over the target,
making a small backup, and optionally executes a restart command.
"""
import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def safe_copy_tree(src: Path, dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            safe_copy_tree(item, target)
        else:
            try:
                shutil.copy2(item, target)
            except Exception:
                # try remove and overwrite
                try:
                    if target.exists():
                        target.unlink()
                    shutil.copy2(item, target)
                except Exception:
                    print(f"Failed to copy {item} -> {target}")


def install(archive_path: Path, target_dir: Path, backup_dir: Path = None):
    if not archive_path.exists():
        raise FileNotFoundError(archive_path)

    tmp = Path(tempfile.mkdtemp(prefix="movieapp_update_"))
    try:
        with zipfile.ZipFile(archive_path, 'r') as z:
            z.extractall(tmp)

        if backup_dir:
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(target_dir, backup_dir)

        # Copy files from tmp to target
        safe_copy_tree(tmp, target_dir)
    finally:
        try:
            shutil.rmtree(tmp)
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', required=True)
    p.add_argument('--target', required=True)
    p.add_argument('--backup', required=False)
    p.add_argument('--restart-cmd', required=False)
    args = p.parse_args()

    archive = Path(args.archive)
    target = Path(args.target)
    backup = Path(args.backup) if args.backup else None

    install(archive, target, backup)

    if args.restart_cmd:
        # Execute restart command as a subprocess; let it run detached
        import subprocess
        try:
            subprocess.Popen(args.restart_cmd, shell=True)
        except Exception as e:
            print('Failed to restart:', e)


if __name__ == '__main__':
    main()
