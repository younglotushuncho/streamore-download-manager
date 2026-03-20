"""
Lightweight watcher to auto-restart a process when files change.
Usage:
  pip install watchfiles
  python scripts/watch_restart.py --cmd ".\\venv\\Scripts\\python.exe backend\\app.py"

This is intentionally simple and cross-platform. It restarts the command whenever
any file under the watched `--path` changes.
"""
import argparse
import shlex
import subprocess
import time
import sys
from watchfiles import watch
import fnmatch
from pathlib import Path


def run_and_watch(cmd: str, path: str = '.', restart_delay: float = 0.2):
    """Run `cmd` and restart it whenever files under `path` change."""
    proc = None
    # Default ignores to avoid restarting on runtime files
    default_ignores = {
        '.git', 'venv', 'env', '__pycache__', 'build', 'dist', 'data', 'downloads',
        'logs', '*.pyc', '*.log', 'movie_app_diagnose.log'
    }

    def _is_ignored(p: str, ignore_patterns) -> bool:
        # Normalize and check path parts and glob patterns
        pp = Path(p)
        parts = set(pp.parts)
        for ig in ignore_patterns:
            if ig in parts:
                return True
            # glob match against the relative path
            if fnmatch.fnmatch(p, ig) or fnmatch.fnmatch(pp.name, ig):
                return True
        return False

    try:
        print(f"Starting process: {cmd}")
        proc = subprocess.Popen(cmd, shell=True)

        for changes in watch(path):
            # `changes` is an iterable of (Change, path) tuples
            raw_paths = [c[1] for c in changes]
            # Filter out ignored changes; if nothing left, skip restart
            interesting = [p for p in raw_paths if not _is_ignored(p, default_ignores)]
            if not interesting:
                # Only ignored files changed (logs, pyc, etc.) — do not restart
                # print for debug when needed
                # print(f"Ignored changes: {raw_paths}")
                continue

            print("Changes detected (interesting):", interesting)
            try:
                if proc and proc.poll() is None:
                    print("Terminating process...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        proc.kill()
                time.sleep(restart_delay)
                print("Restarting process...")
                proc = subprocess.Popen(cmd, shell=True)
            except KeyboardInterrupt:
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if proc and proc.poll() is None:
                proc.terminate()
        except Exception:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cmd', required=True, help='Command to run (as a single string)')
    parser.add_argument('--path', default='.', help='Path to watch (defaults to repo root).')
    parser.add_argument('--delay', type=float, default=0.2, help='Delay before restarting (seconds).')
    args = parser.parse_args()
    run_and_watch(args.cmd, path=args.path, restart_delay=args.delay)
