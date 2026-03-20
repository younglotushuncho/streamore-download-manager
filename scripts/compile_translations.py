"""Compile Qt .ts translation files into .qm using `lrelease` if available.

Run from project root:

    python scripts/compile_translations.py

This script tries to find `lrelease` on PATH. If not found, it prints instructions.
"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
TS_DIR = ROOT / 'frontend' / 'resources' / 'translations'

def find_lrelease():
    return shutil.which('lrelease')


def main():
    if not TS_DIR.exists():
        print("Translations folder not found:", TS_DIR)
        return 1

    lrelease = find_lrelease()
    if not lrelease:
        print("lrelease not found on PATH. Install Qt tools or run lrelease manually.")
        return 1

    for ts in TS_DIR.glob('*.ts'):
        print('Compiling', ts.name)
        try:
            # lrelease <ts> will generate <basename>.qm in same folder
            subprocess.run([lrelease, str(ts)], check=True)
        except subprocess.CalledProcessError as e:
            print('lrelease failed for', ts, e)

    print('Done')
    return 0

if __name__ == '__main__':
    sys.exit(main())
