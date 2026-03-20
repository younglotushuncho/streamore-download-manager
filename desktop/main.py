"""
Streamore Download Manager – Desktop App
====================================
Two modes in one executable:

  1. Protocol handler  – called by Windows when browser opens a streamore:// link.
                         Parses the URL, asks first-run consent, queues download
                         via the local Flask backend or the detection server.

  2. Tray app          – started normally (no streamore:// argument).
                         • Starts backend/app.py in a background subprocess
                         • Runs a tiny **detection server** on localhost:57432
                           so the web app can auto-detect that this app is
                           installed and running.
                         • Sits in the system tray; double-click opens the
                           Download Manager in a NATIVE desktop window (pywebview).

Detection server endpoints (localhost:57432):
  GET  /ping           → {"ok": true, "version": "...", "app": "StreamoreManager"}
  POST /download       → accepts JSON {magnet, title, quality, movie_id}
                         and queues it in aria2 via the flask backend

Usage:
  StreamoreManager.exe                      → tray mode (native window)
  StreamoreManager.exe streamore://download?…  → protocol handler mode
"""

import sys
import os
import json
import threading
import subprocess
import time
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
DETECTION_PORT = 57432          # fixed private port the web app pings
DETECTION_HOST = '127.0.0.1'
APP_VERSION    = '2.2.0'        # keep in sync with shared/version.py
APP_NAME       = 'StreamoreManager'

# Origins that are allowed to call the detection server from a browser
ALLOWED_ORIGINS = [
    'https://streamore-five.vercel.app',   # production
    'https://streamore.vercel.app',
    'https://streamore-beta.vercel.app',
    'http://localhost:3000',
    'http://localhost',
    'http://127.0.0.1:3000',
    'null',                     # local file:// pages
]

# ─── Paths ────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

CONFIG_DIR  = Path(os.environ.get('APPDATA', '~')).expanduser() / 'StreamoreManager'
CONFIG_FILE = CONFIG_DIR / 'config.json'
BACKEND_URL = 'http://127.0.0.1:5000'


# ─── Config helpers ───────────────────────────────────────────────────────────
def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding='utf-8')


def _hidden_subprocess_kwargs() -> dict:
    """Return Windows-only subprocess kwargs to hide spawned console windows."""
    if os.name != 'nt':
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        'creationflags': subprocess.CREATE_NO_WINDOW,
        'startupinfo': startupinfo,
    }


# ─── Backend helpers ──────────────────────────────────────────────────────────
def is_backend_running() -> bool:
    try:
        r = requests.get(f'{BACKEND_URL}/api/health', timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def start_backend():
    """Start Streamore-Backend.exe (sibling of this exe) as a subprocess."""
    backend_exe = APP_DIR / 'Streamore-Backend.exe'
    if not backend_exe.exists():
        logger.warning(f'Backend exe not found: {backend_exe}')
        return None

    proc = subprocess.Popen([str(backend_exe)], **_hidden_subprocess_kwargs())
    logger.info(f'Backend process started (pid={proc.pid})')

    for _ in range(20):
        if is_backend_running():
            logger.info('Backend is reachable')
            return proc
        time.sleep(0.5)

    logger.error('Backend did not respond in time')
    return proc


# ─── Native UI helpers ────────────────────────────────────────────────────────
def _tk_root() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    root.lift()
    root.focus_force()
    return root


def show_consent_dialog(title: str = 'Unknown Movie') -> bool:
    root = _tk_root()
    result = messagebox.askyesno(
        'Streamore – Permission',
        f'A website wants to send this download to your Download Manager:\n\n'
        f'   "{title}"\n\n'
        'Allow downloads from this website?\n'
        '(You will not be asked again)',
        icon='question',
        parent=root,
    )
    root.destroy()
    return bool(result)


def show_info(title: str, msg: str):
    root = _tk_root()
    messagebox.showinfo(title, msg, parent=root)
    root.destroy()


def show_error(msg: str):
    root = _tk_root()
    messagebox.showerror('Streamore Download Manager', msg, parent=root)
    root.destroy()


def show_toast(title: str, msg: str):
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=msg,
            app_name='Streamore',
            timeout=5,
        )
    except Exception:
        root = _tk_root()
        messagebox.showinfo(title, msg, parent=root)
        root.destroy()


# ─── Detection / local HTTP server ────────────────────────────────────────────

def _cors_headers(origin: str) -> dict:
    """Return CORS headers allowing only known web-app origins."""
    allowed = origin if origin in ALLOWED_ORIGINS else ''
    return {
        'Access-Control-Allow-Origin': allowed or ALLOWED_ORIGINS[0],
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400',
    }


def _queue_download_via_backend(payload: dict) -> dict:
    """Forward a download request to the flask backend (aria2)."""
    try:
        if not is_backend_running():
            start_backend()
        resp = requests.post(
            f'{BACKEND_URL}/api/download/start',
            json=payload,
            timeout=10,
        )
        return resp.json()
    except Exception as exc:
        return {'success': False, 'error': str(exc)}


class DetectionHandler(BaseHTTPRequestHandler):
    """Tiny HTTP handler for the web-app ↔ desktop-app bridge."""

    def log_message(self, fmt, *args):
        # Suppress accesslog spam; use our logger instead
        logger.debug('DetectionServer: ' + fmt % args)

    def _origin(self) -> str:
        return self.headers.get('Origin', '')

    def _send_json(self, code: int, body: dict):
        origin = self._origin()
        cors   = _cors_headers(origin)
        data   = json.dumps(body).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        """Pre-flight for browsers doing CORS."""
        origin = self._origin()
        cors   = _cors_headers(origin)
        self.send_response(204)
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        if self.path == '/ping':
            self._send_json(200, {
                'ok':      True,
                'version': APP_VERSION,
                'app':     APP_NAME,
                'backend': is_backend_running(),
            })
        else:
            self._send_json(404, {'error': 'not found'})

    def do_POST(self):
        if self.path == '/download':
            length  = int(self.headers.get('Content-Length', 0))
            raw     = self.rfile.read(length)
            try:
                payload = json.loads(raw)
            except Exception:
                self._send_json(400, {'error': 'invalid JSON'})
                return

            # Consent gate
            cfg = load_config()
            if not cfg.get('consent_given'):
                title = payload.get('title', 'Unknown Movie')
                if not show_consent_dialog(title):
                    self._send_json(403, {'error': 'User declined'})
                    return
                cfg['consent_given'] = True
                save_config(cfg)

            result = _queue_download_via_backend({
                'movie_id':    payload.get('movie_id', ''),
                'movie_title': payload.get('title', 'Unknown'),
                'quality':     payload.get('quality', ''),
                'magnet_link': payload.get('magnet', ''),
            })

            if result.get('success') or result.get('download_id'):
                show_toast(
                    '⬇️ Download Queued',
                    f"{payload.get('title', 'Movie')} ({payload.get('quality', '')}) added to downloads.",
                )
                self._send_json(200, {'ok': True, **result})
            else:
                self._send_json(500, {'ok': False, **result})
        else:
            self._send_json(404, {'error': 'not found'})


def run_detection_server():
    """Start the detection HTTP server in a daemon thread."""
    try:
        server = HTTPServer((DETECTION_HOST, DETECTION_PORT), DetectionHandler)
        logger.info(f'Detection server listening on {DETECTION_HOST}:{DETECTION_PORT}')
        server.serve_forever()
    except OSError as exc:
        logger.warning(f'Could not start detection server (port {DETECTION_PORT} in use?): {exc}')


# ─── Protocol handler mode ────────────────────────────────────────────────────
def handle_protocol(uri: str):
    """
    Handle a streamore:// URI (legacy / fallback path).
    Example:
      streamore://download?magnet=<encoded>&title=<encoded>&quality=<str>&movie_id=<str>
    """
    logger.info(f'Protocol handler invoked: {uri[:120]}')
    try:
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)
        magnet   = (params.get('magnet')   or [''])[0]
        title    = (params.get('title')    or ['Unknown Movie'])[0]
        quality  = (params.get('quality')  or [''])[0]
        movie_id = (params.get('movie_id') or [''])[0]
        if not magnet:
            show_error('Invalid download link: no magnet URI found.')
            return
    except Exception as exc:
        show_error(f'Could not parse download URL:\n{exc}')
        return

    cfg = load_config()
    if not cfg.get('consent_given'):
        if not show_consent_dialog(title):
            return
        cfg['consent_given'] = True
        save_config(cfg)

    if not is_backend_running():
        show_info('Starting Download Manager…', 'The download service is starting. Please wait.')
        start_backend()
        if not is_backend_running():
            show_error(
                'Download Manager is not running.\n'
                'Please launch "Streamore" from the Start Menu first, then try again.'
            )
            return

    try:
        resp = requests.post(
            f'{BACKEND_URL}/api/download/start',
            json={
                'movie_id':    movie_id or title,
                'movie_title': title,
                'quality':     quality or 'unknown',
                'magnet_link': magnet,
            },
            timeout=10,
        )
        data = resp.json()
        if data.get('success') or data.get('download_id'):
            show_toast('⬇️ Download Queued', f'{title} ({quality}) has been added to your downloads.')
        else:
            show_error(f'Could not queue download:\n{data.get("error", "Unknown error")}')
    except Exception as exc:
        show_error(f'Could not reach the Download Manager.\n\nDetail: {exc}')


# ─── Standalone GUI app ─────────────────────────────────────────────────────
def open_manager_window():
    """Launch the standalone PyQt6 download manager."""
    import subprocess
    gui_script = Path(__file__).resolve().parent / 'downloader_app.py'
    if gui_script.exists():
        subprocess.Popen([sys.executable, str(gui_script)], **_hidden_subprocess_kwargs())
    else:
        import webbrowser
        webbrowser.open(f'{BACKEND_URL}/downloads')


# ─── Tray icon image ──────────────────────────────────────────────────────────
def _make_icon_image():
    from PIL import Image, ImageDraw
    img  = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill=(20, 20, 36, 255))
    draw.rectangle([26, 12, 38, 36], fill=(108, 99, 255, 255))
    draw.polygon([(14, 28), (50, 28), (32, 50)], fill=(108, 99, 255, 255))
    draw.rectangle([18, 52, 46, 56], fill=(108, 99, 255, 255))
    return img


# ─── Tray app mode (legacy — now just launches GUI) ──────────────────────────
def run_tray():
    """Launch the standalone GUI download manager directly."""
    # The new downloader_app.py runs its own bridge server and tray icon
    import subprocess
    gui_script = Path(__file__).resolve().parent / 'downloader_app.py'
    if gui_script.exists():
        proc = subprocess.Popen(
            [sys.executable, str(gui_script)] + sys.argv[1:],
            **_hidden_subprocess_kwargs()
        )
        proc.wait()
    else:
        # Fallback: old tray mode
        t = threading.Thread(target=run_detection_server, daemon=True)
        t.start()

    try:
        import pystray
    except ImportError:
        logger.warning('pystray not installed; running backend in foreground mode')
        proc = start_backend()
        try:
            if proc:
                proc.wait()
            else:
                time.sleep(9999)
        except KeyboardInterrupt:
            pass
        return

    icon_image     = _make_icon_image()
    backend_proc: list = [None]

    def open_manager(_icon=None, _item=None):
        threading.Thread(target=open_manager_window, daemon=True).start()

    def quit_app(icon, _item):
        proc = backend_proc[0]
        if proc and proc.poll() is None:
            proc.terminate()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem('⬇️ Open Download Manager', open_manager, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Quit', quit_app),
    )

    icon = pystray.Icon('Streamore', icon_image, 'Streamore Download Manager', menu)

    def _start():
        proc = start_backend()
        backend_proc[0] = proc
        if proc and is_backend_running():
            show_toast('Streamore', 'Download Manager started and ready.')
        elif not is_backend_running():
            logger.warning('Backend did not start successfully')

    threading.Thread(target=_start, daemon=True).start()
    icon.run()


# ─── Entry point ─────────────────────────────────────────────────────────────
def main():
    # 2. If invoked with a streamore:// link, just forward it and exit
    if len(sys.argv) > 1 and sys.argv[1].lower().startswith('streamore://'):
        handle_protocol(sys.argv[1])
    else:
        run_tray()


if __name__ == '__main__':
    main()
