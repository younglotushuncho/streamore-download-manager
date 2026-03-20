"""
Streamore Download Manager Ã¢â‚¬â€œ Standalone Desktop App
=====================================================
A fully native PyQt6 application (like qBittorrent) that:
  Ã¢â‚¬Â¢ Shows all active/completed/error downloads in a rich table
  Ã¢â‚¬Â¢ Displays a real-time speed graph
  Ã¢â‚¬Â¢ Lives in the system tray so it's always reachable
  Ã¢â‚¬Â¢ Runs the bridge HTTP server on localhost:57432 so the web app
    (streamore.vercel.app) can auto-detect it and push downloads

Run:
    python desktop/downloader_app.py
    python desktop/downloader_app.py streamore://download?...   Ã¢â€ Â protocol handler
"""

import sys
import os
import json
import re
import socket
import time
import zipfile
import shutil
import hashlib
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import deque
from discord_rpc import DiscordRPCManager

# Ã¢â€â‚¬Ã¢â€â‚¬ DLL Safety Shield Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
IS_BUNDLED = getattr(sys, 'frozen', False) or '__compiled__' in globals()

if IS_BUNDLED:
    import os
    # When bundled, ensure we only use internal DLLs to avoid shadowing from system paths
    _meipass = getattr(sys, '_MEIPASS', None)
    if _meipass:
        # Add the internal Lib folder to the DLL search path (Python 3.8+)
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(_meipass)
        # Force Qt to find its own plugins in the bundled folder
        os.environ['QT_PLUGIN_PATH'] = os.path.join(_meipass, 'PyQt6', 'Qt6', 'plugins')

# Add project root to path for backend/shared imports
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)


def _windows_hidden_subprocess_kwargs() -> dict:
    """Return Windows-only subprocess kwargs to hide child console windows."""
    if os.name != 'nt':
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        'creationflags': subprocess.CREATE_NO_WINDOW,
        'startupinfo': startupinfo,
    }


def _hide_own_console_window() -> None:
    """Hide this process console window on Windows unless explicitly enabled."""
    if os.name != 'nt' or os.environ.get('STREAMORE_SHOW_CONSOLE') == '1':
        return

    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        # If we cannot hide it, continue normally.
        pass


_hide_own_console_window()

# Ã¢â€â‚¬Ã¢â€â‚¬ Qt imports Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QListWidget, QListWidgetItem,
    QAbstractItemView, QFrame, QMenuBar, QMenu, QDialog, QCheckBox,
    QDialogButtonBox, QSystemTrayIcon, QMessageBox, QFileDialog, QScrollArea,
    QSplitter, QToolButton, QStatusBar, QStyle, QInputDialog, QLineEdit,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QPoint, QRect,
    QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QFontDatabase,
    QLinearGradient, QIcon, QPalette, QAction, QPixmap, QPolygon,
    QDesktopServices, QKeySequence,
)
from PyQt6.QtCore import QUrl
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

# Ã¢â€â‚¬Ã¢â€â‚¬ Third-party optional Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    class _CompatResponse:
        def __init__(self, status_code: int, text: str):
            self.status_code = status_code
            self.text = text

        def json(self):
            return json.loads(self.text) if self.text else {}

    class _CompatRequests:
        @staticmethod
        def get(url: str, timeout: int = 5, **kwargs):
            req = Request(url, method='GET')
            try:
                with urlopen(req, timeout=timeout) as resp:
                    body = resp.read().decode('utf-8', errors='replace')
                    return _CompatResponse(getattr(resp, 'status', 200), body)
            except HTTPError as e:
                body = e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else ''
                return _CompatResponse(e.code, body)
            except URLError as e:
                raise RuntimeError(str(e))

        @staticmethod
        def post(url: str, json: dict | None = None, timeout: int = 5, **kwargs):
            payload = b''
            headers = {'Content-Type': 'application/json'}
            if json is not None:
                payload = __import__('json').dumps(json).encode('utf-8')
            req = Request(url, data=payload, headers=headers, method='POST')
            try:
                with urlopen(req, timeout=timeout) as resp:
                    body = resp.read().decode('utf-8', errors='replace')
                    return _CompatResponse(getattr(resp, 'status', 200), body)
            except HTTPError as e:
                body = e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else ''
                return _CompatResponse(e.code, body)
            except URLError as e:
                raise RuntimeError(str(e))

    _requests = _CompatRequests()
    HAS_REQUESTS = True

try:
    import pystray
    from PIL import Image as _PILImage, ImageDraw as _PILDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# Ã¢â€â‚¬Ã¢â€â‚¬ Logging Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('StreamoreDownloader')

# Ã¢â€â‚¬Ã¢â€â‚¬ Constants Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
DETECTION_PORT = 57432
DETECTION_HOST = '127.0.0.1'
try:
    from shared.version import __version__ as _APP_VER
except Exception:
    _APP_VER = '1.0.0'

APP_VERSION    = _APP_VER
APP_NAME       = 'StreamoreManager'
def _is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except socket.error:
            return True

def _find_free_backend_port(start: int = 58432, count: int = 10) -> int:
    for p in range(start, start + count):
        if not _is_port_in_use(p):
            return p
    return start

_PORT = int(os.environ.get('STREAMORE_BACKEND_PORT', '58432'))
if 'STREAMORE_BACKEND_URL' not in os.environ and 'STREAMORE_BACKEND_PORT' not in os.environ:
    _PORT = _find_free_backend_port(_PORT)

BACKEND_URL = os.environ.get('STREAMORE_BACKEND_URL', f'http://127.0.0.1:{_PORT}').rstrip('/')
os.environ['FLASK_PORT'] = str(_PORT) # Ensure backend picks it up
POLL_INTERVAL  = 2000       # ms between download list refresh
SPEED_HISTORY  = 60         # data points in speed graph
POLL_FAIL_CLEAR_THRESHOLD = 4
UPDATE_BASE_URL = os.environ.get(
    'STREAMORE_UPDATE_BASE_URL',
    'https://pub-de03d3c6527b425fa2ee53203c4ea5fc.r2.dev'
).rstrip('/')
UPDATE_INFO_URL = f'{UPDATE_BASE_URL}/latest.json'
UPDATE_DOWNLOAD_URL = f'{UPDATE_BASE_URL}/StreamoreSetup.exe'
UPDATE_CHECK_HOURS = 6
FORCED_UPDATE_RETRY_SECONDS = 30
FORCED_UPDATE_STALL_SECONDS = 45
ACTION_DEBOUNCE_SECONDS = 0.9
FORCE_START_COOLDOWN_SECONDS = 20
QUEUED_FORCE_START_DELAY_SECONDS = 25
QUEUE_BACKEND_START_WAIT_SECONDS = 2.5
LOW_DISK_WARN_GB = 5
BACKEND_WATCHDOG_MAX_RETRIES = 3   # max auto-restart attempts before alerting the user
STARTUP_SELF_HEAL_MAX_ATTEMPTS = 4
STARTUP_SELF_HEAL_RETRY_SECONDS = 3

ALLOWED_ORIGINS = [
    'https://streamore-five.vercel.app',   # production
    'https://streamore.vercel.app',
    'https://streamore-beta.vercel.app',
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:3002',
    'http://localhost:5173',
    'http://localhost:5174',
    'http://localhost',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
    'null',
]

CONFIG_DIR  = Path(os.environ.get('APPDATA', '~')).expanduser() / 'StreamoreManager'
CONFIG_FILE = CONFIG_DIR / 'config.json'
BACKEND_START_ERROR = ''
_UPDATE_LOCK = threading.Lock()
_UPDATE_LOCKED = False

# Ã¢â€â‚¬Ã¢â€â‚¬ Color palette Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
DARK_C = {
    'bg':       '#0d0d1a',
    'surface':  '#12121f',
    'card':     '#18182b',
    'border':   '#2a2a3d',
    'accent':   '#6c63ff',
    'accent2':  '#a78bfa',
    'green':    '#22c55e',
    'yellow':   '#f59e0b',
    'red':      '#ef4444',
    'text':     '#f0f0ff',
    'muted':    '#7b7b9a',
    'upload':   '#3b82f6',
}
LIGHT_C = {
    'bg':       '#f8f9fa',
    'surface':  '#ffffff',
    'card':     '#f1f3f5',
    'border':   '#dee2e6',
    'accent':   '#6366f1',
    'accent2':  '#8b5cf6',
    'green':    '#10b981',
    'yellow':   '#f59e0b',
    'red':      '#ef4444',
    'text':     '#1f2937',
    'muted':    '#6b7280',
    'upload':   '#3b82f6',
}
C = DARK_C.copy()

STATE_COLOR = {
    'downloading': C['accent'],
    'active':      C['accent'],
    'waiting':     C['yellow'],
    'queued':      C['yellow'],
    'complete':    C['green'],
    'completed':   C['green'],
    'seeding':     C['green'],
    'paused':      C['muted'],
    'pausing':     C['muted'],
    'error':       C['red'],
    'removed':     C['muted'],
}

STATE_LABEL = {
    'downloading': 'Downloading',
    'active':      'Downloading',
    'waiting':     'Queued',
    'queued':      'Queued',
    'complete':    'Complete',
    'completed':   'Complete',
    'seeding':     'Seeding',
    'paused':      'Paused',
    'pausing':     'Pausing',
    'error':       'Error',
    'removed':     'Removed',
}

# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# HELPER FUNCTIONS
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

def fmt_bytes(b: int) -> str:
    if not b: return '0 B'
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if b < 1024: return f'{b:.1f} {unit}'
        b /= 1024
    return f'{b:.1f} PB'

def fmt_speed(bps: int) -> str:
    return fmt_bytes(bps) + '/s' if bps else '-'

def fmt_eta(sec: int) -> str:
    if not sec or sec < 0: return '-'
    if sec < 60: return f'{sec}s'
    if sec < 3600: return f'{sec // 60}m {sec % 60}s'
    return f'{sec // 3600}h {(sec % 3600) // 60}m'

def is_backend_running() -> bool:
    if not HAS_REQUESTS: return False
    try:
        r = _requests.get(f'{BACKEND_URL}/api/health', timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def start_backend():
    """ 
    Start the Flask+SocketIO backend.
    In dev mode, runs backend/app.py via subprocess.
    In bundled mode, imports the backend and runs it in a thread for efficiency.
    """
    global BACKEND_START_ERROR
    BACKEND_START_ERROR = ''
    if IS_BUNDLED:
        # We are bundled in an EXE (PyInstaller or Nuitka)
        logger.info("Starting backend internally (frozen mode)...")
        try:
            # When bundled by PyInstaller with --add-data, modules are in the root
            # or in the internal library folder. 
            import backend.app as backend_app
            def run_flask():
                try:
                    backend_app.run_server()
                except Exception as serve_err:
                    logger.error(f"Internal backend server error: {serve_err}")
            
            t = threading.Thread(target=run_flask, daemon=True)
            t.start()
            logger.info("Internal backend thread started.")
            return
        except Exception as e:
            BACKEND_START_ERROR = str(e)
            logger.error(f"Failed to start backend internally: {e}")
            # Fallback to looking for external exe if the import fails
            exe = Path(sys.executable).parent / 'YTS-Downloader-Backend.exe'
            if exe.exists():
                subprocess.Popen([str(exe)], **_windows_hidden_subprocess_kwargs())
            return

    # DEV MODE: try running backend/app.py via subprocess
    root = Path(__file__).resolve().parent.parent
    backend_script = root / 'backend' / 'app.py'
    if backend_script.exists():
        logger.info(f"Starting backend from source: {backend_script}")
        try:
            subprocess.Popen([sys.executable, str(backend_script)], **_windows_hidden_subprocess_kwargs())
        except Exception as e:
            BACKEND_START_ERROR = str(e)
    else:
        BACKEND_START_ERROR = f'Backend script not found: {backend_script}'
        logger.warning("Could not find backend script to start.")

def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        except Exception: pass
    return {}

def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding='utf-8')


def is_update_locked() -> bool:
    with _UPDATE_LOCK:
        return bool(_UPDATE_LOCKED)


def set_update_locked(locked: bool):
    global _UPDATE_LOCKED
    with _UPDATE_LOCK:
        _UPDATE_LOCKED = bool(locked)


# ── Sleep / Resume Watchdog ──────────────────────────────────────────────────

class SleepResumeWatcher(QThread):
    """
    Detects system sleep/resume by watching for jumps in the monotonic clock.
    When the real wall-clock advances much faster than the monotonic clock
    (i.e. the machine was suspended), fires `resumed` so the app can restart
    aria2 and force-resume stalled downloads.
    """
    resumed = pyqtSignal()

    _CHECK_INTERVAL_S = 5    # how often to poll (seconds)
    _JUMP_THRESHOLD_S = 15   # minimum clock jump to treat as a sleep/wake

    def run(self):
        last_mono = time.monotonic()
        last_wall = time.time()
        while True:
            time.sleep(self._CHECK_INTERVAL_S)
            now_mono = time.monotonic()
            now_wall = time.time()
            mono_elapsed = now_mono - last_mono
            wall_elapsed = now_wall - last_wall
            # If wall time jumped much more than monotonic time, the machine slept.
            if wall_elapsed - mono_elapsed > self._JUMP_THRESHOLD_S:
                logger.info(f'Sleep/resume detected: wall={wall_elapsed:.1f}s mono={mono_elapsed:.1f}s')
                self.resumed.emit()
            last_mono = now_mono
            last_wall = now_wall


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# SETTINGS DIALOG
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

class TelemetryManager:
    """Opt-in, privacy-safe, failure counters only."""
    _url = 'https://streamore-five.vercel.app/api/telemetry'
    
    @classmethod
    def track_failure(cls, category: str, error_msg: str):
        cfg = load_config()
        if not cfg.get('telemetry_opt_in', False):
            return
        
        def _send():
            try:
                payload = {
                    'app_version': APP_VERSION,
                    'category': category,
                    'error_excerpt': str(error_msg)[:100],
                    'is_error': True
                }
                if HAS_REQUESTS:
                    _requests.post(cls._url, json=payload, timeout=5)
            except Exception:
                pass
        
        import threading
        threading.Thread(target=_send, daemon=True).start()

    @classmethod
    def track_event(cls, name: str, properties: dict = None):
        cfg = load_config()
        if not cfg.get('telemetry_opt_in', False):
            return
        
        def _send():
            try:
                payload = {
                    'app_version': APP_VERSION,
                    'event': name,
                    'properties': properties or {}
                }
                if HAS_REQUESTS:
                    _requests.post(cls._url, json=payload, timeout=5)
            except Exception:
                pass
        
        import threading
        threading.Thread(target=_send, daemon=True).start()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Streamore - Settings')
        self.setMinimumSize(560, 640)
        self.resize(620, 760)
        self.setStyleSheet(f'background:{C["card"]}; color:{C["text"]};')
        self._cfg = load_config()
        self._settings = {
            'download_path': self._cfg.get('download_dir') or str(Path.home() / 'Downloads' / 'Streamore'),
            'organize_by_genre': True,
            'remove_torrent_after_send': False,
            'theme_is_light': False,
            'telemetry_opt_in': False,
            'language': 'en',
            'max_download_speed': 0,
            'max_upload_speed': 0,
            'max_concurrent': 5,
            'max_connections': 16,
            'bt_max_peers': 0,
            'seed_ratio': 0.0,
            'seed_time': 0,
            'enable_dht': True,
            'enable_pex': True,
            'stop_seeding': False,
            'bandwidth_schedule_enabled': False,
            'bandwidth_day_start': '08:00',
            'bandwidth_day_end': '23:00',
            'bandwidth_day_dl': 0,
            'bandwidth_day_ul': 0,
            'bandwidth_night_dl': 0,
            'bandwidth_night_ul': 0,
        }
        self._load_backend_settings()
        self._build_ui()

    def _load_backend_settings(self):
        if not HAS_REQUESTS:
            return
        try:
            r = _requests.get(f'{BACKEND_URL}/api/settings', timeout=4)
            if r.ok:
                data = r.json().get('settings') or {}
                self._settings.update(data)
            tr = _requests.get(f'{BACKEND_URL}/api/torrent-settings', timeout=4)
            if tr.ok:
                tdata = tr.json().get('settings') or {}
                self._settings.update(tdata)
            self._normalize_settings()
        except Exception as e:
            logger.debug(f'Could not fetch settings from backend: {e}')

    def _normalize_settings(self):
        bool_keys = {
            'organize_by_genre',
            'remove_torrent_after_send',
            'theme_is_light',
            'telemetry_opt_in',
            'enable_dht',
            'enable_pex',
            'stop_seeding',
            'bandwidth_schedule_enabled',
        }
        int_keys = {
            'max_download_speed',
            'max_upload_speed',
            'max_concurrent',
            'max_connections',
            'bt_max_peers',
            'seed_time',
            'bandwidth_day_dl',
            'bandwidth_day_ul',
            'bandwidth_night_dl',
            'bandwidth_night_ul',
        }
        float_keys = {'seed_ratio'}

        for k in bool_keys:
            if k in self._settings:
                v = self._settings.get(k)
                if isinstance(v, bool):
                    self._settings[k] = v
                else:
                    self._settings[k] = str(v).strip().lower() in ('1', 'true', 'yes', 'on')
        for k in int_keys:
            if k in self._settings:
                self._settings[k] = self._to_int(self._settings.get(k), 0)
        for k in float_keys:
            if k in self._settings:
                self._settings[k] = self._to_float(self._settings.get(k), 0.0)

        # Normalize schedule times
        for k, default in (('bandwidth_day_start', '08:00'), ('bandwidth_day_end', '23:00')):
            val = str(self._settings.get(k, default) or default).strip()
            if not re.match(r'^\d{1,2}:\d{2}$', val):
                val = default
            self._settings[k] = val

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _to_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C['card']}; }}")

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(14)

        input_style = f"""
            QLineEdit {{
                background: {C['bg']}; border: 1px solid {C['border']};
                border-radius: 6px; padding: 8px 10px; color: {C['text']};
            }}
        """

        def section_label(text: str):
            lbl = QLabel(text)
            lbl.setStyleSheet(f'color:{C["muted"]}; font-weight:700; font-size:11px; text-transform:uppercase;')
            lay.addWidget(lbl)

        section_label('General')
        row = QHBoxLayout()
        self.path_edit = QLineEdit(self._settings.get('download_path') or str(Path.home() / 'Downloads' / 'Streamore'))
        self.path_edit.setStyleSheet(input_style)
        row.addWidget(self.path_edit, 1)

        browse_b = QPushButton('Browse...')
        browse_b.setStyleSheet(f"""
            QPushButton {{
                background: {C['border']}; color: {C['text']};
                border: none; border-radius: 6px; padding: 8px 15px;
            }}
            QPushButton:hover {{ background: {C['accent']}44; }}
        """)
        browse_b.clicked.connect(self._browse)
        row.addWidget(browse_b)
        lay.addLayout(row)

        self.organize_by_genre_cb = QCheckBox('Organize downloads by genre')
        self.organize_by_genre_cb.setChecked(bool(self._settings.get('organize_by_genre', True)))
        lay.addWidget(self.organize_by_genre_cb)

        self.remove_torrent_cb = QCheckBox('Remove .torrent after send')
        self.remove_torrent_cb.setChecked(bool(self._settings.get('remove_torrent_after_send', False)))
        lay.addWidget(self.remove_torrent_cb)

        self.enable_dht_cb = QCheckBox('Enable DHT')
        self.enable_dht_cb.setChecked(bool(self._settings.get('enable_dht', True)))
        lay.addWidget(self.enable_dht_cb)

        self.enable_pex_cb = QCheckBox('Enable PEX')
        self.enable_pex_cb.setChecked(bool(self._settings.get('enable_pex', True)))
        lay.addWidget(self.enable_pex_cb)

        misc_row = QHBoxLayout()
        self.language_edit = QLineEdit(str(self._settings.get('language', 'en')))
        self.language_edit.setStyleSheet(input_style)
        self.language_edit.setPlaceholderText('Language (e.g. en)')
        misc_row.addWidget(self.language_edit, 1)

        self.theme_light_cb = QCheckBox('Light mode')
        self.theme_light_cb.setChecked(bool(self._settings.get('theme_is_light', False)))
        misc_row.addWidget(self.theme_light_cb)
        lay.addLayout(misc_row)

        section_label('Privacy & Diagnostics')
        self.telemetry_opt_in_cb = QCheckBox('Share anonymous failure telemetry (opt-in)')
        self.telemetry_opt_in_cb.setChecked(bool(self._settings.get('telemetry_opt_in', False)))
        self.telemetry_opt_in_cb.setToolTip('Only sends counts of errors/stalls to improve the app. No private data.')
        lay.addWidget(self.telemetry_opt_in_cb)

        section_label('Torrent Controls')
        def labeled_input(label_text: str, widget: QLineEdit):
            box = QVBoxLayout()
            box.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f'color:{C["muted"]}; font-size:12px;')
            box.addWidget(lbl)
            box.addWidget(widget)
            return box

        grid1 = QHBoxLayout()
        self.max_download_speed_edit = QLineEdit(str(self._settings.get('max_download_speed', 0)))
        self.max_download_speed_edit.setStyleSheet(input_style)
        self.max_download_speed_edit.setPlaceholderText('Max download KiB/s (0 = unlimited)')
        grid1.addLayout(labeled_input('Max download (KiB/s)', self.max_download_speed_edit), 1)

        self.max_upload_speed_edit = QLineEdit(str(self._settings.get('max_upload_speed', 0)))
        self.max_upload_speed_edit.setStyleSheet(input_style)
        self.max_upload_speed_edit.setPlaceholderText('Max upload KiB/s (0 = unlimited)')
        grid1.addLayout(labeled_input('Max upload (KiB/s)', self.max_upload_speed_edit), 1)
        lay.addLayout(grid1)

        grid2 = QHBoxLayout()
        self.max_concurrent_edit = QLineEdit(str(self._settings.get('max_concurrent', 5)))
        self.max_concurrent_edit.setStyleSheet(input_style)
        self.max_concurrent_edit.setPlaceholderText('Max concurrent downloads')
        grid2.addLayout(labeled_input('Max concurrent', self.max_concurrent_edit), 1)

        self.max_connections_edit = QLineEdit(str(self._settings.get('max_connections', 16)))
        self.max_connections_edit.setStyleSheet(input_style)
        self.max_connections_edit.setPlaceholderText('Connections per server')
        grid2.addLayout(labeled_input('Connections/server', self.max_connections_edit), 1)
        lay.addLayout(grid2)

        grid3 = QHBoxLayout()
        self.bt_max_peers_edit = QLineEdit(str(self._settings.get('bt_max_peers', 0)))
        self.bt_max_peers_edit.setStyleSheet(input_style)
        self.bt_max_peers_edit.setPlaceholderText('BT max peers (0 = unlimited)')
        grid3.addLayout(labeled_input('Max BT peers', self.bt_max_peers_edit), 1)

        self.stop_seeding_cb = QCheckBox('Stop seeding after download')
        self.stop_seeding_cb.setChecked(bool(self._settings.get('stop_seeding', False)))
        self.stop_seeding_cb.setStyleSheet(f'color:{C["text"]};')
        self.stop_seeding_cb.stateChanged.connect(self._toggle_seeding_controls)
        grid3.addWidget(self.stop_seeding_cb)

        self.seed_time_edit = QLineEdit(str(self._settings.get('seed_time', 0)))
        self.seed_time_edit.setStyleSheet(input_style)
        self.seed_time_edit.setPlaceholderText('Seed time (seconds)')
        grid3.addLayout(labeled_input('Seed time (seconds)', self.seed_time_edit), 1)
        lay.addLayout(grid3)

        self.seed_ratio_edit = QLineEdit(str(self._settings.get('seed_ratio', 0)))
        self.seed_ratio_edit.setStyleSheet(input_style)
        self.seed_ratio_edit.setPlaceholderText('Seed ratio (0 = off)')
        lay.addLayout(labeled_input('Seed ratio', self.seed_ratio_edit))

        self._toggle_seeding_controls()

        section_label('Bandwidth Scheduler')
        sched_row = QHBoxLayout()
        self.sched_enable_cb = QCheckBox('Enable scheduler')
        self.sched_enable_cb.setChecked(bool(self._settings.get('bandwidth_schedule_enabled', False)))
        self.sched_enable_cb.setStyleSheet(f'color:{C["text"]};')
        self.sched_enable_cb.stateChanged.connect(self._toggle_schedule_controls)
        sched_row.addWidget(self.sched_enable_cb)
        sched_row.addStretch()
        lay.addLayout(sched_row)

        sched_times = QHBoxLayout()
        self.sched_day_start = QLineEdit(str(self._settings.get('bandwidth_day_start', '08:00')))
        self.sched_day_start.setStyleSheet(input_style)
        self.sched_day_start.setPlaceholderText('Day start (HH:MM)')
        sched_times.addLayout(labeled_input('Day start', self.sched_day_start), 1)

        self.sched_day_end = QLineEdit(str(self._settings.get('bandwidth_day_end', '23:00')))
        self.sched_day_end.setStyleSheet(input_style)
        self.sched_day_end.setPlaceholderText('Day end (HH:MM)')
        sched_times.addLayout(labeled_input('Day end', self.sched_day_end), 1)
        lay.addLayout(sched_times)

        sched_day = QHBoxLayout()
        self.sched_day_dl = QLineEdit(str(self._settings.get('bandwidth_day_dl', 0)))
        self.sched_day_dl.setStyleSheet(input_style)
        self.sched_day_dl.setPlaceholderText('Day max download KiB/s')
        sched_day.addLayout(labeled_input('Day max download', self.sched_day_dl), 1)

        self.sched_day_ul = QLineEdit(str(self._settings.get('bandwidth_day_ul', 0)))
        self.sched_day_ul.setStyleSheet(input_style)
        self.sched_day_ul.setPlaceholderText('Day max upload KiB/s')
        sched_day.addLayout(labeled_input('Day max upload', self.sched_day_ul), 1)
        lay.addLayout(sched_day)

        sched_night = QHBoxLayout()
        self.sched_night_dl = QLineEdit(str(self._settings.get('bandwidth_night_dl', 0)))
        self.sched_night_dl.setStyleSheet(input_style)
        self.sched_night_dl.setPlaceholderText('Night max download KiB/s')
        sched_night.addLayout(labeled_input('Night max download', self.sched_night_dl), 1)

        self.sched_night_ul = QLineEdit(str(self._settings.get('bandwidth_night_ul', 0)))
        self.sched_night_ul.setStyleSheet(input_style)
        self.sched_night_ul.setPlaceholderText('Night max upload KiB/s')
        sched_night.addLayout(labeled_input('Night max upload', self.sched_night_ul), 1)
        lay.addLayout(sched_night)

        self._toggle_schedule_controls()

        lay.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        btns = QHBoxLayout()
        btns.addStretch()

        def _btn(label, color, primary=False):
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {color if primary else 'transparent'};
                    color: {C['text']};
                    border: {'none' if primary else '1px solid ' + C['border']};
                    border-radius: 8px; padding: 10px 24px; font-weight: 700;
                }}
                QPushButton:hover {{ background: {color if primary else C['surface']}; opacity: 0.9; }}
            """)
            return b

        cancel_b = _btn('Cancel', C['border'])
        save_b = _btn('Save Settings', C['accent'], primary=True)
        cancel_b.clicked.connect(self.reject)
        save_b.clicked.connect(self._save)
        btns.addWidget(cancel_b)
        btns.addWidget(save_b)
        outer.addLayout(btns)

    def _browse(self):
        curr = self.path_edit.text()
        path = QFileDialog.getExistingDirectory(self, 'Select Download Folder', curr)
        if path:
            self.path_edit.setText(path)

    def _toggle_seeding_controls(self):
        if not hasattr(self, 'stop_seeding_cb'):
            return
        stop = self.stop_seeding_cb.isChecked()
        if hasattr(self, 'seed_time_edit'):
            self.seed_time_edit.setEnabled(not stop)
        if hasattr(self, 'seed_ratio_edit'):
            self.seed_ratio_edit.setEnabled(not stop)

    def _toggle_schedule_controls(self):
        if not hasattr(self, 'sched_enable_cb'):
            return
        enabled = self.sched_enable_cb.isChecked()
        for w in (
            getattr(self, 'sched_day_start', None),
            getattr(self, 'sched_day_end', None),
            getattr(self, 'sched_day_dl', None),
            getattr(self, 'sched_day_ul', None),
            getattr(self, 'sched_night_dl', None),
            getattr(self, 'sched_night_ul', None),
        ):
            if w is not None:
                w.setEnabled(enabled)

    def _save(self):
        download_path = self.path_edit.text().strip() or str(Path.home() / 'Downloads' / 'Streamore')
        stop_seeding = self.stop_seeding_cb.isChecked() if hasattr(self, 'stop_seeding_cb') else False
        seed_ratio = 0.0 if stop_seeding else self._to_float(self.seed_ratio_edit.text(), 0.0)
        seed_time = 0 if stop_seeding else self._to_int(self.seed_time_edit.text(), 0)
        settings_payload = {
            'download_path': download_path,
            'download_dir': download_path,
            'organize_by_genre': self.organize_by_genre_cb.isChecked(),
            'remove_torrent_after_send': self.remove_torrent_cb.isChecked(),
            'theme_is_light': self.theme_light_cb.isChecked(),
            'telemetry_opt_in': self.telemetry_opt_in_cb.isChecked(),
            'language': self.language_edit.text().strip() or 'en',
            'max_download_speed': self._to_int(self.max_download_speed_edit.text(), 0),
            'max_upload_speed': self._to_int(self.max_upload_speed_edit.text(), 0),
            'max_concurrent': max(1, self._to_int(self.max_concurrent_edit.text(), 1)),
            'max_connections': max(1, self._to_int(self.max_connections_edit.text(), 16)),
            'bt_max_peers': self._to_int(self.bt_max_peers_edit.text(), 0),
            'seed_ratio': seed_ratio,
            'seed_time': seed_time,
            'enable_dht': self.enable_dht_cb.isChecked(),
            'enable_pex': self.enable_pex_cb.isChecked(),
            'stop_seeding': stop_seeding,
            'bandwidth_schedule_enabled': self.sched_enable_cb.isChecked() if hasattr(self, 'sched_enable_cb') else False,
            'bandwidth_day_start': (self.sched_day_start.text().strip() if hasattr(self, 'sched_day_start') else '08:00') or '08:00',
            'bandwidth_day_end': (self.sched_day_end.text().strip() if hasattr(self, 'sched_day_end') else '23:00') or '23:00',
            'bandwidth_day_dl': self._to_int(self.sched_day_dl.text(), 0) if hasattr(self, 'sched_day_dl') else 0,
            'bandwidth_day_ul': self._to_int(self.sched_day_ul.text(), 0) if hasattr(self, 'sched_day_ul') else 0,
            'bandwidth_night_dl': self._to_int(self.sched_night_dl.text(), 0) if hasattr(self, 'sched_night_dl') else 0,
            'bandwidth_night_ul': self._to_int(self.sched_night_ul.text(), 0) if hasattr(self, 'sched_night_ul') else 0,
        }
        torrent_payload = {
            'max_download_speed': settings_payload['max_download_speed'],
            'max_upload_speed': settings_payload['max_upload_speed'],
            'max_concurrent': settings_payload['max_concurrent'],
            'max_connections': settings_payload['max_connections'],
            'bt_max_peers': settings_payload['bt_max_peers'],
            'seed_ratio': seed_ratio,
            'seed_time': seed_time,
            'enable_dht': settings_payload['enable_dht'],
            'enable_pex': settings_payload['enable_pex'],
        }

        self._cfg['download_dir'] = download_path
        self._cfg.update(settings_payload)
        try:
            save_config(self._cfg)
            backend_ok = False
            if HAS_REQUESTS:
                r1 = _requests.post(f'{BACKEND_URL}/api/settings', json=settings_payload, timeout=4)
                r2 = _requests.post(f'{BACKEND_URL}/api/torrent-settings', json=torrent_payload, timeout=6)
                backend_ok = bool(r1.ok and r2.ok)
            if HAS_REQUESTS and not backend_ok:
                QMessageBox.warning(self, 'Settings', 'Saved locally, but backend did not apply all settings.')
        except Exception as e:
            logger.warning(f'Failed to save settings to backend: {e}')
            QMessageBox.warning(self, 'Settings', f'Settings save failed: {e}')
        self.accept()




# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# UPDATE STATUS DIALOG
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

class UpdateStatusDialog(QDialog):
    """Polished 4-state update dialog: checking / latest / available / error."""
    install_requested = pyqtSignal()

    def __init__(self, parent=None, state='checking',
                 current_version=None, latest_version=None,
                 download_url=None, error_msg=None):
        super().__init__(parent)
        self.setWindowTitle('Streamore Update')
        self.setFixedSize(390, 250)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setStyleSheet(f"""
            QDialog {{
                background: {C['card']};
                color: {C['text']};
                font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 9px 22px;
                font-weight: 700;
                font-size: 13px;
                border: none;
            }}
            QPushButton#installBtn {{
                background: {C['accent']};
                color: #fff;
            }}
            QPushButton#installBtn:hover {{ background: {C['accent2']}; }}
            QPushButton#closeBtn {{ background: {C['border']}; color: {C['text']}; }}
            QPushButton#closeBtn:hover {{ background: {C['surface']}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 22)
        root.setSpacing(12)

        icon_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(46, 46)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel()
        title_lbl.setStyleSheet('font-size: 16px; font-weight: 800;')
        icon_row.addWidget(icon_lbl)
        icon_row.addSpacing(12)
        icon_row.addWidget(title_lbl, 1)
        root.addLayout(icon_row)

        body_lbl = QLabel()
        body_lbl.setWordWrap(True)
        body_lbl.setTextFormat(Qt.TextFormat.RichText)
        body_lbl.setStyleSheet(f'color: {C["muted"]}; font-size: 13px;')
        root.addWidget(body_lbl)

        root.addStretch(1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        close_btn = QPushButton('Close')
        close_btn.setObjectName('closeBtn')
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)

        if state == 'checking':
            icon_lbl.setText('Ã°Å¸â€â€ž')
            icon_lbl.setStyleSheet(f'border-radius:23px; font-size:24px; background:{C["border"]};')
            title_lbl.setText('Checking for updatesÃ¢â‚¬Â¦')
            body_lbl.setText('Please wait while we contact the update server.')
            btn_row.addWidget(close_btn)

        elif state == 'latest':
            icon_lbl.setText('Ã¢Å“â€¦')
            icon_lbl.setStyleSheet('border-radius:23px; font-size:24px; background:#16423c;')
            title_lbl.setText("You're up to date!")
            title_lbl.setStyleSheet(f'font-size:16px; font-weight:800; color:{C["green"]};')
            body_lbl.setText(
                f'<b>Version {current_version or latest_version}</b> is the latest available.<br>'
                'No action needed Ã¢â‚¬â€ you are all good!'
            )
            btn_row.addWidget(close_btn)

        elif state == 'available':
            icon_lbl.setText('Ã°Å¸Å¡â‚¬')
            icon_lbl.setStyleSheet('border-radius:23px; font-size:24px; background:#1e1b4b;')
            title_lbl.setText('Optional Update Available')
            title_lbl.setStyleSheet(f'font-size:16px; font-weight:800; color:{C["accent2"]};')
            body_lbl.setText(
                f'An <b>optional update</b> (Version {latest_version}) is available.<br>'
                f'You are currently on <b>{current_version}</b>.<br><br>'
                'Click <b>Install Now</b> if you wish to download and install it.'
            )
            install_btn = QPushButton('Install Now')
            install_btn.setObjectName('installBtn')
            install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            install_btn.clicked.connect(self.install_requested)
            install_btn.clicked.connect(self.accept)
            btn_row.addWidget(install_btn)
            btn_row.addSpacing(8)
            btn_row.addWidget(close_btn)

        elif state == 'error':
            icon_lbl.setText('Ã¢Å¡Â Ã¯Â¸Â')
            icon_lbl.setStyleSheet('border-radius:23px; font-size:24px; background:#2d1515;')
            title_lbl.setText('Update Check Failed')
            title_lbl.setStyleSheet(f'font-size:16px; font-weight:800; color:{C["red"]};')
            body_lbl.setText(error_msg or 'An unknown error occurred.')
            btn_row.addWidget(close_btn)

        root.addLayout(btn_row)


class ForcedUpdateDialog(QDialog):
    retry_requested = pyqtSignal()
    open_installer_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Update Required')
        self.setFixedSize(460, 250)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background: {C['card']};
                color: {C['text']};
                font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
            }}
            QLabel#title {{ font-size: 18px; font-weight: 800; color: {C['accent2']}; }}
            QLabel#body {{ color: {C['muted']}; font-size: 13px; }}
            QPushButton {{
                background: {C['accent']};
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 9px 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {C['accent2']}; }}
            QProgressBar {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                color: {C['text']};
                text-align: center;
                height: 18px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 {C['accent']}, stop:1 {C['accent2']});
                border-radius: 5px;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(12)

        self._title = QLabel('A mandatory update is required')
        self._title.setObjectName('title')
        lay.addWidget(self._title)

        self._body = QLabel('Checking for the latest installer...')
        self._body.setObjectName('body')
        self._body.setWordWrap(True)
        lay.addWidget(self._body)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat('0%')
        lay.addWidget(self._progress)

        self._retry_btn = QPushButton('Retry Update')
        self._retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._retry_btn.setVisible(False)
        self._retry_btn.clicked.connect(self.retry_requested)
        lay.addWidget(self._retry_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._open_btn = QPushButton('Open Installer Link')
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setVisible(False)
        self._open_btn.clicked.connect(self.open_installer_requested)
        lay.addWidget(self._open_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def set_message(self, message: str):
        self._body.setText(message)

    def set_progress(self, pct: int | None):
        if pct is None:
            self._progress.setRange(0, 0)
            self._progress.setFormat('Working...')
            return
        self._progress.setRange(0, 100)
        p = max(0, min(100, int(pct)))
        self._progress.setValue(p)
        self._progress.setFormat(f'{p}%')

    def allow_retry(self, allowed: bool):
        self._retry_btn.setVisible(bool(allowed))

    def allow_open_installer(self, allowed: bool):
        self._open_btn.setVisible(bool(allowed))

    def reject(self):
        # Non-dismissible while update is required.
        return

    def closeEvent(self, event):
        event.ignore()
# BRIDGE DETECTION SERVER (runs in a daemon thread)
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

# Shared queue: web app posts downloads here, Qt thread picks them up
_download_queue: list = []
_download_queue_lock = threading.Lock()


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass   # silence access log

    def _origin(self): return self.headers.get('Origin', '')

    def _cors(self):
        o = self._origin()
        # Bridge is localhost-only, so allow any browser origin.
        # This avoids CORS failures for custom domains.
        allowed = o if o else '*'
        return {
            'Access-Control-Allow-Origin': allowed,
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Access-Control-Allow-Private-Network',
            'Access-Control-Allow-Private-Network': 'true',
            'Access-Control-Max-Age': '86400',
            'Vary': 'Origin',
        }

    def _json(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        for k, v in self._cors().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in self._cors().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        if self.path == '/ping':
            self._json(200, {
                'ok': True, 'version': APP_VERSION,
                'app': APP_NAME, 'backend': is_backend_running(),
            })
        else:
            self._json(404, {'error': 'not found'})

    def do_POST(self):
        if self.path == '/download':
            if is_update_locked():
                self._json(423, {
                    'error': 'Update required',
                    'message': 'Please update Streamore Download Manager to continue.',
                })
                return

            length = int(self.headers.get('Content-Length', 0))
            try:
                payload = json.loads(self.rfile.read(length))
            except Exception:
                self._json(400, {'error': 'invalid JSON'})
                return

            cfg = load_config()
            origin = self._origin()
            is_web_trigger = bool(origin and payload.get('magnet'))
            if is_web_trigger and not cfg.get('consent_given'):
                cfg['consent_given'] = True
                save_config(cfg)
            if not cfg.get('consent_given'):
                # Push to Qt for consent dialog - block here until answered.
                event = threading.Event()
                result_box = [False]

                def ask():
                    from PyQt6.QtWidgets import QMessageBox, QApplication
                    app = QApplication.instance()
                    if app is None:
                        result_box[0] = False
                        event.set()
                        return
                    mb = QMessageBox()
                    mb.setWindowTitle('Streamore - Allow Download?')
                    mb.setText(
                        f"A website wants to send this download to your manager:\n\n"
                        f"  \"{payload.get('title', 'Unknown Movie')}\"\n\n"
                        "Allow downloads from this website?"
                    )
                    mb.setIcon(QMessageBox.Icon.Question)
                    mb.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    result_box[0] = mb.exec() == QMessageBox.StandardButton.Yes
                    event.set()

                QTimer.singleShot(0, ask)
                event.wait(timeout=30)

                if not result_box[0]:
                    self._json(403, {'error': 'User declined'})
                    return
                cfg['consent_given'] = True
                save_config(cfg)

            with _download_queue_lock:
                _download_queue.append(payload)

            self._json(200, {'ok': True, 'queued': True})
        else:
            self._json(404, {'error': 'not found'})


def run_bridge_server():
    try:
        server = HTTPServer((DETECTION_HOST, DETECTION_PORT), BridgeHandler)
        logger.info(f'Bridge server on {DETECTION_HOST}:{DETECTION_PORT}')
        server.serve_forever()
    except OSError as e:
        logger.warning(f'Bridge server failed to start: {e}')


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# SPEED GRAPH WIDGET
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

class SpeedGraph(QWidget):
    """Mini animated line graph showing download/upload speed history."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dl_data: deque = deque([0] * SPEED_HISTORY, maxlen=SPEED_HISTORY)
        self.ul_data: deque = deque([0] * SPEED_HISTORY, maxlen=SPEED_HISTORY)
        self.setMinimumHeight(70)
        self.setMaximumHeight(90)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def push(self, dl: int, ul: int):
        self.dl_data.append(dl)
        self.ul_data.append(ul)
        self.update()

    def paintEvent(self, _event):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        p.fillRect(0, 0, w, h, QColor(C['surface']))

        mx = max(max(self.dl_data, default=1), max(self.ul_data, default=1), 1)

        def draw_line(data, color_hex, fill_hex):
            pts = list(data)
            n = len(pts)
            if n < 2:
                return
            step = w / (n - 1)
            poly = QPolygon()
            poly.append(QPoint(0, h))
            for i, v in enumerate(pts):
                x = int(i * step)
                y = h - int(v / mx * (h - 4)) - 2
                poly.append(QPoint(x, y))
            poly.append(QPoint(w, h))

            # Fill gradient
            grad = QLinearGradient(0, 0, 0, h)
            c = QColor(fill_hex)
            c.setAlpha(70)
            grad.setColorAt(0, c)
            c2 = QColor(fill_hex)
            c2.setAlpha(0)
            grad.setColorAt(1, c2)
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(poly)

            # Line
            pen = QPen(QColor(color_hex), 1.5)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            pts2 = list(data)
            for i in range(len(pts2) - 1):
                x1 = int(i * step)
                y1 = h - int(pts2[i] / mx * (h - 4)) - 2
                x2 = int((i + 1) * step)
                y2 = h - int(pts2[i + 1] / mx * (h - 4)) - 2
                p.drawLine(QPoint(x1, y1), QPoint(x2, y2))

        draw_line(self.dl_data, C['accent'], C['accent'])
        draw_line(self.ul_data, C['upload'],  C['upload'])
        p.end()

class TrendGraph(QWidget):
    """Simple historical bar/line graph for daily bandwidth."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = [] # List of {'date': '...', 'bytes': ...}
        self.setMinimumHeight(120)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, _event):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(0, 0, w, h, QColor(C['surface']))
        
        if not self.data:
            p.setPen(QColor(C['muted']))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No trend data yet")
            p.end()
            return

        mx = max([d['bytes'] for d in self.data] + [1])
        n = len(self.data)
        bar_w = int(w / max(1, n)) - 4
        
        for i, d in enumerate(self.data):
            val = d['bytes']
            bh = int((val / mx) * (h - 30))
            x = i * (w / n) + 2
            
            # Bar
            rect = QRect(int(x), h - bh - 20, int(bar_w), bh)
            p.fillRect(rect, QColor(C['accent']))
            
            # Label (Date)
            p.setPen(QColor(C['muted']))
            p.setFont(QFont('Segoe UI', 8))
            short_date = d['date'].split('-')[-1] # last 2 chars
            p.drawText(QRect(int(x), h - 18, int(bar_w), 15), Qt.AlignmentFlag.AlignCenter, short_date)
            
        p.end()


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# SIDEBAR NAV
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

FILTERS = [
    ('all',         'All',         None),
    ('downloading', 'Downloading', ['downloading', 'active', 'waiting', 'queued']),
    ('seeding',     'Seeding',      ['seeding']),
    ('paused',      'Paused',       ['paused', 'pausing']),
    ('completed',   'Completed',    ['complete', 'completed']),
    ('error',       'Errors',       ['error']),
]

SIDEBAR_BTN = """
QPushButton {{
    background: transparent;
    color: {fg};
    font-size: 13px;
    font-weight: {fw};
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-left: 3px solid {bdr};
    border-radius: 0px;
}}
QPushButton:hover {{
    background: rgba(108,99,255,0.08);
    color: {fgh};
}}
"""


class SidebarButton(QPushButton):
    def __init__(self, label, active=False, parent=None):
        super().__init__(label, parent)
        self.set_active(active)
        self.setFlat(True)

    def set_active(self, a: bool):
        self._active = a
        self.setStyleSheet(SIDEBAR_BTN.format(
            fg  = C['text']  if a else C['muted'],
            fw  = '700'       if a else '400',
            bdr = C['accent'] if a else 'transparent',
            fgh = C['text'],
        ))


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# DOWNLOAD WORKER (polls backend API)
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

class DownloadPoller(QThread):
    updated = pyqtSignal(list)        # list of download dicts
    backend_state = pyqtSignal(bool)  # backend online/offline
    backend_error = pyqtSignal(str)   # critical error message

    def __init__(self, interval_ms=2000):
        super().__init__()
        self._interval = interval_ms / 1000
        self._running  = True
        self._fail_count = 0

    def run(self):
        while self._running:
            ok = self._fetch()
            time.sleep(self._interval)

    def _fetch(self) -> bool:
        if not HAS_REQUESTS:
            self.backend_state.emit(False)
            return False
        try:
            # /api/downloads can be slower when aria2 is busy or recovering.
            r = _requests.get(f'{BACKEND_URL}/api/downloads', timeout=10)
            if r.status_code == 200:
                data = r.json()
                dls = data.get('downloads') or (data if isinstance(data, list) else [])
                self.updated.emit(dls)
                self._fail_count = 0
                self.backend_state.emit(True)
                
                # Check for critical errors
                try:
                    er = _requests.get(f'{BACKEND_URL}/api/errors/latest', timeout=2)
                    if er.ok:
                        errs = er.json().get('errors') or []
                        if errs:
                            # Just send the latest one if we haven't seen it yet
                            latest = errs[-1][1]
                            self.backend_error.emit(latest)
                except Exception: pass
                
                return True
        except Exception:
            pass

        # If downloads endpoint hiccups, verify backend liveness before marking offline.
        try:
            hr = _requests.get(f'{BACKEND_URL}/api/health', timeout=2)
            if hr.status_code == 200:
                self.backend_state.emit(True)
                return False
        except Exception:
            pass

        self._fail_count += 1
        self.backend_state.emit(False)
        # Avoid flicker/disappear-reappear on temporary backend latency spikes.
        if self._fail_count >= POLL_FAIL_CLEAR_THRESHOLD:
            self.updated.emit([])
        return False

    def stop(self):
        self._running = False
        self.quit()

def show_crash_report(ex_type, ex_value, ex_traceback):
    """Global crash reporter that intercepts unhandled exceptions."""
    import traceback
    from PyQt6.QtWidgets import QMessageBox, QApplication
    
    # Generate error bundle
    err_msg = "".join(traceback.format_exception(ex_type, ex_value, ex_traceback))
    logger.critical(f"FATAL CRASH:\n{err_msg}")
    
    # If app is running, show a QT dialog
    app = QApplication.instance()
    if app:
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Streamore - Application Crash")
            msg.setText("Oops! Streamore encountered a fatal error and needs to close.")
            msg.setInformativeText("A crash report has been generated. Would you like to view the details or restart the app?")
            msg.setDetailedText(err_msg)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Retry)
            msg.setDefaultButton(QMessageBox.StandardButton.Retry)
            
            res = msg.exec()
            if res == QMessageBox.StandardButton.Retry:
                import os
                os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception:
            pass
    sys.exit(1)

class AnalyticsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Streamore - Dashboard')
        self.setMinimumSize(600, 400)
        self.setStyleSheet(f'background:{C["card"]}; color:{C["text"]};')
        self._build_ui()
        QTimer.singleShot(100, self._load_stats)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        title = QLabel('Analytics Dashboard')
        title.setStyleSheet(f'color:{C["accent"]}; font-size:20px; font-weight:800;')
        lay.addWidget(title)

        self._grid = QGridLayout()
        self._grid.setSpacing(15)
        lay.addLayout(self._grid)

        def _card(title, value, row, col, icon=''):
            w = QFrame()
            w.setStyleSheet(f'background:{C["surface"]}; border:1px solid {C["border"]}; border-radius:12px;')
            vlay = QVBoxLayout(w)
            tl = QLabel(title)
            tl.setStyleSheet(f'color:{C["muted"]}; font-size:11px; font-weight:700; text-transform:uppercase;')
            vl = QLabel(value)
            vl.setStyleSheet(f'color:{C["text"]}; font-size:24px; font-weight:800;')
            vlay.addWidget(tl)
            vlay.addWidget(vl)
            self._grid.addWidget(w, row, col)
            return vl

        self._lbl_total_dl = _card('Total Downloads', '0', 0, 0)
        self._lbl_completed = _card('Completed', '0', 0, 1)
        self._lbl_failed = _card('Failed', '0', 1, 0)
        self._lbl_total_bytes = _card('Total Bandwidth', '0 B', 1, 1)

        lay.addWidget(QLabel('7-Day Bandwidth Trend (MB)'))
        self._trend_graph = TrendGraph()
        lay.addWidget(self._trend_graph)

        lay.addStretch()
        
        btn_close = QPushButton('Close')
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {C['border']}; color: {C['text']};
                border: none; border-radius: 8px; padding: 10px 24px; font-weight: 600;
            }}
            QPushButton:hover {{ background: rgba(108,99,255,0.2); }}
        """)
        lay.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignRight)

    def _load_stats(self):
        if not HAS_REQUESTS: return
        try:
            r = _requests.get(f'{BACKEND_URL}/api/analytics', timeout=5)
            if r.ok:
                stats = r.json().get('stats') or {}
                self._lbl_total_dl.setText(str(stats.get('total_downloads', 0)))
                self._lbl_completed.setText(str(stats.get('completed', 0)))
                self._lbl_failed.setText(str(stats.get('failed', 0)))
                self._lbl_total_bytes.setText(fmt_bytes(stats.get('total_bytes', 0)))
                self._trend_graph.set_data(stats.get('trend', []))
        except Exception as e:
            logger.debug(f'Analytics load error: {e}')

class UpdateWorker(QThread):
    result_ready = pyqtSignal(object, bool)
    error_ready = pyqtSignal(str, bool)

    def __init__(self, parent, fetch_func, notify_if_latest):
        super().__init__(parent)
        self.fetch_func = fetch_func
        self.notify_if_latest = notify_if_latest

    def run(self):
        try:
            info = self.fetch_func()
            self.result_ready.emit(info or {}, self.notify_if_latest)
        except Exception as e:
            self.error_ready.emit(str(e), self.notify_if_latest)


class DownloadManagerWindow(QMainWindow):
    # Signal emitted from the bridge thread to push a new download to Qt
    new_download_from_web = pyqtSignal(dict)
    background_ok = pyqtSignal(object, object)
    background_err = pyqtSignal(object, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'Streamore Download Manager {APP_VERSION}')
        self.resize(1100, 680)
        self.setMinimumSize(800, 500)
        self._downloads: list[dict] = []
        self._last_download_states: dict[str, str] = {}
        self._active_filter = 'all'
        self._backend_online = False
        self._total_dl = 0
        self._total_ul = 0
        self._search_text = ''
        self._schedule_state = None
        self._schedule_limits = {'dl': None, 'ul': None}
        self._last_status_fetch = 0
        self._update_lock_active = False
        self._force_update_dialog = None
        self._lock_retry_timer_active = False
        self._last_lock_warning = 0.0
        self._update_install_in_progress = False
        self._forced_update_download_url = ''
        self._last_update_progress_at = 0.0
        self._update_watchdog_timer = None
        self._last_action_at: dict[str, float] = {}
        self._queued_since: dict[str, float] = {}
        self._stalled_active_since: dict[str, float] = {}
        self._last_force_start_at: dict[str, float] = {}
        self._force_start_attempts: dict[str, int] = {}
        self._last_render_signature = None
        self._last_backend_bootstrap_attempt = 0.0
        self._backend_bootstrap_inflight = False
        self._backend_watchdog_retries = 0
        self._backend_watchdog_alerted = False
        self._last_aria2_restart_at = 0.0
        self._startup_heal_lock_active = False
        self._startup_self_heal_inflight = False
        self._startup_self_heal_attempt = 0
        self._startup_self_heal_ok = False

        self._apply_global_style()
        self._build_ui()
        self._build_menu()
        self._setup_tray()
        self._start_poller()
        self._start_bridge()
        self._start_queue_timer()
        self._start_status_timer()
        self._start_scheduler_timer()
        self._start_sleep_watcher()

        self.new_download_from_web.connect(self._on_web_download)
        self.background_ok.connect(self._on_background_ok)
        self.background_err.connect(self._on_background_err)
        QTimer.singleShot(250, self._ensure_backend_started)
        QTimer.singleShot(700, self._startup_self_heal_bootstrap)
        QTimer.singleShot(4500, self._auto_resume_downloads)
        QTimer.singleShot(1200, lambda: self._schedule_update_check(force=True))
        QTimer.singleShot(8000, self._schedule_update_check)
        
        # Start Discord Rich Presence
        self._discord_rpc = None
        try:
            self._discord_rpc = DiscordRPCManager()
        except Exception as e:
            logger.debug(f'Failed to initialize Discord RPC: {e}')

    # Ã¢â€â‚¬Ã¢â€â‚¬ Style Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _apply_global_style(self):
        cfg = load_config()
        is_light = bool(cfg.get('theme_is_light', False))
        global C, STATE_COLOR
        palette = LIGHT_C if is_light else DARK_C
        for k, v in palette.items():
            C[k] = v

        # Update state colors for table
        STATE_COLOR.update({
            'downloading': C['accent'],
            'active':      C['accent'],
            'waiting':     C['yellow'],
            'queued':      C['yellow'],
            'complete':    C['green'],
            'completed':   C['green'],
            'seeding':     C['green'],
            'paused':      C['muted'],
            'pausing':     C['muted'],
            'error':       C['red'],
            'removed':     C['muted'],
        })

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {C['bg']};
                color: {C['text']};
                font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
                font-size: 13px;
            }}
            QTableWidget {{
                background: {C['surface']};
                alternate-background-color: {C['card']};
                border: 1px solid {C['border']};
                gridline-color: {C['border']};
                color: {C['text']};
                selection-background-color: rgba(108,99,255,0.25);
                selection-color: {C['text']};
            }}
            QHeaderView::section {{
                background: {C['card']};
                color: {C['muted']};
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                padding: 8px 10px;
                border: none;
                border-right: 1px solid {C['border']};
                border-bottom: 1px solid {C['border']};
                letter-spacing: 0.05em;
            }}
            QScrollBar:vertical {{
                background: {C['surface']};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border']};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar:horizontal {{ height: 6px; background: {C['surface']}; border-radius: 3px; }}
            QScrollBar::handle:horizontal {{ background: {C['border']}; border-radius: 3px; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}
            QMenuBar {{
                background: {C['surface']};
                color: {C['text']};
                border-bottom: 1px solid {C['border']};
                padding: 2px 4px;
            }}
            QMenuBar::item:selected {{ background: rgba(108,99,255,0.2); border-radius: 4px; }}
            QMenu {{
                background: {C['card']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{ padding: 8px 20px; border-radius: 4px; }}
            QMenu::item:selected {{ background: rgba(108,99,255,0.2); }}
            QStatusBar {{ background: {C['surface']}; color: {C['muted']}; font-size: 11px; padding: 2px 8px; }}
            QToolTip {{
                background: {C['card']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)

    # Ã¢â€â‚¬Ã¢â€â‚¬ UI construction Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Ã¢â€â‚¬Ã¢â€â‚¬ Sidebar Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f'background:{C["surface"]}; border-right:1px solid {C["border"]};')
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        # Logo area
        logo = QLabel('Streamore')
        logo.setStyleSheet(f"""
            color: {C['accent']};
            font-size: 15px;
            font-weight: 800;
            padding: 20px 16px 12px;
            background: {C['surface']};
            border-bottom: 1px solid {C['border']};
        """)
        sb_lay.addWidget(logo)

        # Nav buttons
        sep = QLabel('DOWNLOADS')
        sep.setStyleSheet(f'color:{C["muted"]}; font-size:10px; font-weight:700; '
                          f'letter-spacing:0.1em; padding:16px 16px 4px;')
        sb_lay.addWidget(sep)

        self._sidebar_btns: dict[str, SidebarButton] = {}
        self._filter_counts: dict[str, int] = {f[0]: 0 for f in FILTERS}
        for fid, label, _ in FILTERS:
            btn = SidebarButton(label, active=(fid == 'all'))
            btn.clicked.connect(lambda _, f=fid: self._set_filter(f))
            self._sidebar_btns[fid] = btn
            sb_lay.addWidget(btn)

        sb_lay.addStretch()

        # Backend status pill
        self._backend_pill = QLabel('Offline')
        self._backend_pill.setStyleSheet(f'color:{C["red"]}; padding:12px 16px; font-size:11px;')
        sb_lay.addWidget(self._backend_pill)

        root.addWidget(sidebar)

        # Ã¢â€â‚¬Ã¢â€â‚¬ Right pane Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        right = QWidget()
        r_lay  = QVBoxLayout(right)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(52)
        toolbar.setStyleSheet(f'background:{C["surface"]}; border-bottom:1px solid {C["border"]};')
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(16, 0, 16, 0)
        tb_lay.setSpacing(8)

        def _tb_btn(label, color=C['accent'], tip=''):
            b = QPushButton(label)
            b.setToolTip(tip)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(108,99,255,0.15);
                    color: {color};
                    border: 1px solid rgba(108,99,255,0.3);
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background: rgba(108,99,255,0.28); }}
                QPushButton:pressed {{ background: rgba(108,99,255,0.4); }}
            """)
            return b

        self._btn_add   = _tb_btn('Add Magnet', tip='Add magnet link or torrent URL')
        self._btn_pause_all = _tb_btn('Pause All', C['yellow'], 'Pause all active downloads')
        self._btn_resume_all = _tb_btn('Resume All', C['green'], 'Resume all paused downloads')
        self._btn_force_start = _tb_btn('Force Start', C['accent2'], 'Force start first queued or stalled item')
        self._btn_reset_engine = _tb_btn('Reset Engine', C['yellow'], 'Reset aria2/backend download engine')
        self._btn_open_dir  = _tb_btn('Open Folder', C['muted'], 'Open downloads folder')

        self._btn_add.clicked.connect(self._add_magnet_dialog)
        self._btn_pause_all.clicked.connect(self._pause_all)
        self._btn_resume_all.clicked.connect(self._resume_all)
        self._btn_force_start.clicked.connect(self._force_start_next)
        self._btn_reset_engine.clicked.connect(self._reset_download_engine)
        self._btn_open_dir.clicked.connect(self._open_folder)

        self._btn_history = _tb_btn('History', C['muted'], 'View persistent download history')
        self._btn_history.clicked.connect(self._open_history)
        self._btn_dashboard = _tb_btn('Dashboard', C['accent'], 'View analytics dashboard')
        self._btn_dashboard.clicked.connect(self._open_dashboard)
        self._btn_settings = _tb_btn('Settings', C['muted'], 'Open app settings')
        self._btn_settings.clicked.connect(self._open_settings)

        tb_lay.addWidget(self._btn_add)
        tb_lay.addWidget(self._btn_pause_all)
        tb_lay.addWidget(self._btn_resume_all)
        tb_lay.addWidget(self._btn_force_start)
        tb_lay.addWidget(self._btn_reset_engine)
        tb_lay.addWidget(self._btn_open_dir)
        tb_lay.addWidget(self._btn_history)
        tb_lay.addWidget(self._btn_dashboard)
        tb_lay.addWidget(self._btn_settings)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText('Search downloads...')
        self._search_edit.setFixedHeight(30)
        self._search_edit.setMaximumWidth(260)
        self._search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {C['bg']};
                border: 1px solid {C['border']};
                border-radius: 8px;
                padding: 4px 10px;
                color: {C['text']};
            }}
        """)
        self._search_edit.textChanged.connect(self._on_search_changed)
        tb_lay.addWidget(self._search_edit)
        tb_lay.addStretch()

        # Speed labels
        self._lbl_dl = QLabel('DL 0 B/s')
        self._lbl_dl.setStyleSheet(f'color:{C["accent"]}; font-size:12px; font-weight:600;')
        self._lbl_ul = QLabel('UL 0 B/s')
        self._lbl_ul.setStyleSheet(f'color:{C["upload"]}; font-size:12px; font-weight:600;')
        tb_lay.addWidget(self._lbl_dl)
        tb_lay.addWidget(self._lbl_ul)

        r_lay.addWidget(toolbar)

        # Speed graph
        self.speed_graph = SpeedGraph()
        r_lay.addWidget(self.speed_graph)

        # Table
        self._setup_table()
        r_lay.addWidget(self._table, 1)

        # Empty state (overlaid when no downloads)
        self._empty = QLabel()
        self._empty_default_text = 'No downloads yet\n\nGo to streamore-five.vercel.app and click Download on a movie'
        self._empty.setText(self._empty_default_text)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet(f'color:{C["muted"]}; font-size:14px; line-height:1.8;')
        self._empty.setVisible(False)
        r_lay.addWidget(self._empty)

        root.addWidget(right, 1)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_left = QLabel('Ready')
        self._status_left.setStyleSheet(f'color:{C["muted"]};')
        self._status_right = QLabel('')
        self._status_right.setStyleSheet(f'color:{C["muted"]};')
        self._status.addWidget(self._status_left, 1)
        self._status.addPermanentWidget(self._status_right)

    def _setup_table(self):
        cols = ['#', 'Title', 'Status', 'Progress', 'DL Speed', 'UL Speed',
                'Seeds', 'ETA', 'Size', 'Actions']
        self._table = QTableWidget()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Make columns adjustable
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setStretchLastSection(False)
        
        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(1, 280)  # Initial width for Title
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 140)
        self._table.setColumnWidth(4, 90)
        self._table.setColumnWidth(5, 90)
        self._table.setColumnWidth(6, 60)
        self._table.setColumnWidth(7, 80)
        self._table.setColumnWidth(8, 90)
        self._table.setColumnWidth(9, 140)
        
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setMinimumSectionSize(50)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._ctx_menu)

    # Ã¢â€â‚¬Ã¢â€â‚¬ Menu Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _build_menu(self):
        mb = self.menuBar()

        file_m = mb.addMenu('File')
        self._act_add = QAction('Add Magnet Link...', self, shortcut='Ctrl+N')
        self._act_add.triggered.connect(self._add_magnet_dialog)
        file_m.addAction(self._act_add)
        file_m.addSeparator()
        self._act_quit = QAction('Quit', self, shortcut='Ctrl+Q')
        self._act_quit.triggered.connect(QApplication.instance().quit)
        file_m.addAction(self._act_quit)

        view_m = mb.addMenu('Downloads')
        self._act_folder = QAction('Open Downloads Folder', self)
        self._act_folder.triggered.connect(self._open_folder)
        view_m.addAction(self._act_folder)
        self._act_pause_all = QAction('Pause All', self)
        self._act_pause_all.triggered.connect(self._pause_all)
        view_m.addAction(self._act_pause_all)
        self._act_resume_all = QAction('Resume All', self)
        self._act_resume_all.triggered.connect(self._resume_all)
        view_m.addAction(self._act_resume_all)
        self._act_force_next = QAction('Force Start Next Stuck/Queued', self)
        self._act_force_next.triggered.connect(self._force_start_next)
        view_m.addAction(self._act_force_next)
        self._act_reset_engine = QAction('Reset Download Engine', self)
        self._act_reset_engine.triggered.connect(self._reset_download_engine)
        view_m.addAction(self._act_reset_engine)

        help_m = mb.addMenu('Help')
        self._act_about = QAction('About', self)
        self._act_about.triggered.connect(self._show_about)
        help_m.addAction(self._act_about)
        self._act_update = QAction('Check for Updates...', self)
        self._act_update.triggered.connect(self._on_check_updates_clicked)
        help_m.addAction(self._act_update)
        self._act_health = QAction('Health Details...', self)
        self._act_health.triggered.connect(self._show_health_details)
        help_m.addAction(self._act_health)
        self._act_export_diag = QAction('Export Diagnostics...', self)
        self._act_export_diag.triggered.connect(self._export_diagnostics)
        help_m.addAction(self._act_export_diag)
        self._act_repair_install = QAction('Repair Install...', self)
        self._act_repair_install.triggered.connect(self._repair_install)
        help_m.addAction(self._act_repair_install)

        self._actions_blocked_during_update = [
            self._act_add,
            self._act_folder,
            self._act_pause_all,
            self._act_resume_all,
            self._act_force_next,
            self._act_reset_engine,
        ]

    # Ã¢â€â‚¬Ã¢â€â‚¬ Updates Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _show_about(self):
        QMessageBox.information(
            self,
            'About Streamore',
            (
                'Streamore Download Manager\n'
                f'Version {APP_VERSION}\n\n'
                'Updates: automatic check every 6 hours.\n'
                'Use Help > Check for Updates to download the latest installer.'
            ),
        )

    def _show_health_details(self):
        snap = self._fetch_health_snapshot()
        lines = [
            f"Backend: {'Online' if snap.get('backend_online') else 'Offline'}",
            f"aria2: {snap.get('aria2_status', 'offline')}",
            f"Queue (waiting): {snap.get('waiting_count', 0)}",
            f"Stalled active: {snap.get('stalled_active', 0)}",
            f"Limits: DL {snap.get('limit_dl', 'unknown')} | UL {snap.get('limit_ul', 'unknown')}",
            f"Port: {BACKEND_URL}",
            '',
            f"Visible totals: all={len(self._downloads)} downloading={self._filter_counts.get('downloading', 0)} completed={self._filter_counts.get('completed', 0)}",
        ]
        err = str(snap.get('error') or '').strip()
        if err:
            lines.extend(['', f'Last error: {err}'])
        QMessageBox.information(self, 'Health Details', '\n'.join(lines))

    def _export_diagnostics(self):
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        default_name = f'streamore-diagnostics-{ts}.zip'
        default_dir = str(Path.home() / 'Desktop')
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            'Export Diagnostics',
            str(Path(default_dir) / default_name),
            'ZIP files (*.zip)',
        )
        if not out_path:
            return

        if hasattr(self, '_status_left'):
            self._status_left.setText('Exporting diagnostics...')

        def _do():
            out = Path(out_path)
            out.parent.mkdir(parents=True, exist_ok=True)

            snap = self._fetch_health_snapshot()
            cfg = load_config()
            sample_downloads = []
            for d in (self._downloads or [])[:200]:
                sample_downloads.append({
                    'id': str(d.get('id') or ''),
                    'title': str(d.get('movie_title') or d.get('name') or ''),
                    'state': str(d.get('state') or ''),
                    'progress': d.get('progress', 0),
                    'download_rate': d.get('download_rate', 0),
                    'upload_rate': d.get('upload_rate', 0),
                    'is_stalled': bool(d.get('is_stalled')),
                    'stall_reason': str(d.get('stall_reason') or ''),
                    'eta': d.get('eta'),
                })

            manifest = {
                'app_version': APP_VERSION,
                'generated_at_utc': datetime.now(timezone.utc).isoformat(),
                'backend_url': BACKEND_URL,
                'update_info_url': UPDATE_INFO_URL,
                'filters': {
                    'active_filter': self._active_filter,
                    'search': self._search_text,
                    'counts': dict(self._filter_counts),
                },
                'health': snap,
                'config': cfg,
                'downloads_sample': sample_downloads,
            }

            appdata_dir = Path(os.environ.get('APPDATA', '~')).expanduser() / 'StreamoreManager'
            candidate_files = [
                CONFIG_FILE,
                appdata_dir / 'logs' / 'aria2_backend.log',
                appdata_dir / 'logs' / 'backend_start.log',
                Path('aria2_backend.log'),
                Path('backend_start.log'),
            ]

            with zipfile.ZipFile(out, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False))
                for p in candidate_files:
                    try:
                        pp = Path(p)
                        if not pp.exists() or not pp.is_file():
                            continue
                        arc = f'files/{pp.name}'
                        zf.write(pp, arcname=arc)
                    except Exception:
                        continue

            return str(out)

        def _ok(path):
            if hasattr(self, '_status_left'):
                self._status_left.setText(f'Diagnostics exported: {path}')
            QMessageBox.information(self, 'Diagnostics', f'Diagnostics exported:\n{path}')

        def _err(msg):
            if hasattr(self, '_status_left'):
                self._status_left.setText('Diagnostics export failed.')
            QMessageBox.warning(self, 'Diagnostics', f'Failed to export diagnostics:\n{msg}')

        self._run_background(_do, on_ok=_ok, on_err=_err)

    def _repair_install(self):
        """
        Open latest installer URL to recover a broken/partial install.
        Falls back to static UPDATE_DOWNLOAD_URL if metadata lookup fails.
        """
        if hasattr(self, '_status_left'):
            self._status_left.setText('Preparing repair installer link...')

        def _do():
            try:
                info = self._fetch_update_info()
                url = str(info.get('download_url') or '').strip()
            except Exception:
                url = ''
            if not url:
                url = UPDATE_DOWNLOAD_URL
            return url

        def _ok(url):
            try:
                if not QDesktopServices.openUrl(QUrl(url)):
                    raise RuntimeError('Could not open URL')
                if hasattr(self, '_status_left'):
                    self._status_left.setText('Opened repair installer link.')
                QMessageBox.information(
                    self,
                    'Repair Install',
                    'Installer link opened.\n\nRun it to repair/update Streamore.',
                )
            except Exception as e:
                QMessageBox.warning(self, 'Repair Install', f'Failed to open installer link:\n{e}')

        def _err(msg):
            # If metadata fetch fails entirely, still try static fallback.
            try:
                if QDesktopServices.openUrl(QUrl(UPDATE_DOWNLOAD_URL)):
                    if hasattr(self, '_status_left'):
                        self._status_left.setText('Opened fallback repair installer link.')
                    QMessageBox.information(
                        self,
                        'Repair Install',
                        'Opened fallback installer link.\n\nRun it to repair/update Streamore.',
                    )
                    return
            except Exception:
                pass
            QMessageBox.warning(self, 'Repair Install', f'Failed to prepare repair installer link:\n{msg}')

        self._run_background(_do, on_ok=_ok, on_err=_err)

    def _warn_update_locked(self):
        now = time.time()
        if (now - self._last_lock_warning) < 2.0:
            return
        self._last_lock_warning = now
        QMessageBox.warning(
            self,
            'Update Required',
            'This version is blocked. Please complete the update to continue.'
        )

    def _set_update_lock(self, active: bool, reason: str = ''):
        self._update_lock_active = bool(active)
        set_update_locked(active)

        self._apply_action_enabled_state()
        if hasattr(self, '_status_left') and reason:
            self._status_left.setText(reason)

    def _set_startup_heal_lock(self, active: bool, reason: str = ''):
        self._startup_heal_lock_active = bool(active)
        self._apply_action_enabled_state()
        if hasattr(self, '_status_left') and reason:
            self._status_left.setText(reason)

    def _apply_action_enabled_state(self):
        enabled = (not self._update_lock_active) and (not self._startup_heal_lock_active)
        for wname in ('_btn_add', '_btn_pause_all', '_btn_resume_all', '_btn_force_start', '_btn_reset_engine', '_btn_open_dir', '_btn_settings', '_btn_dashboard', '_search_edit', '_table'):
            w = getattr(self, wname, None)
            if w is not None:
                w.setEnabled(enabled)

        for act in getattr(self, '_actions_blocked_during_update', []):
            if act is not None:
                act.setEnabled(enabled)

    def _ensure_forced_update_dialog(self):
        if self._force_update_dialog is None:
            dlg = ForcedUpdateDialog(self)
            dlg.retry_requested.connect(self._retry_forced_update)
            dlg.open_installer_requested.connect(self._open_forced_installer_link)
            self._force_update_dialog = dlg
        return self._force_update_dialog

    def _update_force_dialog(
        self,
        message: str,
        progress: int | None = None,
        can_retry: bool = False,
        can_open_link: bool = False,
    ):
        dlg = self._ensure_forced_update_dialog()
        dlg.set_message(message)
        dlg.set_progress(progress)
        dlg.allow_retry(can_retry)
        dlg.allow_open_installer(can_open_link and bool(self._forced_update_download_url))
        if not dlg.isVisible():
            dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_forced_installer_link(self):
        url = str(self._forced_update_download_url or '').strip()
        if not url:
            QMessageBox.warning(self, 'Update Required', 'Installer download link is not available yet.')
            return
        try:
            QDesktopServices.openUrl(QUrl(url))
            if hasattr(self, '_status_left'):
                self._status_left.setText('Opened installer link in browser.')
        except Exception as e:
            QMessageBox.warning(self, 'Update Required', f'Failed to open installer link:\n{e}')

    def _ensure_update_watchdog(self):
        if self._update_watchdog_timer is None:
            self._update_watchdog_timer = QTimer(self)
            self._update_watchdog_timer.setInterval(5000)
            self._update_watchdog_timer.timeout.connect(self._check_update_watchdog)

    def _start_update_watchdog(self):
        self._ensure_update_watchdog()
        self._last_update_progress_at = time.time()
        if self._update_watchdog_timer is not None and not self._update_watchdog_timer.isActive():
            self._update_watchdog_timer.start()

    def _stop_update_watchdog(self):
        if self._update_watchdog_timer is not None and self._update_watchdog_timer.isActive():
            self._update_watchdog_timer.stop()

    def _mark_update_progress(self):
        self._last_update_progress_at = time.time()

    def _check_update_watchdog(self):
        if not self._update_install_in_progress:
            self._stop_update_watchdog()
            return
        if not self._update_lock_active:
            return
        last = float(self._last_update_progress_at or 0.0)
        if not last:
            return
        if (time.time() - last) < FORCED_UPDATE_STALL_SECONDS:
            return
        self._update_force_dialog(
            (
                'Update download appears stuck (no progress detected).\n'
                'You can retry now or open the installer link directly.'
            ),
            progress=None,
            can_retry=True,
            can_open_link=True,
        )
        # Prevent spamming the same warning every timer tick.
        self._last_update_progress_at = time.time()

    def _retry_forced_update(self):
        self._lock_retry_timer_active = False
        self._schedule_update_check(force=True)

    def _schedule_forced_retry(self):
        if self._lock_retry_timer_active:
            return
        self._lock_retry_timer_active = True
        QTimer.singleShot(FORCED_UPDATE_RETRY_SECONDS * 1000, self._retry_forced_update)

    def _is_force_update_required(self, info: dict | None) -> bool:
        if not isinstance(info, dict):
            return False
        floor = str(info.get('minimum_required_version') or '').strip()
        if not floor:
            return False
        return self._is_newer_version(floor, APP_VERSION)
    def _on_check_updates_clicked(self):
        """Show a loading dialog immediately, then check in the background."""
        self._update_loading_dlg = UpdateStatusDialog(self, state='checking')
        self._update_loading_dlg.show()
        self._schedule_update_check(notify_if_latest=True, force=self._update_lock_active)

    def _schedule_update_check(self, notify_if_latest: bool = False, force: bool = False):
        if not HAS_REQUESTS:
            if force:
                self._set_update_lock(True, 'Update verification failed: dependency missing.')
                self._update_force_dialog(
                    'Could not verify the required update because the HTTP client is missing.',
                    progress=None,
                    can_retry=True,
                )
            elif notify_if_latest:
                QMessageBox.warning(self, 'Update Check Failed', 'Update dependency is missing.')
            return

        cfg = load_config()
        now = time.time()
        last = float(cfg.get('last_update_check', 0) or 0)
        if not force and not notify_if_latest and (now - last) < (UPDATE_CHECK_HOURS * 3600):
            return

        if force:
            self._set_update_lock(True, 'Verifying required update...')
            self._update_force_dialog('Checking required update from server...', progress=None, can_retry=False)
        elif notify_if_latest and hasattr(self, '_status_left'):
            self._status_left.setText('Checking for updates...')

        cfg['last_update_check'] = now
        save_config(cfg)

        self._update_worker = UpdateWorker(self, self._fetch_update_info, notify_if_latest)
        self._update_worker.result_ready.connect(self._on_update_result)
        self._update_worker.error_ready.connect(self._on_update_error)
        self._update_worker.start()

    def _close_loading_dlg(self):
        dlg = getattr(self, '_update_loading_dlg', None)
        if dlg and dlg.isVisible():
            dlg.close()
        self._update_loading_dlg = None

    def _close_force_update_dialog(self):
        dlg = getattr(self, '_force_update_dialog', None)
        if dlg is not None:
            dlg.hide()
            dlg.deleteLater()
        self._force_update_dialog = None

    def _on_update_result(self, info, notify_if_latest):
        self._close_loading_dlg()
        self._lock_retry_timer_active = False

        latest = str((info or {}).get('version') or '').strip()
        required_floor = str((info or {}).get('minimum_required_version') or '').strip()
        download_url = (info or {}).get('download_url') or UPDATE_DOWNLOAD_URL
        expected_sha = str((info or {}).get('sha256') or '').strip().lower()
        expected_app_sha = str((info or {}).get('app_sha256') or '').strip().lower()
        current_app_sha = self._local_app_binary_sha256()
        same_version_binary_changed = bool(
            latest
            and not self._is_newer_version(latest, APP_VERSION)
            and expected_app_sha
            and current_app_sha
            and expected_app_sha != current_app_sha
        )

        force_required = self._is_force_update_required(info)
        if force_required:
            floor = required_floor or latest or APP_VERSION
            target = latest or floor
            self._forced_update_download_url = str(download_url or '').strip()
            self._set_update_lock(True, f'Update required: version {floor}+ is required.')
            self._update_force_dialog(
                f'A mandatory update is required to continue. Installing version {target}...',
                progress=0,
                can_retry=False,
                can_open_link=True,
            )
            self._auto_update(target, download_url, expected_sha=expected_sha, mandatory=True)
            return

        if self._update_lock_active and not self._update_install_in_progress:
            self._set_update_lock(False, 'Ready')
            self._close_force_update_dialog()

        if latest and (self._is_newer_version(latest, APP_VERSION) or same_version_binary_changed):
            if notify_if_latest:
                dlg = UpdateStatusDialog(
                    self,
                    state='available',
                    current_version=APP_VERSION,
                    latest_version=latest,
                    download_url=download_url,
                )
                dlg.install_requested.connect(
                    lambda: self._auto_update(
                        latest,
                        download_url,
                        expected_sha=expected_sha,
                        mandatory=False,
                    )
                )
                dlg.exec()
            else:
                self._auto_update(
                    latest,
                    download_url,
                    expected_sha=expected_sha,
                    mandatory=False,
                )
            return

        if notify_if_latest:
            if latest:
                dlg = UpdateStatusDialog(
                    self,
                    state='latest',
                    current_version=APP_VERSION,
                    latest_version=latest,
                )
            else:
                dlg = UpdateStatusDialog(
                    self,
                    state='error',
                    error_msg='No update information found. Please try again later.',
                )
            dlg.exec()

    def _on_update_error(self, err_msg, notify_if_latest):
        self._close_loading_dlg()

        if self._update_lock_active:
            self._update_force_dialog(
                f'Could not verify required update.\n{err_msg}\n\nRetrying in {FORCED_UPDATE_RETRY_SECONDS}s...',
                progress=None,
                can_retry=True,
                can_open_link=True,
            )
            self._schedule_forced_retry()
            return

        if notify_if_latest:
            dlg = UpdateStatusDialog(
                self,
                state='error',
                error_msg=f'Could not check for updates.\n{err_msg}',
            )
            dlg.exec()

    def _fetch_update_info(self) -> dict:
        r = _requests.get(UPDATE_INFO_URL, timeout=10, headers={'User-Agent': 'StreamoreManager'})
        if getattr(r, 'status_code', 0) != 200:
            raise RuntimeError(f'HTTP {getattr(r, "status_code", "unknown")} from update server')

        data = r.json() if hasattr(r, 'json') else {}
        if not isinstance(data, dict):
            raise RuntimeError('Invalid update metadata format')

        latest = str(data.get('version') or '').strip()
        if not latest:
            raise RuntimeError('latest.json is missing version')

        floor = str(data.get('minimum_required_version') or latest).strip()
        if not floor:
            floor = latest

        return {
            'version': latest,
            'minimum_required_version': floor,
            'download_url': data.get('download_url') or UPDATE_DOWNLOAD_URL,
            'sha256': str(data.get('sha256') or '').strip().lower(),
            'app_sha256': str(data.get('app_sha256') or '').strip().lower(),
        }

    @staticmethod
    def _version_tuple(v: str) -> tuple:
        parts = [int(p) for p in re.findall(r'\d+', v)]
        return tuple(parts)

    def _is_newer_version(self, latest: str, current: str) -> bool:
        l = self._version_tuple(latest)
        c = self._version_tuple(current)
        if not l or not c:
            return False
        max_len = max(len(l), len(c))
        l = l + (0,) * (max_len - len(l))
        c = c + (0,) * (max_len - len(c))
        return l > c

    def _local_app_binary_sha256(self) -> str:
        # Only meaningful in packaged desktop builds.
        if not IS_BUNDLED:
            return ''
        try:
            app_path = Path(sys.executable)
            if not app_path.exists():
                return ''
            hasher = hashlib.sha256()
            with open(app_path, 'rb') as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest().lower()
        except Exception:
            return ''

    def _auto_update(self, latest: str, url: str, expected_sha: str = '', mandatory: bool = False):
        if self._update_install_in_progress:
            return

        self._update_install_in_progress = True
        self._forced_update_download_url = str(url or '').strip()
        self._mark_update_progress()
        if hasattr(self, '_status_left'):
            self._status_left.setText(f'Updating to {latest}...')

        if mandatory:
            self._set_update_lock(True, f'Update required: installing {latest}...')
            self._start_update_watchdog()
            self._update_force_dialog(
                f'Downloading mandatory update {latest}...',
                progress=None,
                can_retry=False,
                can_open_link=True,
            )

        threading.Thread(
            target=self._download_and_run_installer,
            args=(latest, url, expected_sha, mandatory),
            daemon=True,
        ).start()

    def _download_and_run_installer(self, latest: str, url: str, expected_sha: str = '', mandatory: bool = False):
        try:
            try:
                temp_root = Path(os.environ.get('TEMP', str(Path.home() / 'AppData' / 'Local' / 'Temp')))
            except Exception:
                temp_root = Path.cwd()
            temp_root.mkdir(parents=True, exist_ok=True)
            installer_path = temp_root / f'StreamoreSetup-{latest}.exe'

            req = Request(url, headers={'User-Agent': 'StreamoreManager'})
            total = 0
            hasher = hashlib.sha256()
            with urlopen(req, timeout=120) as resp, open(installer_path, 'wb') as f:
                try:
                    total = int(resp.headers.get('Content-Length', '0') or '0')
                except Exception:
                    total = 0

                downloaded = 0
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    self._mark_update_progress()
                    f.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int((downloaded * 100) / total)
                        if mandatory:
                            QTimer.singleShot(
                                0,
                                lambda p=pct: self._update_force_dialog(
                                    f'Downloading mandatory update {latest}...',
                                    progress=p,
                                    can_retry=False,
                                    can_open_link=True,
                                ),
                            )
                    else:
                        # Unknown content length (chunked transfer): keep UI in working state.
                        if mandatory:
                            mb = downloaded / (1024 * 1024)
                            QTimer.singleShot(
                                0,
                                lambda m=mb: self._update_force_dialog(
                                    f'Downloading mandatory update {latest}... ({m:.1f} MB)',
                                    progress=None,
                                    can_retry=False,
                                    can_open_link=True,
                                ),
                            )

            got_sha = hasher.hexdigest().lower()
            if expected_sha and got_sha != expected_sha.lower():
                raise RuntimeError('Installer integrity check failed (SHA256 mismatch).')

            if os.name == 'nt':
                args = [
                    str(installer_path),
                    '/VERYSILENT',
                    '/NORESTART',
                    '/CLOSEAPPLICATIONS',
                    '/FORCECLOSEAPPLICATIONS',
                    '/NOCANCEL',
                    '/SUPPRESSMSGBOXES',
                ]
                subprocess.Popen(args, cwd=str(installer_path.parent))
            else:
                subprocess.Popen([str(installer_path)], cwd=str(installer_path.parent))

            def _finish_success():
                self._stop_update_watchdog()
                if mandatory:
                    self._update_force_dialog(
                        'Installer started. Closing app to complete update...',
                        progress=100,
                        can_retry=False,
                        can_open_link=False,
                    )
                else:
                    QMessageBox.information(
                        self,
                        'Update Started',
                        'Installer started. The app will close to complete the update.',
                    )
                app = QApplication.instance()
                if app is not None:
                    QTimer.singleShot(1200, app.quit)

            QTimer.singleShot(0, _finish_success)
        except Exception as e:
            self._update_install_in_progress = False

            def _fail_ui():
                self._stop_update_watchdog()
                if mandatory or self._update_lock_active:
                    self._set_update_lock(True, 'Update required: retrying...')
                    self._update_force_dialog(
                        f'Update failed:\n{e}\n\nRetrying in {FORCED_UPDATE_RETRY_SECONDS}s...',
                        progress=None,
                        can_retry=True,
                        can_open_link=True,
                    )
                    self._schedule_forced_retry()
                else:
                    QMessageBox.warning(
                        self,
                        'Update Failed',
                        f'Could not download or launch the installer.\n{e}',
                    )

            QTimer.singleShot(0, _fail_ui)
        else:
            self._update_install_in_progress = False
            self._stop_update_watchdog()

    # -- Tray --
    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        # Create a simple purple icon
        px = QPixmap(32, 32)
        px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(C['accent'])))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.setBrush(QBrush(QColor('#fff')))
        # Arrow down
        p.drawRect(13, 4, 6, 14)
        pts = QPolygon([QPoint(6, 14), QPoint(26, 14), QPoint(16, 26)])
        p.drawPolygon(pts)
        p.fillRect(8, 26, 16, 4, QColor('#fff'))
        p.end()
        icon = QIcon(px)
        self._tray.setIcon(icon)
        self.setWindowIcon(icon)
        self._tray.setToolTip('Streamore Download Manager')

        tray_menu = QMenu()
        act_show = QAction('Open Download Manager', self)
        act_show.triggered.connect(self._show_window)
        act_quit = QAction('Quit', self)
        act_quit.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(act_show)
        tray_menu.addSeparator()
        tray_menu.addAction(act_quit)
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    @staticmethod
    def _resp_ok(resp) -> bool:
        return bool(getattr(resp, 'ok', False) or int(getattr(resp, 'status_code', 0)) < 400)

    @staticmethod
    def _resp_json(resp) -> dict:
        try:
            data = resp.json() if hasattr(resp, 'json') else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _startup_self_heal_bootstrap(self):
        if self._startup_self_heal_ok or self._startup_self_heal_inflight:
            return
        self._set_startup_heal_lock(True, 'Running startup checks...')
        self._run_startup_self_heal()

    def _run_startup_self_heal(self):
        if self._startup_self_heal_inflight:
            return
        self._startup_self_heal_inflight = True

        def _worker():
            success = False
            message = 'Startup checks failed.'
            attempt = 0
            for idx in range(1, STARTUP_SELF_HEAL_MAX_ATTEMPTS + 1):
                attempt = idx
                try:
                    ok, msg = self._startup_self_heal_once(idx)
                    if ok:
                        success = True
                        message = msg
                        break
                    message = msg
                except Exception as e:
                    message = str(e)
                time.sleep(STARTUP_SELF_HEAL_RETRY_SECONDS)
            return success, message, attempt

        def _ok(result):
            success, message, attempt = result
            self._startup_self_heal_inflight = False
            self._startup_self_heal_attempt = attempt
            self._finish_startup_self_heal(success, message)

        def _err(msg):
            self._startup_self_heal_inflight = False
            self._finish_startup_self_heal(False, msg)

        self._run_background(_worker, on_ok=_ok, on_err=_err)

    def _startup_self_heal_once(self, attempt: int) -> tuple[bool, str]:
        if hasattr(self, '_status_left'):
            self._status_left.setText(f'Startup self-heal attempt {attempt}/{STARTUP_SELF_HEAL_MAX_ATTEMPTS}...')

        if not is_backend_running():
            start_backend()
            time.sleep(2.5)

        health_resp = _requests.get(f'{BACKEND_URL}/api/health', timeout=4)
        if not self._resp_ok(health_resp):
            return False, f'Backend health failed (HTTP {getattr(health_resp, "status_code", "n/a")}).'

        aria_resp = _requests.get(f'{BACKEND_URL}/api/aria2/status', timeout=6)
        if not self._resp_ok(aria_resp):
            return False, f'aria2 status check failed (HTTP {getattr(aria_resp, "status_code", "n/a")}).'
        aria_data = self._resp_json(aria_resp)
        aria_status = str(aria_data.get('status') or 'offline').lower()

        if aria_status == 'offline':
            _requests.post(f'{BACKEND_URL}/api/engine/reset', timeout=25)
            time.sleep(3.0)
            aria_resp2 = _requests.get(f'{BACKEND_URL}/api/aria2/status', timeout=8)
            if not self._resp_ok(aria_resp2):
                return False, 'aria2 restart check failed after engine reset.'
            aria_data = self._resp_json(aria_resp2)
            aria_status = str(aria_data.get('status') or 'offline').lower()
            if aria_status == 'offline':
                return False, 'aria2 is still offline after engine reset.'

        # Warm settings endpoints so first UI actions do not freeze on cold backend state.
        try:
            _requests.get(f'{BACKEND_URL}/api/settings', timeout=4)
            _requests.get(f'{BACKEND_URL}/api/torrent-settings', timeout=4)
        except Exception:
            pass

        return True, f'Startup checks passed (backend online, aria2 {aria_status}).'

    def _finish_startup_self_heal(self, success: bool, message: str):
        if success:
            self._startup_self_heal_ok = True
            self._set_startup_heal_lock(False, 'Ready')
            self._update_status_panel(force=True)
            return

        # Keep actions locked when startup checks fail; retry in the background.
        self._set_startup_heal_lock(True, f'{message} Retrying...')
        QTimer.singleShot(STARTUP_SELF_HEAL_RETRY_SECONDS * 1000, self._run_startup_self_heal)

    def closeEvent(self, event):
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()
        self._tray.showMessage(
            'Streamore', 'Running in the background.',
            QSystemTrayIcon.MessageIcon.Information, 2000
        )

    # Ã¢â€â‚¬Ã¢â€â‚¬ Backend / Polling Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _start_poller(self):
        self._poller = DownloadPoller(POLL_INTERVAL)
        self._poller.updated.connect(self._on_downloads)
        self._poller.backend_state.connect(self._on_backend_state)
        self._poller.backend_error.connect(self._on_backend_error)
        self._poller.start()

    def _on_backend_state(self, online: bool):
        """Update UI status dot and labels based on backend connectivity."""
        self._backend_online = online
        self._apply_action_enabled_state()
        color = C['success'] if online else C['red']
        if hasattr(self, '_status_dot'):
            self._status_dot.setStyleSheet(f'background:{color}; border-radius:5px;')
        if hasattr(self, '_status_lbl'):
            self._status_lbl.setText('Engine: Online' if online else 'Engine: Offline')

    def _on_backend_error(self, message: str):
        """Show a tray notification for critical backend errors."""
        # Rate limit toasts so we don't spam the user
        now = time.time()
        if not hasattr(self, '_last_backend_toast_at'):
            self._last_backend_toast_at = 0
            
        if (now - self._last_backend_toast_at) > 60: # Max one toast per minute
            self._last_backend_toast_at = now
            self._tray.showMessage(
                "Streamore Engine Alert",
                message,
                QSystemTrayIcon.MessageIcon.Warning,
                5000
            )

    def _start_status_timer(self):
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(8000)
        self._status_timer.timeout.connect(self._update_status_panel)
        self._status_timer.start()

    def _start_sleep_watcher(self):
        """Start the background thread that detects system sleep/resume."""
        self._sleep_watcher = SleepResumeWatcher(self)
        self._sleep_watcher.resumed.connect(self._on_system_resume)
        self._sleep_watcher.start()

    def _on_system_resume(self):
        """Called when the machine wakes from sleep. Restart aria2 and force-resume downloads."""
        logger.info('System resumed from sleep — triggering backend/aria2 restart')
        TelemetryManager.track_event('system_resume', {})
        if hasattr(self, '_status_left'):
            self._status_left.setText('Resuming after sleep — restarting download engine...')
        # Force backend restart and auto-resume
        self._ensure_backend_started(force=True)
        QTimer.singleShot(4000, self._post_resume_restart)

    def _post_resume_restart(self):
        """After sleep wakeup, hit the engine reset endpoint then force-resume all paused."""
        def _do():
            try:
                if HAS_REQUESTS:
                    # Soft-reset engine
                    _requests.post(f'{BACKEND_URL}/api/engine/reset', timeout=20)
                    time.sleep(2)
                    # Force-resume anything that was downloading before sleep
                    r = _requests.get(f'{BACKEND_URL}/api/downloads', timeout=4)
                    if r.ok:
                        for d in (r.json().get('downloads') or []):
                            st = (d.get('state') or '').lower()
                            if st in ('paused', 'pausing', 'error', 'waiting', 'queued'):
                                try:
                                    _requests.post(
                                        f'{BACKEND_URL}/api/download/{d["id"]}/resume',
                                        timeout=3
                                    )
                                except Exception:
                                    pass
            except Exception as e:
                logger.warning(f'Post-resume restart failed: {e}')
            def _ui():
                if hasattr(self, '_status_left'):
                    self._status_left.setText('Download engine resumed after sleep.')
            QTimer.singleShot(0, _ui)
        threading.Thread(target=_do, daemon=True).start()

    def _start_scheduler_timer(self):
        self._schedule_timer = QTimer(self)
        self._schedule_timer.setInterval(60000)
        self._schedule_timer.timeout.connect(self._apply_bandwidth_schedule)
        self._schedule_timer.start()
        QTimer.singleShot(2000, self._apply_bandwidth_schedule)

    def _on_backend_state(self, online: bool):
        prev_online = self._backend_online
        self._backend_online = online
        if online:
            self._backend_pill.setText('Online')
            self._backend_pill.setStyleSheet(f'color:{C["green"]}; padding:12px 16px; font-size:11px;')
            # Reset watchdog counter on successful connection
            self._backend_watchdog_retries = 0
        else:
            self._backend_pill.setText('Offline')
            self._backend_pill.setStyleSheet(f'color:{C["red"]}; padding:12px 16px; font-size:11px;')

            retries = getattr(self, '_backend_watchdog_retries', 0)
            if retries < BACKEND_WATCHDOG_MAX_RETRIES:
                self._backend_watchdog_retries = retries + 1
                logger.info(f'Backend offline — watchdog restart attempt {retries + 1}/{BACKEND_WATCHDOG_MAX_RETRIES}')
                self._ensure_backend_started()

                if BACKEND_START_ERROR and hasattr(self, '_status_left'):
                    self._status_left.setText(f'Backend start error: {BACKEND_START_ERROR}')
                    if getattr(self, '_last_telemetry_error', None) != BACKEND_START_ERROR:
                        self._last_telemetry_error = BACKEND_START_ERROR
                        TelemetryManager.track_failure('backend_start', BACKEND_START_ERROR)
            elif not getattr(self, '_backend_watchdog_alerted', False):
                # Exhausted retries — alert the user once
                self._backend_watchdog_alerted = True
                TelemetryManager.track_failure('backend_watchdog_exhausted', 'max retries reached')
                logger.error('Backend watchdog: max retries exhausted, alerting user')
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, 'Download Backend Error',
                    'The download backend could not be started after multiple attempts.\n\n'
                    'Please click \'Reset Engine\' or restart the app.'
                ))

        self._update_status_panel(force=True)

    def _ensure_backend_started(self, force: bool = False):
        if self._backend_online and not force:
            return
        now = time.time()
        if not force and (now - self._last_backend_bootstrap_attempt) < 8.0:
            return
        if self._backend_bootstrap_inflight:
            return

        self._backend_bootstrap_inflight = True
        self._last_backend_bootstrap_attempt = now

        def _worker():
            try:
                if not is_backend_running():
                    start_backend()
                    time.sleep(2.5)
            finally:
                def _finish():
                    self._backend_bootstrap_inflight = False
                QTimer.singleShot(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _auto_resume_downloads(self):
        if not HAS_REQUESTS:
            return
        try:
            if not is_backend_running():
                start_backend()
                time.sleep(2)
            r = _requests.get(f'{BACKEND_URL}/api/downloads', timeout=4)
            if not r.ok:
                return
            items = r.json().get('downloads') or []
            for d in items:
                st = (d.get('state') or '').lower()
                if st in ('paused', 'pausing'):
                    try:
                        _requests.post(f'{BACKEND_URL}/api/download/{d.get("id")}/resume', timeout=3)
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f'Auto-resume skipped: {e}')

    def _apply_bandwidth_limits(self, dl_kib: int, ul_kib: int):
        if not HAS_REQUESTS:
            return False
        try:
            payload = {
                'max_download_speed': int(dl_kib),
                'max_upload_speed': int(ul_kib),
            }
            r = _requests.post(f'{BACKEND_URL}/api/torrent-settings', json=payload, timeout=6)
            return bool(r.ok)
        except Exception as e:
            logger.debug(f'Apply bandwidth limits failed: {e}')
            return False

    def _parse_hhmm(self, val: str, fallback: int) -> int:
        try:
            parts = val.strip().split(':')
            if len(parts) != 2:
                return fallback
            h = max(0, min(23, int(parts[0])))
            m = max(0, min(59, int(parts[1])))
            return h * 60 + m
        except Exception:
            return fallback

    def _apply_bandwidth_schedule(self):
        cfg = load_config()
        enabled = bool(cfg.get('bandwidth_schedule_enabled', False))
        base_dl = int(cfg.get('max_download_speed', 0) or 0)
        base_ul = int(cfg.get('max_upload_speed', 0) or 0)

        if not enabled:
            if self._schedule_state is not None:
                self._schedule_state = None
                self._schedule_limits = {'dl': None, 'ul': None}
                self._apply_bandwidth_limits(base_dl, base_ul)
            return

        start_min = self._parse_hhmm(str(cfg.get('bandwidth_day_start', '08:00')), 8 * 60)
        end_min = self._parse_hhmm(str(cfg.get('bandwidth_day_end', '23:00')), 23 * 60)
        now = time.localtime()
        now_min = now.tm_hour * 60 + now.tm_min

        if start_min <= end_min:
            is_day = start_min <= now_min < end_min
        else:
            # Overnight window (e.g., 22:00 - 06:00)
            is_day = not (end_min <= now_min < start_min)

        if is_day:
            dl_kib = int(cfg.get('bandwidth_day_dl', base_dl) or 0)
            ul_kib = int(cfg.get('bandwidth_day_ul', base_ul) or 0)
            state = 'day'
        else:
            dl_kib = int(cfg.get('bandwidth_night_dl', base_dl) or 0)
            ul_kib = int(cfg.get('bandwidth_night_ul', base_ul) or 0)
            state = 'night'

        if self._schedule_state != state or self._schedule_limits.get('dl') != dl_kib or self._schedule_limits.get('ul') != ul_kib:
            if self._apply_bandwidth_limits(dl_kib, ul_kib):
                self._schedule_state = state
                self._schedule_limits = {'dl': dl_kib, 'ul': ul_kib}
                self._update_status_panel(force=True)

    def _update_status_panel(self, force: bool = False):
        if not hasattr(self, '_status_right'):
            return
        now = time.time()
        if not force and (now - self._last_status_fetch) < 6:
            return
        self._last_status_fetch = now

        snap = self._fetch_health_snapshot()
        aria2_status = snap.get('aria2_status', 'offline')
        limit_dl = snap.get('limit_dl')
        limit_ul = snap.get('limit_ul')
        stalled_active = int(snap.get('stalled_active', 0) or 0)
        waiting_count = int(snap.get('waiting_count', 0) or 0)

        # ── aria2 auto-restart ────────────────────────────────────────────────
        if aria2_status == 'offline' and self._backend_online and HAS_REQUESTS:
            now_restart = time.time()
            last_aria2_restart = getattr(self, '_last_aria2_restart_at', 0.0)
            if (now_restart - last_aria2_restart) > 60:  # at most once per 60s
                self._last_aria2_restart_at = now_restart
                logger.info('aria2 reported offline — triggering engine reset')
                def _restart_aria2():
                    try:
                        _requests.post(f'{BACKEND_URL}/api/engine/reset', timeout=20)
                    except Exception as e:
                        logger.warning(f'aria2 auto-restart failed: {e}')
                threading.Thread(target=_restart_aria2, daemon=True).start()

        sched = ''
        cfg = load_config()
        if cfg.get('bandwidth_schedule_enabled'):
            sched = f"Scheduler: {self._schedule_state or 'auto'}"
        if limit_dl is not None or limit_ul is not None:
            lim = f'Limits DL {limit_dl} UL {limit_ul}'
        else:
            lim = 'Limits unknown'
        backend = 'Online' if self._backend_online else 'Offline'
        text = f'Backend {backend} | aria2 {aria2_status} | {lim} | Queue {waiting_count} | Stalled {stalled_active}'
        if sched:
            text = f'{text} | {sched}'
        self._status_right.setText(text)

        # Safety release: never keep startup lock if core services are healthy.
        if self._startup_heal_lock_active and self._backend_online and aria2_status == 'running':
            self._startup_self_heal_ok = True
            self._set_startup_heal_lock(False, 'Ready')

    def _fetch_health_snapshot(self) -> dict:
        out = {
            'backend_online': bool(self._backend_online),
            'aria2_status': 'offline',
            'limit_dl': None,
            'limit_ul': None,
            'stalled_active': 0,
            'waiting_count': 0,
            'error': '',
        }
        if not HAS_REQUESTS or not self._backend_online:
            return out
        try:
            r = _requests.get(f'{BACKEND_URL}/api/aria2/status', timeout=4)
            if r.ok:
                data = r.json()
                out['aria2_status'] = data.get('status', out['aria2_status'])
                out['stalled_active'] = int(data.get('stalled_active_downloads', 0) or 0)
                out['waiting_count'] = int(data.get('waiting_downloads', 0) or 0)
            t = _requests.get(f'{BACKEND_URL}/api/torrent-settings', timeout=4)
            if t.ok:
                tdata = t.json().get('settings') or {}
                out['limit_dl'] = tdata.get('max_download_speed')
                out['limit_ul'] = tdata.get('max_upload_speed')
        except Exception as e:
            out['error'] = str(e)
        return out

    @staticmethod
    def _downloads_signature(downloads: list[dict]) -> tuple:
        sig = []
        for d in downloads or []:
            try:
                sig.append((
                    str(d.get('id') or ''),
                    str(d.get('state') or '').lower(),
                    int(float(d.get('progress', 0)) * 10),
                    int(float(d.get('download_rate', 0)) // 1024),
                    int(float(d.get('upload_rate', 0)) // 1024),
                    int(d.get('num_seeds', 0) or 0),
                    int(d.get('num_peers', 0) or 0),
                    int(d.get('eta', 0) or 0),
                    1 if bool(d.get('is_stalled')) else 0,
                    str(d.get('stall_reason') or ''),
                ))
            except Exception:
                continue
        return tuple(sig)

    def _on_downloads(self, downloads: list):
        self._downloads = downloads or []
        self._recover_stuck_queued()
        
        new_states = {}
        for d in self._downloads:
            did = str(d.get('id', ''))
            state = (d.get('state', '') or '').lower()

            # Clean up stale speeds for non-active downloads
            if state not in ('downloading', 'active'):
                d['download_rate'] = 0
                if state not in ('seeding', 'complete', 'completed'):
                    d['upload_rate'] = 0

            if not did:
                continue
            new_states[did] = state
            old_state = self._last_download_states.get(did)
            if old_state is not None and old_state != state:
                if state in ('complete', 'completed') and old_state not in ('complete', 'completed', 'seeding'):
                    TelemetryManager.track_event('download_completed', {'has_movie_title': bool(d.get('movie_title'))})
                    # Show completion notification
                    title = d.get('movie_title') or d.get('name') or 'Download'
                    self._tray.showMessage(
                        'Download Complete',
                        f'"{title}" has finished downloading.',
                        QSystemTrayIcon.MessageIcon.Information, 5000
                    )
                elif state == 'error' and old_state != 'error':
                    TelemetryManager.track_failure('download_error', str(d.get('errorMessage') or d.get('error_message') or ''))
        self._last_download_states = new_states

        signature = self._downloads_signature(self._downloads)
        if signature != self._last_render_signature:
            self._refresh_table()
            self._last_render_signature = signature

        # Update Discord Rich Presence
        if self._discord_rpc:
            self._discord_rpc.update(self._downloads)

        total_dl = sum(d.get('download_rate', 0) for d in self._downloads)
        total_ul = sum(d.get('upload_rate', 0) for d in self._downloads)
        self._total_dl = total_dl
        self._total_ul = total_ul
        self._lbl_dl.setText(f'DL {fmt_speed(total_dl)}')
        self._lbl_ul.setText(f'UL {fmt_speed(total_ul)}')
        self.speed_graph.push(total_dl, total_ul)

        # Update sidebar counts
        all_states = [(d.get('state', '') or '').lower() for d in self._downloads]
        for fid, _, states in FILTERS:
            if fid == 'all':
                self._sidebar_btns[fid].set_active(self._active_filter == fid)
                self._filter_counts[fid] = len(self._downloads)
            else:
                count = sum(1 for s in all_states if s in (states or []))
                self._filter_counts[fid] = count

        for fid, label, _ in FILTERS:
            c = self._filter_counts[fid]
            suffix = f'  ({c})' if c else ''
            self._sidebar_btns[fid].setText(label + suffix)

        # Status bar and dynamic title
        active_items = [d for d in self._downloads if (d.get('state', '') or '').lower() in ('downloading', 'active')]
        active_count = len(active_items)
        queued_count = sum(1 for d in self._downloads if (d.get('state', '') or '').lower() in ('waiting', 'queued'))
        stalled_count = sum(1 for d in self._downloads if bool(d.get('is_stalled')))
        if active_count > 0:
            primary = active_items[0]
            p_name = primary.get('movie_title') or primary.get('name') or 'Download'
            self.setWindowTitle(f"Streamore - {p_name} ({active_count} active)")
        else:
            self.setWindowTitle("Streamore Download Manager")

        if hasattr(self, '_status_left'):
            self._status_left.setText(
                f'{len(self._downloads)} downloads | {active_count} active | '
                f'Q {queued_count} | Stalled {stalled_count} | '
                f'DL {fmt_speed(total_dl)}  UL {fmt_speed(total_ul)}'
            )
        self._update_status_panel()

    def _refresh_table(self):
        # Filter
        visible = []
        for d in self._downloads:
            st = (d.get('state', '') or '').lower()
            if self._active_filter == 'all':
                visible.append(d)
            else:
                _, _, states = next(f for f in FILTERS if f[0] == self._active_filter)
                if st in (states or []):
                    visible.append(d)

        query = (self._search_text or '').strip().lower()
        if query:
            visible = [d for d in visible if self._matches_search(d, query)]

        show_empty = len(visible) == 0
        if show_empty:
            if query:
                self._empty.setText(f'No downloads match "{query}"\n\nClear search to see items')
            elif self._active_filter != 'all' and self._filter_counts.get(self._active_filter, 0) > 0:
                self._empty.setText('No downloads visible in this view\n\nTry "All" or clear search')
            else:
                self._empty.setText(self._empty_default_text)
        self._table.setVisible(not show_empty)
        self._empty.setVisible(show_empty)

        self._table.setRowCount(len(visible))
        self._table.setUpdatesEnabled(False)
        try:
            def _to_int(value, default=0):
                try:
                    if value is None:
                        return default
                    if isinstance(value, bool):
                        return int(value)
                    if isinstance(value, (int, float)):
                        return int(value)
                    text = str(value).strip()
                    if text == '':
                        return default
                    return int(float(text))
                except Exception:
                    return default

            def _to_float(value, default=0.0):
                try:
                    if value is None:
                        return default
                    if isinstance(value, bool):
                        return float(int(value))
                    if isinstance(value, (int, float)):
                        return float(value)
                    text = str(value).strip()
                    if text == '':
                        return default
                    return float(text)
                except Exception:
                    return default

            for row, d in enumerate(visible):
                state = (d.get('state') or 'unknown').lower()
                sc = STATE_COLOR.get(state, C['muted'])
                title = d.get('movie_title') or d.get('name') or 'Unknown'
                qual  = d.get('quality', '')

                def _item(text, align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft):
                    it = QTableWidgetItem(str(text))
                    it.setTextAlignment(align)
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    it.setData(Qt.ItemDataRole.UserRole, d.get('id'))
                    return it

                # Row #
                self._table.setItem(
                    row,
                    0,
                    _item(
                        str(row + 1),
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                    ),
                )

                # Title cell with two lines
                movie_title = d.get('movie_title') or 'Unknown'
                file_name = d.get('name') or ''

                title_widget = QWidget()
                title_lay = QVBoxLayout(title_widget)
                title_lay.setContentsMargins(8, 4, 8, 4)
                title_lay.setSpacing(0)

                m_lbl = QLabel(f"{movie_title}  {qual}")
                m_lbl.setStyleSheet(f"font-weight: 600; color: {C['text']}; font-size: 13px;")
                title_lay.addWidget(m_lbl)

                if file_name and file_name != movie_title and file_name != "Unknown":
                    f_lbl = QLabel(file_name)
                    f_lbl.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")
                    title_lay.addWidget(f_lbl)

                err_msg = str(d.get('error_message') or d.get('errorMessage') or '').strip()
                stall_reason = str(d.get('stall_reason') or '').strip()
                
                if state == 'error' and err_msg:
                    warn_lbl = QLabel(f"⚠️ Error: {err_msg} (Action: Force Start / Reset Engine)")
                    warn_lbl.setStyleSheet(f"color: {C['red']}; font-size: 11px; font-weight: bold;")
                    warn_lbl.setWordWrap(True)
                    title_lay.addWidget(warn_lbl)
                elif d.get('is_stalled') and stall_reason:
                    warn_lbl = QLabel(f"⚠️ Stalled: {stall_reason} (Action: Pause & Resume / Force Start)")
                    warn_lbl.setStyleSheet(f"color: {C['yellow']}; font-size: 11px; font-weight: bold;")
                    warn_lbl.setWordWrap(True)
                    title_lay.addWidget(warn_lbl)

                title_widget.setToolTip(f"Path: {d.get('save_path', 'N/A')}")
                self._table.setCellWidget(row, 1, title_widget)
                # Status badge
                st_item = _item(STATE_LABEL.get(state, state))
                st_item.setForeground(QColor(sc))
                stall_reason = str(d.get('stall_reason') or '').strip()
                if stall_reason:
                    st_item.setToolTip(stall_reason)
                self._table.setItem(row, 2, st_item)
                # Progress bar
                prog = _to_float(d.get('progress', 0))
                prog = max(0.0, min(prog, 100.0))
                pb = QProgressBar()
                pb.setRange(0, 100)
                pb.setValue(int(prog))
                pb.setTextVisible(True)
                pb.setFormat(f'{prog:.1f}%')
                pb.setStyleSheet(f"""
                QProgressBar {{
                    background: {C['card']};
                    border: 1px solid {C['border']};
                    border-radius: 6px;
                    color: {C['text']};
                    text-align: center;
                    height: 18px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                                stop:0 {sc}, stop:1 {sc}88);
                    border-radius: 5px;
                }}
            """)
                self._table.setCellWidget(row, 3, pb)
                # Speeds
                self._table.setItem(row, 4, _item(fmt_speed(_to_int(d.get('download_rate', 0)))))
                self._table.setItem(row, 5, _item(fmt_speed(_to_int(d.get('upload_rate', 0)))))
                # Seeds
                self._table.setItem(
                    row,
                    6,
                    _item(
                        str(_to_int(d.get('num_seeds', 0))),
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                    ),
                )
                # ETA
                eta = d.get('eta')
                eta_txt = '-'
                try:
                    eta_int = _to_int(eta, -1)
                    if eta_int >= 0 and state in ('downloading', 'active', 'waiting', 'queued'):
                        eta_txt = fmt_eta(eta_int)
                except Exception:
                    eta_txt = '-'
                self._table.setItem(row, 7, _item(
                    eta_txt,
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter))
                # Size
                self._table.setItem(row, 8, _item(fmt_bytes(_to_int(d.get('size_total', 0)))))
                # Actions
                acts = QWidget()
                acts_lay = QHBoxLayout(acts)
                acts_lay.setContentsMargins(6, 4, 6, 4)
                acts_lay.setSpacing(4)

                def _act_btn(icon_name, color, tip, slot):
                    b = QPushButton()
                    b.setToolTip(tip)
                    b.setFixedSize(32, 28)
                    icon_map = {
                    'resume': QStyle.StandardPixmap.SP_MediaPlay,
                    'pause': QStyle.StandardPixmap.SP_MediaPause,
                    'play': QStyle.StandardPixmap.SP_MediaPlay,
                    'force': QStyle.StandardPixmap.SP_MediaSkipForward,
                    'folder': QStyle.StandardPixmap.SP_DirOpenIcon,
                    'remove': QStyle.StandardPixmap.SP_TrashIcon,
                }
                    sp = icon_map.get(icon_name)
                    if sp is not None:
                        base_icon = self.style().standardIcon(sp)
                        pix = base_icon.pixmap(16, 16)
                        tinted = QPixmap(pix.size())
                        tinted.fill(Qt.GlobalColor.transparent)
                        painter = QPainter(tinted)
                        painter.drawPixmap(0, 0, pix)
                        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                        painter.fillRect(tinted.rect(), QColor(color))
                        painter.end()
                        b.setIcon(QIcon(tinted))
                        b.setIconSize(QSize(14, 14))
                    b.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(255,255,255,0.04);
                        color: {color};
                        border: 1px solid {color}44;
                        border-radius: 6px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{ background: {color}22; border-color: {color}88; }}
                    QPushButton:pressed {{ background: {color}44; }}
                """)
                    b.clicked.connect(slot)
                    return b

                did = d.get('id', '')
                if state in ('paused', 'pausing', 'error'):
                    acts_lay.addWidget(_act_btn('resume', C['green'], 'Resume',
                        lambda _, i=did: self._api_action(i, 'resume')))
                elif state in ('downloading', 'active', 'waiting', 'queued'):
                    acts_lay.addWidget(_act_btn('pause', C['yellow'], 'Pause',
                        lambda _, i=did: self._api_action(i, 'pause')))
                if state not in ('complete', 'completed', 'seeding', 'removed'):
                    acts_lay.addWidget(_act_btn('force', C['accent'], 'Force start',
                        lambda _, i=did: self._api_force_start(i)))
                if state in ('complete', 'completed', 'seeding'):
                    acts_lay.addWidget(_act_btn('play', C['accent'], 'Play / Open',
                        lambda _, i=did: self._api_action(i, 'play')))
                acts_lay.addWidget(_act_btn('folder', C['accent'], 'Open folder',
                    lambda _, i=did: self._api_action(i, 'open-folder')))
                acts_lay.addWidget(_act_btn('remove', C['red'], 'Remove',
                    lambda _, i=did, t=title: self._confirm_remove(i, t)))

                self._table.setCellWidget(row, 9, acts)
        finally:
            self._table.setUpdatesEnabled(True)

    # Ã¢â€â‚¬Ã¢â€â‚¬ Sidebar filter Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _set_filter(self, fid: str):
        self._active_filter = fid
        for f, btn in self._sidebar_btns.items():
            btn.set_active(f == fid)
        self._refresh_table()

    def _on_search_changed(self, text: str):
        self._search_text = text or ''
        self._refresh_table()

    @staticmethod
    def _matches_search(download: dict, query: str) -> bool:
        if not query:
            return True
        fields = [
            str(download.get('movie_title') or ''),
            str(download.get('name') or ''),
            str(download.get('quality') or ''),
            str(download.get('id') or ''),
        ]
        hay = ' '.join(fields).lower()
        return query in hay

    def _action_key(self, download_id: str, action: str) -> str:
        return f'{action}:{download_id}'

    def _is_action_debounced(self, download_id: str, action: str, *, window_s: float = ACTION_DEBOUNCE_SECONDS) -> bool:
        now = time.time()
        key = self._action_key(download_id, action)
        last = self._last_action_at.get(key, 0.0)
        if (now - last) < window_s:
            return True
        self._last_action_at[key] = now
        return False

    def _run_background(self, fn, on_ok=None, on_err=None):
        def _worker():
            try:
                result = fn()
                if on_ok is not None:
                    self.background_ok.emit(on_ok, result)
            except Exception as e:
                if on_err is not None:
                    self.background_err.emit(on_err, str(e))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_background_ok(self, callback, result):
        try:
            if callable(callback):
                callback(result)
        except Exception:
            logger.exception('Background success callback failed')

    def _on_background_err(self, callback, message: str):
        try:
            if callable(callback):
                callback(message)
        except Exception:
            logger.exception('Background error callback failed')

    def _recover_stuck_queued(self):
        now = time.time()
        active_ids: set[str] = set()
        for d in self._downloads:
            did = str(d.get('id') or '')
            if not did:
                continue
            active_ids.add(did)
            state = (d.get('state') or '').lower()

            # Seed guard: never force-start a torrent with 0 seeds — it won't help.
            num_seeds = int(d.get('num_seeds') or 0)
            if state in ('waiting', 'queued', 'downloading', 'active') and num_seeds == 0:
                # Clear stale tracking so it re-evaluates next time seeds appear
                self._queued_since.pop(did, None)
                self._stalled_active_since.pop(did, None)
                continue

            if state in ('waiting', 'queued') or (state in ('downloading', 'active') and bool(d.get('is_stalled'))):
                if state in ('waiting', 'queued'):
                    first_seen = self._queued_since.setdefault(did, now)
                else:
                    first_seen = self._stalled_active_since.setdefault(did, now)

                # Exponential backoff for auto-recovery: base_delay * (1.5 ^ attempts)
                attempts = self._force_start_attempts.get(did, 0)
                # Base is FORCE_START_COOLDOWN_SECONDS (20s). Cap at 300s (5m).
                cooldown = min(300, FORCE_START_COOLDOWN_SECONDS * (1.5 ** attempts))
                
                if (now - first_seen) < QUEUED_FORCE_START_DELAY_SECONDS:
                    continue
                if (now - self._last_force_start_at.get(did, 0.0)) < cooldown:
                    continue

                self._last_force_start_at[did] = now
                self._force_start_attempts[did] = attempts + 1
                logger.info(f'Auto-recovery force-start for {did}: attempt {attempts + 1}, cooldown {cooldown:.1f}s')
                self._api_force_start(did, source='auto')
            else:
                self._queued_since.pop(did, None)
                self._stalled_active_since.pop(did, None)
                self._force_start_attempts.pop(did, None)

        for did in list(self._queued_since.keys()):
            if did not in active_ids:
                self._queued_since.pop(did, None)
                self._last_force_start_at.pop(did, None)
        for did in list(self._stalled_active_since.keys()):
            if did not in active_ids:
                self._stalled_active_since.pop(did, None)

    # Ã¢â€â‚¬Ã¢â€â‚¬ API actions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _api_action(self, download_id: str, action: str):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        if self._is_action_debounced(str(download_id), action):
            return
        if not HAS_REQUESTS:
            return
        def _do():
            try:
                url = f'{BACKEND_URL}/api/download/{download_id}/{action}'
                body = {'delete_files': False} if action == 'cancel' else {}
                _requests.post(url, json=body, timeout=5)
            except Exception as e:
                logger.warning(f'API action {action} failed: {e}')
        threading.Thread(target=_do, daemon=True).start()

    def _api_move(self, download_id: str, direction: str):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        if self._is_action_debounced(str(download_id), f'move-{direction}'):
            return
        if not HAS_REQUESTS:
            return
        def _do():
            try:
                _requests.post(
                    f'{BACKEND_URL}/api/download/{download_id}/move',
                    json={'direction': direction},
                    timeout=5,
                )
            except Exception as e:
                logger.warning(f'API move {direction} failed: {e}')
        threading.Thread(target=_do, daemon=True).start()

    def _api_priority(self, download_id: str, level: str):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        if self._is_action_debounced(str(download_id), f'priority-{level}'):
            return
        if not HAS_REQUESTS:
            return
        def _do():
            try:
                _requests.post(
                    f'{BACKEND_URL}/api/download/{download_id}/priority',
                    json={'level': level},
                    timeout=5,
                )
            except Exception as e:
                logger.warning(f'API priority {level} failed: {e}')
        threading.Thread(target=_do, daemon=True).start()

    def _api_force_start(self, download_id: str, source: str = 'manual'):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        action_window = FORCE_START_COOLDOWN_SECONDS if source == 'auto' else ACTION_DEBOUNCE_SECONDS
        if self._is_action_debounced(str(download_id), 'force-start', window_s=action_window):
            return
        if not HAS_REQUESTS:
            return
        def _do():
            try:
                _requests.post(
                    f'{BACKEND_URL}/api/download/{download_id}/force-start',
                    timeout=6,
                )
                logger.info(f'Force-start requested ({source}) for download {download_id}')
            except Exception as e:
                logger.warning(f'API force-start failed: {e}')
        threading.Thread(target=_do, daemon=True).start()

    def _confirm_remove(self, download_id: str, title: str):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        dlg = QDialog(self)
        dlg.setWindowTitle('Remove Download')
        dlg.setFixedSize(400, 180)
        dlg.setStyleSheet(f'background:{C["card"]}; color:{C["text"]};')
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lbl = QLabel(f'Remove <b>{title}</b> from the download list?')
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        cb = QCheckBox('Also delete files from disk')
        cb.setStyleSheet(f'color:{C["muted"]}; font-size:12px;')
        lay.addWidget(cb)

        btns = QHBoxLayout()
        btns.addStretch()
        def _btn(label, color):
            b = QPushButton(label)
            b.setStyleSheet(f"""
                QPushButton {{
                    background:{color}; color:#fff; border:none;
                    border-radius:8px; padding:8px 18px; font-weight:600;
                }}
                QPushButton:hover {{ opacity:0.85; }}
            """)
            return b

        cancel_b = _btn('Cancel', C['border'])
        rem_b    = _btn('Remove', C['red'])
        cancel_b.clicked.connect(dlg.reject)
        rem_b.clicked.connect(dlg.accept)
        btns.addWidget(cancel_b)
        btns.addWidget(rem_b)
        lay.addLayout(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            delete_files = cb.isChecked()
            if not HAS_REQUESTS:
                return
            if self._is_action_debounced(str(download_id), 'cancel'):
                return

            def _do_remove():
                _requests.post(
                    f'{BACKEND_URL}/api/download/{download_id}/cancel',
                    json={'delete_files': delete_files},
                    timeout=5,
                )

            def _on_remove_error(msg: str):
                logger.warning(f'Remove failed: {msg}')
                QMessageBox.warning(self, 'Error', f'Failed to remove download:\n{msg}')

            self._run_background(_do_remove, on_err=_on_remove_error)

    # Ã¢â€â‚¬Ã¢â€â‚¬ Toolbar actions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _add_magnet_dialog(self):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        dlg = QDialog(self)
        dlg.setWindowTitle('Add Download')
        dlg.setFixedWidth(450)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)

        lbl = QLabel('Paste magnet link, torrent URL, or select a .torrent file:')
        lbl.setStyleSheet(f'color:{C["text"]}; font-weight:600;')
        lay.addWidget(lbl)

        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setPlaceholderText('magnet:?xt=... or https://... or C:\\path\\to\\file.torrent')
        edit.setStyleSheet(f"background:{C['bg']}; border:1px solid {C['border']}; border-radius:6px; padding:8px; color:{C['text']};")
        row.addWidget(edit)

        browse_btn = QPushButton('...')
        browse_btn.setFixedSize(36, 36)
        browse_btn.setToolTip('Browse for .torrent file')
        browse_btn.setStyleSheet(f"background:{C['surface']}; color:{C['accent']}; border:1px solid {C['border']}; border-radius:6px; font-size:16px;")
        
        def _browse_torrent():
            path, _ = QFileDialog.getOpenFileName(dlg, 'Select Torrent File', '', 'Torrent Files (*.torrent);;All Files (*)')
            if path:
                edit.setText(path)
        
        browse_btn.clicked.connect(_browse_torrent)
        row.addWidget(browse_btn)
        lay.addLayout(row)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton('Cancel')
        add = QPushButton('Add Download')
        
        for b in (cancel, add):
            is_add = b == add
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {C['accent'] if is_add else 'transparent'};
                    color: {C['text'] if is_add else C['muted']};
                    border: {'none' if is_add else '1px solid ' + C['border']};
                    border-radius: 8px; padding: 10px 20px; font-weight: 700;
                }}
                QPushButton:hover {{ opacity: 0.9; background: {C['accent'] if is_add else C['surface']}; }}
            """)
        
        cancel.clicked.connect(dlg.reject)
        add.clicked.connect(dlg.accept)
        btns.addWidget(cancel)
        btns.addWidget(add)
        lay.addLayout(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            val = edit.text().strip()
            if val:
                # If it's a local file path, try to use the filename as an initial title
                title = 'Manual Download'
                if os.path.exists(val) or val.startswith('/') or (len(val) > 2 and val[1:3] == ':\\'):
                    title = os.path.basename(val)
                
                self._queue_download({
                    'magnet': val, 
                    'title': title, 
                    'quality': '', 
                    'movie_id': ''
                })

    def _pause_all(self):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        if not HAS_REQUESTS:
            return
        def _do():
            for d in self._downloads:
                if (d.get('state','') or '').lower() in ('downloading','active','queued','waiting'):
                    try:
                        _requests.post(
                            f'{BACKEND_URL}/api/download/{d["id"]}/pause', timeout=3)
                    except Exception:
                        pass
        threading.Thread(target=_do, daemon=True).start()

    def _resume_all(self):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        if not HAS_REQUESTS:
            return
        def _do():
            for d in self._downloads:
                if (d.get('state','') or '').lower() in ('paused','pausing','error'):
                    try:
                        _requests.post(
                            f'{BACKEND_URL}/api/download/{d["id"]}/resume', timeout=3)
                    except Exception:
                        pass
        threading.Thread(target=_do, daemon=True).start()

    def _force_start_next(self):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        # Priority: explicitly queued/waiting, then stalled active ones.
        candidates = []
        stalled = []
        for d in self._downloads:
            did = str(d.get('id') or '')
            if not did:
                continue
            st = (d.get('state') or '').lower()
            if st in ('waiting', 'queued'):
                candidates.append(d)
            elif st in ('downloading', 'active') and bool(d.get('is_stalled')):
                stalled.append(d)
        target = (candidates[0] if candidates else (stalled[0] if stalled else None))
        if not target:
            if hasattr(self, '_status_left'):
                self._status_left.setText('No queued/stalled download to force start.')
            return
        did = str(target.get('id') or '')
        self._api_force_start(did, source='manual')
        if hasattr(self, '_status_left'):
            name = target.get('movie_title') or target.get('name') or did
            self._status_left.setText(f'Force start requested: {name}')

    def _reset_download_engine(self):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        if not HAS_REQUESTS:
            QMessageBox.warning(self, 'Reset Engine', 'Requests library is missing.')
            return

        if hasattr(self, '_status_left'):
            self._status_left.setText('Resetting download engine...')
        btn = getattr(self, '_btn_reset_engine', None)
        if btn is not None:
            btn.setEnabled(False)

        def _do():
            ok = False
            msg = ''
            try:
                r = _requests.post(f'{BACKEND_URL}/api/engine/reset', timeout=25)
                data = r.json() if r.text else {}
                ok = bool(r.ok and data.get('success'))
                msg = data.get('message') or data.get('error') or f'HTTP {r.status_code}'
            except Exception as e:
                msg = str(e)

            def _done():
                rb = getattr(self, '_btn_reset_engine', None)
                if rb is not None:
                    rb.setEnabled(True)
                self._update_status_panel(force=True)
                if ok:
                    if hasattr(self, '_status_left'):
                        self._status_left.setText('Download engine reset complete.')
                    QMessageBox.information(self, 'Reset Engine', msg or 'Download engine reset complete.')
                    QTimer.singleShot(500, lambda: self._ensure_backend_started(force=True))
                else:
                    if hasattr(self, '_status_left'):
                        self._status_left.setText('Download engine reset failed.')
                    QMessageBox.warning(self, 'Reset Engine', f'Failed to reset engine:\n{msg}')

            QTimer.singleShot(0, _done)

        threading.Thread(target=_do, daemon=True).start()

    def _open_folder(self):
        # Try to get downloads folder from settings
        folder = None
        if HAS_REQUESTS:
            try:
                r = _requests.get(f'{BACKEND_URL}/api/settings', timeout=3)
                if r.ok:
                    s = r.json().get('settings') or {}
                    folder = s.get('download_path') or s.get('download_dir') or s.get('save_path')
            except Exception: pass
        if not folder:
            folder = str(Path.home() / 'Downloads' / 'Streamore')
        Path(folder).mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _open_settings(self):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Refresh UI if theme might have changed
            self._apply_global_style()
            self._refresh_table()

    def _open_dashboard(self):
        if not HAS_REQUESTS: return
        dlg = AnalyticsDialog(self)
        dlg.exec()

    def _open_history(self):
        if not HAS_REQUESTS:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle('Download History')
        dlg.resize(850, 600)
        dlg.setStyleSheet(f'background:{C["card"]}; color:{C["text"]};')
        lay = QVBoxLayout(dlg)
        
        table = QTableWidget(0, 7)
        table.setHorizontalHeaderLabels(['Date', 'Title', 'Quality', 'Size', 'Started', 'Finished', 'Result'])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setStyleSheet(self.styleSheet())
        lay.addWidget(table)
        
        def _load():
            try:
                r = _requests.get(f'{BACKEND_URL}/api/downloads/history?limit=150', timeout=6)
                if r.ok:
                    items = r.json().get('history') or []
                    table.setRowCount(len(items))
                    for i, d in enumerate(items):
                        def _it(t, color=None):
                            it = QTableWidgetItem(str(t or '-'))
                            if color: it.setForeground(QColor(color))
                            return it
                        
                        st = d.get('started_at', '')
                        if st: st = st.replace('T', ' ').split('.')[0]
                        ct = d.get('completed_at', '')
                        if ct: ct = ct.replace('T', ' ').split('.')[0]
                        
                        res = (d.get('result') or 'unknown').lower()
                        res_c = C['green'] if res in ('completed', 'complete') else (C['red'] if res == 'error' else C['muted'])
                        
                        table.setItem(i, 0, _it(st.split(' ')[0] if st else '-'))
                        table.setItem(i, 1, _it(d.get('movie_title')))
                        table.setItem(i, 2, _it(d.get('quality')))
                        table.setItem(i, 3, _it(fmt_bytes(d.get('size_total', 0))))
                        table.setItem(i, 4, _it(st))
                        table.setItem(i, 5, _it(ct))
                        table.setItem(i, 6, _it(res.capitalize(), res_c))
            except Exception as e:
                logger.error(f'History load error: {e}')

        QTimer.singleShot(0, _load)
        
        btns = QHBoxLayout()
        btns.addStretch()
        close_b = QPushButton('Close')
        close_b.setStyleSheet(f"background:{C['bg']}; color:{C['text']}; padding:8px 20px; border-radius:8px; border:1px solid {C['border']};")
        close_b.clicked.connect(dlg.accept)
        btns.addWidget(close_b)
        lay.addLayout(btns)
        dlg.exec()

    # Ã¢â€â‚¬Ã¢â€â‚¬ Context menu Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _ctx_menu(self, pos):
        if self._update_lock_active:
            return
        row = self._table.rowAt(pos.y())
        if row < 0: return
        item = self._table.item(row, 0)
        if not item: return
        did  = self._table.item(row, 1)
        if did: did = did.data(Qt.ItemDataRole.UserRole)
        else:   did = item.data(Qt.ItemDataRole.UserRole)
        if not did: return

        drec = next((d for d in self._downloads if str(d.get('id')) == str(did)), None)
        title = (drec.get('movie_title') if drec else '') or (drec.get('name') if drec else '') or 'Unknown'

        menu = QMenu(self)
        menu.setStyleSheet(f'background:{C["card"]}; color:{C["text"]}; border:1px solid {C["border"]};')
        state = (drec.get('state') if drec else '') or ''
        state = state.lower()
        if state in ('paused', 'pausing', 'error'):
            menu.addAction('Resume', lambda: self._api_action(did, 'resume'))
        elif state in ('downloading', 'active', 'waiting', 'queued'):
            menu.addAction('Pause', lambda: self._api_action(did, 'pause'))
        if state not in ('complete', 'completed', 'seeding', 'removed'):
            menu.addAction('Force Start', lambda: self._api_force_start(did))
        menu.addSeparator()
        menu.addAction('Move Up', lambda: self._api_move(did, 'up'))
        menu.addAction('Move Down', lambda: self._api_move(did, 'down'))
        pr_menu = menu.addMenu('Priority')
        pr_menu.addAction('Top (High)', lambda: self._api_priority(did, 'top'))
        pr_menu.addAction('Normal', lambda: self._api_priority(did, 'normal'))
        pr_menu.addAction('Bottom (Low)', lambda: self._api_priority(did, 'bottom'))
        menu.addSeparator()
        menu.addAction('Open Folder', lambda: self._api_action(did, 'open-folder'))
        menu.addAction('Play',        lambda: self._api_action(did, 'play'))
        menu.addSeparator()
        menu.addAction('Remove',      lambda: self._confirm_remove(did, title))
        menu.exec(self._table.mapToGlobal(pos))

    # Ã¢â€â‚¬Ã¢â€â‚¬ Bridge server & download queuing Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _start_bridge(self):
        threading.Thread(target=run_bridge_server, daemon=True).start()

    def _start_queue_timer(self):
        """Poll the shared queue every 500ms for downloads from the web app."""
        self._qtimer = QTimer(self)
        self._qtimer.setInterval(500)
        self._qtimer.timeout.connect(self._drain_queue)
        self._qtimer.start()

    def _drain_queue(self):
        with _download_queue_lock:
            items = list(_download_queue)
            _download_queue.clear()
        for payload in items:
            self._queue_download(payload)

    def _on_web_download(self, payload: dict):
        self._queue_download(payload)

    def _resolve_download_folder(self) -> Path:
        folder = ''
        try:
            cfg = load_config()
            folder = (
                str(cfg.get('download_path') or '').strip()
                or str(cfg.get('download_dir') or '').strip()
                or str(cfg.get('save_path') or '').strip()
            )
        except Exception:
            folder = ''
        if not folder:
            folder = str(Path.home() / 'Downloads' / 'Streamore')
        p = Path(folder).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _confirm_low_disk_space(self) -> bool:
        """
        Return True when queueing should continue.
        Shows a warning prompt if free space is very low.
        """
        try:
            target = self._resolve_download_folder()
            usage = shutil.disk_usage(str(target))
            free_gb = usage.free / (1024 ** 3)
            if free_gb < LOW_DISK_WARN_GB:
                msg = (
                    f'Low disk space detected on:\n{target}\n\n'
                    f'Free space: {free_gb:.2f} GB\n'
                    f'Recommended minimum: {LOW_DISK_WARN_GB} GB\n\n'
                    'Queue download anyway?'
                )
                res = QMessageBox.warning(
                    self,
                    'Low Disk Space',
                    msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                return res == QMessageBox.StandardButton.Yes
            return True
        except Exception:
            # Do not block queueing if the disk check itself fails.
            return True

    def _queue_download(self, payload: dict):
        if self._update_lock_active:
            self._warn_update_locked()
            return
        if not HAS_REQUESTS:
            QMessageBox.warning(self, 'Missing dependency',
                                'requests library not installed - cannot queue download.')
            return
        if not self._confirm_low_disk_space():
            if hasattr(self, '_status_left'):
                self._status_left.setText('Download cancelled due to low disk space.')
            return
        def _queue_worker():
            backend_ok = self._backend_online or is_backend_running()
            if not backend_ok:
                start_backend()
                time.sleep(QUEUE_BACKEND_START_WAIT_SECONDS)
                if not is_backend_running():
                    detail = f'\n\nDetails: {BACKEND_START_ERROR}' if BACKEND_START_ERROR else ''
                    raise RuntimeError(
                        'The download backend is not running.\n'
                        'Please wait a moment and try again.' + detail
                    )
            cfg = load_config()
            r = _requests.post(f'{BACKEND_URL}/api/download/start', timeout=10, json={
                'movie_id':    payload.get('movie_id', ''),
                'movie_title': payload.get('title', 'Unknown'),
                'quality':     payload.get('quality', '') or '',
                'magnet_link': payload.get('magnet', ''),
                'genres':      payload.get('genres', []) or [],
                'organize_by_genre': bool(cfg.get('organize_by_genre', True)),
            })
            if getattr(r, 'status_code', 200) >= 400:
                detail = ''
                try:
                    body = r.json()
                    if isinstance(body, dict):
                        detail = body.get('error') or body.get('message') or ''
                except Exception:
                    detail = getattr(r, 'text', '') or ''
                if not detail:
                    detail = f"Backend error ({getattr(r, 'status_code', 'unknown')})"
                raise RuntimeError(detail)
            
            TelemetryManager.track_event('download_started', {'has_movie_title': bool(payload.get('title'))})
            return payload.get('title', 'Movie')

        def _queue_ok(title: str):
            self._tray.showMessage(
                'Download Queued',
                f'{title} added to downloads.',
                QSystemTrayIcon.MessageIcon.Information, 3000,
            )
            self._show_window()

        def _queue_err(msg: str):
            QMessageBox.warning(self, 'Error', f'Failed to queue download:\n{msg}')

        self._run_background(_queue_worker, on_ok=_queue_ok, on_err=_queue_err)

    def keyPressEvent(self, event):
        if self._update_lock_active or self._startup_heal_lock_active:
            return super().keyPressEvent(event)

        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            sel = self._table.selectedItems()
            if sel:
                d_id = sel[0].data(Qt.ItemDataRole.UserRole)
                row = sel[0].row()
                widget = self._table.cellWidget(row, 1)
                title = widget.layout().itemAt(0).widget().text() if widget and widget.layout() else "Item"
                self._confirm_remove(d_id, title)
            event.accept()

        elif event.key() == Qt.Key.Key_Space:
            sel = self._table.selectedItems()
            if sel:
                d_id = sel[0].data(Qt.ItemDataRole.UserRole)
                for d in self._downloads:
                    if str(d.get('id')) == str(d_id):
                        st = (d.get('state', '') or '').lower()
                        if st in ('paused', 'pausing', 'error'):
                            self._api_action(d_id, 'resume')
                        elif st in ('downloading', 'active', 'seeding', 'waiting', 'queued'):
                            self._api_action(d_id, 'pause')
                        break
            event.accept()

        elif event.key() == Qt.Key.Key_Return:
            self._open_folder()
            event.accept()

        else:
            super().keyPressEvent(event)


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# PROTOCOL HANDLER (ytsdl://)
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

def handle_protocol_headless(uri: str):
    """Handle ytsdl:// when the GUI is not running Ã¢â‚¬â€ just push to the bridge."""
    try:
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)
        payload = {
            'magnet':   (params.get('magnet')   or [''])[0],
            'title':    (params.get('title')    or ['Unknown'])[0],
            'quality':  (params.get('quality')  or [''])[0],
            'movie_id': (params.get('movie_id') or [''])[0],
        }
        if not payload['magnet']:
            return
        # Push directly to backend
        if HAS_REQUESTS and is_backend_running() and not is_update_locked():
            r = _requests.post(f'{BACKEND_URL}/api/download/start', json={
                'movie_id':    payload['movie_id'],
                'movie_title': payload['title'],
                'quality':     payload['quality'],
                'magnet_link': payload['magnet'],
            }, timeout=8)
            if getattr(r, 'status_code', 200) >= 400:
                detail = ''
                try:
                    body = r.json()
                    if isinstance(body, dict):
                        detail = body.get('error') or body.get('message') or ''
                except Exception:
                    detail = getattr(r, 'text', '') or ''
                if not detail:
                    detail = 'Backend error ({})'.format(getattr(r, 'status_code', 'unknown'))
                raise RuntimeError(detail)
    except Exception as e:
        logger.error(f'Protocol handler error: {e}')


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# ENTRY POINT
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

def main():
    app_id = 'streamore_downloader_lock'
    
    # High-DPI support
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass

    # CRASH REPORTER: Catch unhandled exceptions
    sys.excepthook = show_crash_report

    app = QApplication(sys.argv)
    app.setApplicationName('Streamore Download Manager')
    app.setOrganizationName('Streamore')
    app.setQuitOnLastWindowClosed(False)

    # Check for another instance
    socket = QLocalSocket()
    socket.connectToServer(app_id)
    if socket.waitForConnected(500):
        # Already running!
        # If we have arguments (like a protocol URI), we can send them to the primary instance
        if len(sys.argv) > 1:
            socket.write(sys.argv[1].encode('utf-8'))
            socket.waitForBytesWritten(1000)
        
        print("Another instance is already running. Focusing that one...")
        # Most OS won't allow focusing from another process easily, but the primary 
        # instance will listen for this connection and show itself.
        return

    # If not running, start the local server for next time
    local_server = QLocalServer()
    local_server.removeServer(app_id) # Cleanup if previous crashed
    if not local_server.listen(app_id):
        print(f"Could not start local server: {local_server.errorString()}")

    window = DownloadManagerWindow()
    window.show()

    # Listen for new connection from secondary instances
    def _on_new_instance():
        new_socket = local_server.nextPendingConnection()
        if new_socket.waitForReadyRead(1000):
            msg = new_socket.readAll().data().decode('utf-8')
            if msg.lower().startswith('streamore://'):
                window._on_web_download({'magnet': msg, 'title': 'Remote Request', 'quality': ''})
        
        # Always bring primary to front
        window._show_window()

    local_server.newConnection.connect(_on_new_instance)

    # If the backend isn't running, try to start it
    if not is_backend_running():
        logger.info('Backend not running Ã¢â‚¬â€ attempting to startÃ¢â‚¬Â¦')
        threading.Thread(target=start_backend, daemon=True).start()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
