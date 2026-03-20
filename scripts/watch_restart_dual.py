"""
Watch frontend and backend folders and restart only the process whose files changed.

Usage:
  pip install watchfiles
  python scripts/watch_restart_dual.py --frontend ".\\venv\\Scripts\\python.exe frontend\\main.py" --backend ".\\venv\\Scripts\\python.exe backend\\app.py"

This watcher keeps two subprocesses (frontend and backend). When a change is detected
under `frontend/` the frontend process is restarted, and when a change is detected
under `backend/` the backend process is restarted. Other changes are ignored unless
they are outside the default ignore list.
"""
import argparse
import os
import subprocess
import time
import sys
import signal
from watchfiles import watch
from pathlib import Path
import fnmatch


DEFAULT_IGNORES = {
    '.git', 'venv', 'env', '__pycache__', 'build', 'dist', 'data', 'downloads',
    'logs', '*.pyc', '*.log', 'movie_app_diagnose.log'
}


def _is_ignored(path: str, ignores=DEFAULT_IGNORES) -> bool:
    pp = Path(path)
    parts = set(pp.parts)
    for ig in ignores:
        if ig in parts:
            return True
        if fnmatch.fnmatch(path, ig) or fnmatch.fnmatch(pp.name, ig):
            return True
    return False


class ProcessGuard:
    def __init__(self, name: str, cmd: str):
        self.name = name
        self.cmd = cmd
        self.proc = None

    def start(self):
        print(f"Starting {self.name}: {self.cmd}")
        try:
            self.proc = subprocess.Popen(self.cmd, shell=True)
        except Exception as e:
            print(f"Failed to start {self.name}: {e}")
            self.proc = None

    def stop(self, timeout=5):
        if not self.proc:
            return
        try:
            if self.proc.poll() is None:
                print(f"Terminating {self.name} (pid={self.proc.pid})")
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=timeout)
                except Exception:
                    print(f"Killing {self.name}")
                    self.proc.kill()
        except Exception as e:
            print(f"Error stopping {self.name}: {e}")
        finally:
            self.proc = None

    def restart(self):
        print(f"Restarting {self.name}")
        self.stop()
        time.sleep(0.2)
        self.start()


def run_dual_watcher(frontend_cmd: str, backend_cmd: str, path: str = '.'):
    frontend = ProcessGuard('frontend', frontend_cmd) if frontend_cmd else None
    backend = ProcessGuard('backend', backend_cmd) if backend_cmd else None

    try:
        if frontend:
            frontend.start()
        if backend:
            backend.start()

        for changes in watch(path):
            raw_paths = [c[1] for c in changes]
            interesting = [p for p in raw_paths if not _is_ignored(p)]
            if not interesting:
                continue
            print('Detected changes:', interesting)

            # Determine whether any frontend/backend files were touched
            restart_frontend = any(str(Path(p)).startswith('frontend' + os.sep) for p in interesting)
            restart_backend = any(str(Path(p)).startswith('backend' + os.sep) for p in interesting)

            # If a top-level file changed (e.g., packaging or manifest) don't auto-restart
            # unless it lives under frontend/ or backend/.

            if restart_frontend and frontend:
                frontend.restart()

            if restart_backend and backend:
                backend.restart()

    except KeyboardInterrupt:
        print('Watcher interrupted')
    finally:
        try:
            if frontend:
                frontend.stop()
            if backend:
                backend.stop()
        except Exception:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frontend', default='')
    parser.add_argument('--backend', default='')
    parser.add_argument('--path', default='.')
    args = parser.parse_args()
    if not args.frontend and not args.backend:
        print('Specify at least one of --frontend or --backend')
        sys.exit(1)
    run_dual_watcher(args.frontend, args.backend, path=args.path)
