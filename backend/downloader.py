"""Simple aria2 download manager wrapper using JSON-RPC

This module controls an aria2c instance via its JSON-RPC interface. It will
start aria2c as a subprocess if not already running, and provide functions to
add magnet/torrent, pause, resume, remove downloads, and list active downloads.

This is a minimal implementation suitable for local single-user use.
"""
import subprocess
import threading
import time
import json
import os
import re
import shutil
import zipfile
import requests
from pathlib import Path
import logging

from backend.config import Config
from backend.database import get_db
from shared.models import Download
from shared.constants import (
    DOWNLOAD_STATE_QUEUED,
    DOWNLOAD_STATE_DOWNLOADING,
    DOWNLOAD_STATE_PAUSED,
    DOWNLOAD_STATE_COMPLETED,
    DOWNLOAD_STATE_ERROR
)

logger = logging.getLogger(__name__)

ARIA2RPC_URL = 'http://127.0.0.1:6800/jsonrpc'
ARIA2_RELEASE_API = os.getenv('ARIA2_RELEASE_API', 'https://api.github.com/repos/aria2/aria2/releases/latest')
ARIA2C_DOWNLOAD_URL = os.getenv('ARIA2C_DOWNLOAD_URL', '')
# Always prefer the bundled binary first (absolute path), then fall back to system aria2c
_project_root = Path(__file__).resolve().parent.parent
_appdata_root = Path(os.environ.get('APPDATA', str(Path.home()))).expanduser()


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

def _aria2_log_path() -> Path:
    log_dir = _appdata_root / 'StreamoreManager' / 'logs'
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return log_dir / 'aria2_backend.log'


def _aria2_bin_dir() -> Path:
    bin_dir = _appdata_root / 'StreamoreManager' / 'bin'
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return bin_dir


def _pick_aria2_asset(assets):
    if not assets:
        return None
    for asset in assets:
        name = str(asset.get('name', '')).lower()
        if name.endswith('.zip') and 'win' in name and ('64' in name or 'x64' in name):
            return asset
    for asset in assets:
        name = str(asset.get('name', '')).lower()
        if name.endswith('.zip') and 'win' in name:
            return asset
    return None


def _download_aria2_windows() -> bool:
    if os.name != 'nt':
        return False
    try:
        if ARIA2C_DOWNLOAD_URL:
            url = ARIA2C_DOWNLOAD_URL
        else:
            headers = {
                'Accept': 'application/vnd.github+json',
                'User-Agent': 'StreamoreManager',
            }
            r = requests.get(ARIA2_RELEASE_API, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json() if r.text else {}
            asset = _pick_aria2_asset(data.get('assets', []))
            if not asset:
                logger.error('aria2 download: no Windows asset found in latest release')
                return False
            url = asset.get('browser_download_url')
        if not url:
            logger.error('aria2 download: missing download url')
            return False
        logger.info(f'aria2 missing; downloading from {url}')
        tmp_dir = _appdata_root / 'StreamoreManager' / 'tmp'
        try:
            tmp_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if url.lower().endswith('.exe'):
            dest = _aria2_bin_dir() / 'aria2c.exe'
            with requests.get(url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                with open(dest, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
            return dest.exists()
        zip_path = tmp_dir / 'aria2c.zip'
        with requests.get(url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(zip_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        exe_member = None
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if name.lower().endswith('aria2c.exe'):
                    exe_member = name
                    break
            if not exe_member:
                logger.error('aria2 download: aria2c.exe not found in zip')
                return False
            dest = _aria2_bin_dir() / 'aria2c.exe'
            with zf.open(exe_member) as src, open(dest, 'wb') as dst:
                shutil.copyfileobj(src, dst)
        try:
            zip_path.unlink()
        except Exception:
            pass
        return dest.exists()
    except Exception as e:
        logger.error(f'aria2 download failed: {e}', exc_info=True)
        return False

def _find_aria2c() -> str:
    """Return an absolute path to the aria2c binary."""
    # 1. Bundled binaries (absolute, most reliable)
    for candidate in [
        _project_root / 'bin' / 'aria2c.exe',
        _project_root / 'bin' / 'aria2c.tmp',  # Windows Defender workaround
        _aria2_bin_dir() / 'aria2c.exe',
        _project_root / 'bin' / 'aria2c',       # Linux/Mac
    ]:
        if candidate.exists():
            return str(candidate)
    # 2. System-installed aria2c â€” resolve to absolute path
    found = shutil.which('aria2c')
    if found:
        return str(Path(found).resolve())
    # 3. Fallback (will produce a clear error when checked later)
    return str(_project_root / 'bin' / 'aria2c.exe')

ARIA2C_BINARY = _find_aria2c()
ARIA2_RPC_SECRET = os.getenv('ARIA2_RPC_SECRET', '')

# Broad public tracker set for better peer discovery across different torrents.
PUBLIC_TRACKERS = (
    'udp://tracker.opentrackr.org:1337/announce,'
    'udp://open.stealth.si:80/announce,'
    'udp://tracker.openbittorrent.com:6969/announce,'
    'udp://tracker.torrent.eu.org:451/announce,'
    'udp://exodus.desync.com:6969/announce,'
    'udp://tracker.bittor.pw:1337/announce,'
    'udp://tracker.internetwarriors.net:1337/announce,'
    'udp://tracker.leechers-paradise.org:6969/announce,'
    'udp://tracker.coppersurfer.tk:6969/announce,'
    'udp://9.rarbg.to:2710/announce'
)

PROMO_FILE_NAME = 'Streamore.txt'
PROMO_FILE_CONTENT = 'Streamore\nhttps://streamore-five.vercel.app\n'
PROMO_TAG = 'Streamore'
PROMO_TAG_PATTERN = re.compile(r'(\[)?yts\.bz(\])?', re.IGNORECASE)
STALL_RECOVERY_SECONDS = int(os.getenv('STALL_RECOVERY_SECONDS', '120'))
STALL_RECOVERY_COOLDOWN_SECONDS = int(os.getenv('STALL_RECOVERY_COOLDOWN_SECONDS', '120'))
STALL_ZERO_SPEED_EPSILON = float(os.getenv('STALL_ZERO_SPEED_EPSILON', '1024'))

class Aria2Manager:
    def __init__(self):
        self.process = None
        self._lock = threading.Lock()
        self.session = requests.Session()
        self._cleaned_downloads = set()
        self._progress_snapshots = {}
        self._stalled_since = {}
        self._recovery_cooldown = {}
        self._speed_ema = {}
        self._last_waiting_promotion_at = 0.0
        self._last_rebalance_at = 0.0
        self._last_ensure_attempt_at = 0.0
        self._engine_stall_since = 0.0
        self._last_completed_length = {}
        # Initialize DB handle
        self.db = get_db()
        # Ensure aria2 is running (may start aria2c subprocess)
        self._ensure_aria2_running()
        # Start background polling thread to sync aria2 status to DB
        self._stop_event = threading.Event()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        # One-time cleanup for already-completed downloads
        threading.Thread(target=self._cleanup_completed_on_start, daemon=True).start()

    def _ensure_aria2_running(self, force_restart: bool = False):
        """Start aria2c in RPC mode if not already available."""
        global ARIA2C_BINARY

        # 1) If RPC is already healthy and restart was not explicitly requested, keep it.
        if not force_restart:
            try:
                r = self.session.post(ARIA2RPC_URL, json={'jsonrpc': '2.0', 'id': 'test', 'method': 'aria2.getVersion'}, timeout=2)
                if r.status_code == 200:
                    logger.info('aria2 RPC is reachable')
                    return
            except Exception:
                pass

        # 2) Restart path: clean stale aria2 processes so we can bind RPC port reliably.
        if os.name == 'nt':
            try:
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'aria2c.exe', '/T'],
                    capture_output=True,
                    check=False,
                    **_windows_hidden_subprocess_kwargs(),
                )
                logger.info("Cleaned up existing aria2c processes")
            except Exception:
                pass

        # 3) Build candidate list (bundled first, then appdata/system).
        candidates = []

        def _add_candidate(path_like):
            if not path_like:
                return
            try:
                p = Path(path_like)
            except Exception:
                return
            if not p.exists():
                return
            resolved = str(p.resolve())
            if resolved not in candidates:
                candidates.append(resolved)

        _add_candidate(_find_aria2c())
        _add_candidate(_project_root / 'bin' / 'aria2c.exe')
        _add_candidate(_project_root / 'bin' / 'aria2c.tmp')
        _add_candidate(_aria2_bin_dir() / 'aria2c.exe')
        _add_candidate(shutil.which('aria2c'))

        if not candidates and os.name == 'nt':
            if _download_aria2_windows():
                _add_candidate(_aria2_bin_dir() / 'aria2c.exe')

        if not candidates:
            logger.error(f"aria2 binary NOT found. Last searched: {ARIA2C_BINARY}")
            return

        file_allocation = 'prealloc' if os.name == 'nt' else 'falloc'
        log_path = _aria2_log_path()
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            if Config.DOWNLOAD_PATH:
                Path(Config.DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create directories for aria2: {e}")

        settings = self._torrent_option_values()
        dl_limit = f'--max-overall-download-limit={settings["max_download_speed"]}K' if settings["max_download_speed"] > 0 else '--max-overall-download-limit=0'
        ul_limit = f'--max-overall-upload-limit={settings["max_upload_speed"]}K' if settings["max_upload_speed"] > 0 else '--max-overall-upload-limit=0'
        dht_flag = 'true' if settings["enable_dht"] else 'false'
        pex_flag = 'true' if settings["enable_pex"] else 'false'

        base_args = [
            '--enable-rpc',
            '--rpc-listen-all=false',
            '--rpc-allow-origin-all',
            '--rpc-listen-port=6800',
            f'--log={log_path}',
            '--log-level=notice',
            '--console-log-level=warn',
            dl_limit,
            ul_limit,
            '--max-download-limit=0',
            '--max-upload-limit=0',
            '--split=16',
            f'--max-connection-per-server={max(1, int(settings["max_connections"]))}',
            '--min-split-size=1M',
            f'--max-concurrent-downloads={max(1, int(settings["max_concurrent"]))}',
            '--listen-port=6881-6999',
            f'--enable-dht={dht_flag}',
            '--dht-listen-port=6881-6999',
            '--enable-dht6=false',
            f'--enable-peer-exchange={pex_flag}',
            '--bt-enable-lpd=true',
            f'--bt-tracker={PUBLIC_TRACKERS}',
            f'--bt-max-peers={int(settings["bt_max_peers"])}',
            '--bt-request-peer-speed-limit=10M',
            '--bt-tracker-connect-timeout=10',
            '--bt-tracker-timeout=60',
            '--bt-tracker-interval=15',
            '--bt-prioritize-piece=head,tail',
            f'--seed-ratio={settings["seed_ratio"]}',
            f'--seed-time={int(settings["seed_time"])}',
            f'--file-allocation={file_allocation}',
            f'--dir={Config.DOWNLOAD_PATH}',
        ]
        if ARIA2_RPC_SECRET:
            base_args.append(f"--rpc-secret={ARIA2_RPC_SECRET}")

        # 4) Try each candidate until one provides a healthy RPC endpoint.
        for binary in candidates:
            cmd = [binary] + base_args
            logger.info(f"Starting aria2c candidate: {binary}")
            try:
                try:
                    logf = open(str(log_path), 'a', encoding='utf-8')
                except Exception as e:
                    logger.warning(f"Failed to open aria2 log file at {log_path}: {e}")
                    logf = subprocess.DEVNULL
                self._aria2_log_file = logf
                self.process = subprocess.Popen(
                    cmd,
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                    **_windows_hidden_subprocess_kwargs(),
                )
                logger.info(f"aria2c process started (pid={self.process.pid}) from {binary}")
            except Exception as e:
                logger.error(f"Failed to start aria2c subprocess with {binary}: {e}")
                continue

            for attempt in range(20):
                try:
                    r = self.session.post(ARIA2RPC_URL, json={'jsonrpc': '2.0', 'id': 'test', 'method': 'aria2.getVersion'}, timeout=2)
                    if r.status_code == 200:
                        ARIA2C_BINARY = str(binary)
                        logger.info(f'aria2 RPC is reachable after starting aria2c ({binary})')
                        return
                except Exception:
                    pass
                if self.process.poll() is not None:
                    logger.error(f'aria2c process exited unexpectedly while starting ({binary})')
                    break
                time.sleep(0.5)

            try:
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=2)
            except Exception:
                pass
            self.process = None

        logger.error(f'aria2 RPC did not respond after trying candidates: {candidates}')

    def _attempt_recover_aria2(self):
        """
        Try to recover aria2 RPC with a small cooldown to avoid restart loops
        under heavy polling load.
        """
        now = time.time()
        if (now - float(self._last_ensure_attempt_at or 0.0)) < 8.0:
            return
        self._last_ensure_attempt_at = now
        try:
            self._ensure_aria2_running(force_restart=True)
        except Exception as e:
            logger.warning(f'aria2 recovery attempt failed: {e}')

    def rpc_available(self, timeout: int = 2):
        """Fast health check for aria2 RPC."""
        try:
            r = self.session.post(
                ARIA2RPC_URL,
                json={'jsonrpc': '2.0', 'id': 'health', 'method': 'aria2.getVersion'},
                timeout=timeout,
            )
            return r.status_code == 200
        except Exception as e:
            logger.debug(f"aria2 RPC health check failed: {e}")
            return False

    def _rpc_call(self, method, params=None):
        payload = {
            'jsonrpc': '2.0',
            'id': 'rpc',
            'method': method,
            'params': params or []
        }
        if ARIA2_RPC_SECRET:
            payload['params'] = [f'token:{ARIA2_RPC_SECRET}'] + (params or [])
        # Try a few times with a longer timeout to avoid intermittent read timeouts
        attempts = 3
        for attempt in range(attempts):
            try:
                r = self.session.post(ARIA2RPC_URL, json=payload, timeout=10)
                r.raise_for_status()
                data = r.json()
                return data.get('result') if 'result' in data else data
            except Exception as e:
                logger.debug(f"aria2 RPC call attempt {attempt+1}/{attempts} failed: {method} {e}")
                # Any RPC failure can mean aria2 died or port got wedged; attempt recovery.
                if attempt == 0:
                    self._attempt_recover_aria2()
                time.sleep(1)
        logger.error(f"aria2 RPC call failed after {attempts} attempts: {method}")
        return None

    def _rekey_download(self, old_gid: str, new_gid: str):
        """Move a DB download record from old_gid to new_gid."""
        try:
            existing = self.db.get_download(str(old_gid))
            if not existing:
                return False
            if str(old_gid) == str(new_gid):
                return False
            existing.id = str(new_gid)
            self.db.delete_download(str(old_gid))
            self.db.add_download(existing)
            logger.info(f"Rekeyed download {old_gid} -> {new_gid}")
            return True
        except Exception as e:
            logger.warning(f"Failed to rekey download {old_gid} -> {new_gid}: {e}")
            return False

    def change_global_option(self, options: dict):
        if not options:
            return None
        return self._rpc_call('aria2.changeGlobalOption', [options])

    def reset_engine(self) -> dict:
        """
        Soft-reset the download engine.
        - Attempts aria2 RPC recovery/restart.
        - Re-applies global speed/peer options from persisted settings.
        """
        result = {
            'success': False,
            'before_online': False,
            'after_online': False,
            'message': '',
        }
        with self._lock:
            try:
                result['before_online'] = bool(self.rpc_available(timeout=2))

                # Recovery path first; it escalates to force restart when needed.
                self._attempt_recover_aria2()
                if not self.rpc_available(timeout=3):
                    self._ensure_aria2_running(force_restart=True)

                online = bool(self.rpc_available(timeout=4))
                result['after_online'] = online
                if not online:
                    result['message'] = 'aria2 is still offline after reset.'
                    return result

                # Re-apply persisted performance options to make reset deterministic.
                settings = self._torrent_option_values()
                global_opts = {
                    'max-overall-download-limit': f'{int(settings["max_download_speed"])}K' if settings["max_download_speed"] > 0 else '0',
                    'max-overall-upload-limit': f'{int(settings["max_upload_speed"])}K' if settings["max_upload_speed"] > 0 else '0',
                    'max-concurrent-downloads': str(max(1, int(settings["max_concurrent"]))),
                    'max-connection-per-server': str(max(1, int(settings["max_connections"]))),
                    'bt-max-peers': str(int(settings["bt_max_peers"])),
                    'seed-ratio': str(settings["seed_ratio"]),
                    'seed-time': str(int(settings["seed_time"])),
                    'enable-dht': 'true' if settings["enable_dht"] else 'false',
                    'enable-peer-exchange': 'true' if settings["enable_pex"] else 'false',
                }
                self.change_global_option(global_opts)

                result['success'] = True
                result['message'] = 'Download engine reset complete.'
                return result
            except Exception as e:
                logger.error(f"reset_engine failed: {e}", exc_info=True)
                result['message'] = str(e)
                return result

    def _get_torrent_setting(self, key: str, default):
        # Prefer torrent_* namespace but fall back to legacy key if present
        val = self.db.get_setting(f'torrent_{key}', None)
        if val is None:
            val = self.db.get_setting(key, None)
        return val if val is not None else default

    def _torrent_option_values(self):
        def _to_int(v, default=0):
            try:
                return int(v)
            except Exception:
                return default

        def _to_float(v, default=0.0):
            try:
                return float(v)
            except Exception:
                return default

        def _to_bool(v, default=True):
            if isinstance(v, bool):
                return v
            if v is None:
                return default
            return str(v).strip().lower() in ('1', 'true', 'yes', 'on')

        return {
            'max_download_speed': _to_int(self._get_torrent_setting('max_download_speed', 0), 0),
            'max_upload_speed':   _to_int(self._get_torrent_setting('max_upload_speed', 0), 0),
            'max_concurrent':     _to_int(self._get_torrent_setting('max_concurrent', getattr(Config, "MAX_CONCURRENT_DOWNLOADS", 5)), getattr(Config, "MAX_CONCURRENT_DOWNLOADS", 5)),
            'max_connections':    _to_int(self._get_torrent_setting('max_connections', 16), 16),
            'bt_max_peers':       _to_int(self._get_torrent_setting('bt_max_peers', 0), 0),
            'seed_ratio':         _to_float(self._get_torrent_setting('seed_ratio', 0.0), 0.0),
            'seed_time':          _to_int(self._get_torrent_setting('seed_time', 0), 0),
            'enable_dht':         _to_bool(self._get_torrent_setting('enable_dht', True), True),
            'enable_pex':         _to_bool(self._get_torrent_setting('enable_pex', True), True),
        }

    def add_magnet(self, magnet_uri: str, save_path: str = None):
        # Per-download options to maximise torrent speed
        # Add a short list of well-known public trackers to improve peer discovery
        settings = self._torrent_option_values()
        options = {
            'bt-max-peers': str(int(settings['bt_max_peers'])),
            'seed-ratio': str(settings['seed_ratio']),
            'seed-time': str(int(settings['seed_time'])),
            'bt-prioritize-piece': 'head,tail',
            'max-download-limit': f'{int(settings["max_download_speed"])}K' if settings["max_download_speed"] > 0 else '0',
            'max-upload-limit': f'{int(settings["max_upload_speed"])}K' if settings["max_upload_speed"] > 0 else '0',
            'max-connection-per-server': str(int(settings['max_connections'])),
            'bt-tracker': PUBLIC_TRACKERS,
        }
        # Allow overriding per-download destination directory
        if save_path:
            try:
                options['dir'] = str(save_path)
            except Exception:
                options['dir'] = save_path
        return self._rpc_call('aria2.addUri', [[magnet_uri], options])

    def add_torrent(self, torrent_path: str, save_path: str = None):
        """Add a torrent file to aria2 by reading and sending as base64"""
        import base64
        
        fp = Path(torrent_path).resolve()
        if not fp.exists():
            logger.error(f"Torrent file not found: {torrent_path}")
            return None
        
        try:
            # Read torrent file and encode as base64
            with open(fp, 'rb') as f:
                torrent_data = f.read()
            torrent_base64 = base64.b64encode(torrent_data).decode('utf-8')
            
            # Per-download options to maximise torrent speed
            settings = self._torrent_option_values()
            options = {
                'bt-max-peers': str(int(settings['bt_max_peers'])),
                'seed-ratio': str(settings['seed_ratio']),
                'seed-time': str(int(settings['seed_time'])),
                'bt-prioritize-piece': 'head,tail',
                'max-download-limit': f'{int(settings["max_download_speed"])}K' if settings["max_download_speed"] > 0 else '0',
                'max-upload-limit': f'{int(settings["max_upload_speed"])}K' if settings["max_upload_speed"] > 0 else '0',
                'max-connection-per-server': str(int(settings['max_connections'])),
                'bt-tracker': PUBLIC_TRACKERS,
            }
            if save_path:
                try:
                    options['dir'] = str(save_path)
                except Exception:
                    options['dir'] = save_path
            # Use aria2.addTorrent method with base64 data
            return self._rpc_call('aria2.addTorrent', [torrent_base64, [], options])
        except Exception as e:
            logger.error(f"Failed to read/encode torrent file: {e}")
            return None

    def tell_active(self):
        return self._rpc_call('aria2.tellActive')

    def tell_waiting(self, offset=0, num=1000):
        return self._rpc_call('aria2.tellWaiting', [offset, num])

    def tell_stopped(self, offset=0, num=1000):
        return self._rpc_call('aria2.tellStopped', [offset, num])

    def pause(self, gid):
        return self._rpc_call('aria2.pause', [gid])

    def resume(self, gid):
        return self._rpc_call('aria2.unpause', [gid])

    def remove(self, gid):
        return self._rpc_call('aria2.remove', [gid])

    def change_position(self, gid: str, pos: int, how: str = 'POS_CUR'):
        """Move a download within the aria2 queue."""
        return self._rpc_call('aria2.changePosition', [gid, int(pos), how])

    def _max_concurrent_downloads(self) -> int:
        try:
            v = self.db.get_setting('torrent_max_concurrent', None)
            if v is None:
                return max(1, int(getattr(Config, 'MAX_CONCURRENT_DOWNLOADS', 5)))
            return max(1, int(v))
        except Exception:
            return max(1, int(getattr(Config, 'MAX_CONCURRENT_DOWNLOADS', 5)))

    def _enforce_active_limit(self, active_items: list):
        """
        Keep active torrents within configured max_concurrent.
        Extra active items are paused, preferring to keep the fastest/progressed ones running.
        """
        if not active_items:
            return
        max_concurrent = self._max_concurrent_downloads()
        if len(active_items) <= max_concurrent:
            return

        def _sort_key(it):
            try:
                return (
                    int(it.get('downloadSpeed', 0)),
                    int(it.get('completedLength', 0)),
                )
            except Exception:
                return (0, 0)

        need_pause = len(active_items) - max_concurrent
        for it in sorted(active_items, key=_sort_key)[:need_pause]:
            gid = str(it.get('gid') or '')
            if not gid:
                continue
            try:
                self.pause(gid)
                d = self.db.get_download(gid)
                if d:
                    d.state = DOWNLOAD_STATE_PAUSED
                    self.db.add_download(d)
                logger.info(f"Auto-paused extra active download to respect max_concurrent: {gid}")
            except Exception as e:
                logger.debug(f"Could not auto-pause {gid} while enforcing max_concurrent: {e}")

    def _promote_waiting_if_slot(self, active_items: list, waiting_items: list):
        """
        If there is a free concurrent slot, aggressively nudge the oldest waiting item.
        This avoids long queue stalls when aria2 does not auto-promote reliably.
        """
        if not waiting_items:
            return
        max_concurrent = self._max_concurrent_downloads()
        if len(active_items) >= max_concurrent:
            return

        now = time.time()
        if (now - self._last_waiting_promotion_at) < 8.0:
            return

        waiting_only = [w for w in waiting_items if str(w.get('status', '')).lower() == 'waiting']
        if not waiting_only:
            return
        target = waiting_only[0]
        gid = str(target.get('gid') or '')
        if not gid:
            return

        try:
            self.change_position(gid, 0, 'POS_SET')
            self.resume(gid)
            self._last_waiting_promotion_at = now
            logger.info(f"Auto-promoted waiting download into free slot: {gid}")
        except Exception as e:
            logger.debug(f"Could not promote waiting download {gid}: {e}")

    def _compute_eta(self, gid: str, total_length: int, completed_length: int, instant_rate: float) -> int | None:
        remaining = max(0, int(total_length) - int(completed_length))
        if remaining <= 0:
            self._speed_ema[gid] = 0.0
            return 0

        speed = max(0.0, float(instant_rate or 0.0))
        prev = float(self._speed_ema.get(gid, 0.0))
        if speed > 0:
            ema = speed if prev <= 0 else (prev * 0.7 + speed * 0.3)
        else:
            ema = prev * 0.85
        self._speed_ema[gid] = ema

        effective = ema if ema > STALL_ZERO_SPEED_EPSILON else speed
        if effective > 0:
            return int(max(0, remaining / effective))
        return None

    def _rebalance_stalled_vs_waiting(self, active_items: list, waiting_items: list):
        """
        If queue is blocked (full active set + waiting exists), rotate out the most stalled active item.
        """
        if not active_items or not waiting_items:
            return
        max_concurrent = self._max_concurrent_downloads()
        if len(active_items) < max_concurrent:
            return

        now = time.time()
        if (now - self._last_rebalance_at) < 30.0:
            return

        stalled_candidates = []
        for it in active_items:
            gid = str(it.get('gid') or '')
            if not gid:
                continue
            stalled_since = float(self._stalled_since.get(gid, 0.0))
            if stalled_since <= 0:
                continue
            if (now - stalled_since) < STALL_RECOVERY_SECONDS:
                continue
            try:
                speed = float(it.get('downloadSpeed', 0) or 0)
                peers = int(it.get('numPeers', 0) or 0)
                seeds = int(it.get('numSeeders', 0) or 0)
            except Exception:
                speed, peers, seeds = 0.0, 0, 0
            if speed <= STALL_ZERO_SPEED_EPSILON and (peers <= 1 and seeds <= 1):
                stalled_candidates.append((stalled_since, gid))

        if not stalled_candidates:
            return

        stalled_candidates.sort(key=lambda x: x[0])  # oldest stall first
        stalled_gid = stalled_candidates[0][1]
        waiting_gid = str(waiting_items[0].get('gid') or '')
        if not waiting_gid:
            return

        try:
            self.pause(stalled_gid)
            self.change_position(waiting_gid, 0, 'POS_SET')
            self.resume(waiting_gid)
            self._last_rebalance_at = now
            logger.info(f"Rebalanced stalled queue: paused {stalled_gid}, promoted {waiting_gid}")
        except Exception as e:
            logger.debug(f"Queue rebalance failed ({stalled_gid} -> {waiting_gid}): {e}")

    def _maybe_recover_stalled_active(self, gid: str, item: dict, progress: float, download_rate: float):
        """
        Recover torrents that are active but stuck with no progress and near-zero speed.
        Uses a cooldown so we don't thrash pause/resume calls.
        """
        state = str(item.get('_state', '')).lower()
        now = time.time()
        if state != DOWNLOAD_STATE_DOWNLOADING:
            self._stalled_since.pop(gid, None)
            self._progress_snapshots.pop(gid, None)
            return

        prev_progress = self._progress_snapshots.get(gid, progress)
        progress_moved = progress > (float(prev_progress) + 0.05)
        has_speed = float(download_rate) > STALL_ZERO_SPEED_EPSILON

        if progress_moved or has_speed:
            self._progress_snapshots[gid] = progress
            self._stalled_since.pop(gid, None)
            return

        first_stalled = self._stalled_since.setdefault(gid, now)
        self._progress_snapshots[gid] = progress
        if (now - first_stalled) < STALL_RECOVERY_SECONDS:
            return

        last_recovery = float(self._recovery_cooldown.get(gid, 0.0))
        if (now - last_recovery) < STALL_RECOVERY_COOLDOWN_SECONDS:
            return

        self._recovery_cooldown[gid] = now
        try:
            # Move up and nudge session to force tracker/peer refresh.
            self.change_position(gid, 0, 'POS_SET')
            self.pause(gid)
            time.sleep(0.2)
            self.resume(gid)
            logger.info(f"Auto-recovered stalled active download: {gid}")
        except Exception as e:
            logger.debug(f"Auto-recover failed for stalled download {gid}: {e}")

    def _poll_loop(self):
        """Background loop that polls aria2 and updates DB download rows."""
        interval = getattr(Config, 'DOWNLOAD_POLL_INTERVAL_SECONDS', 5)
        logger.info(f"Starting aria2 poll loop (interval={interval}s)")
        
        last_history_cleanup = 0.0

        while not getattr(self, '_stop_event') or not self._stop_event.is_set():
            try:
                # 1. Fetch current status from aria2
                active = self.tell_active() or []
                waiting = self.tell_waiting(0, 1000) or []
                stopped = self.tell_stopped(0, 1000) or []

                # 2. Engine-wide stall recovery
                if active:
                    any_moving = any(float(it.get('downloadSpeed', 0)) > STALL_ZERO_SPEED_EPSILON for it in active)
                    now = time.time()
                    if any_moving:
                        self._engine_stall_since = 0.0
                    else:
                        if not self._engine_stall_since:
                            self._engine_stall_since = now
                        elif (now - self._engine_stall_since) > 300: # 5 minutes of total stall
                            logger.warning("Engine-wide stall detected (all downloads at 0 speed for 5m). Restarting aria2...")
                            self._ensure_aria2_running(force_restart=True)
                            self._engine_stall_since = 0.0
                else:
                    self._engine_stall_since = 0.0

                # 3. Enforce concurrency limits and promote waiting items
                self._enforce_active_limit(active)
                self._promote_waiting_if_slot(active, waiting)

                # 4. Process all items
                combined = []
                for it in active:
                    it['_state'] = DOWNLOAD_STATE_DOWNLOADING
                    combined.append(it)
                for it in waiting:
                    it['_state'] = DOWNLOAD_STATE_QUEUED
                    combined.append(it)
                for it in stopped:
                    it['_state'] = DOWNLOAD_STATE_COMPLETED if it.get('status') == 'complete' else DOWNLOAD_STATE_ERROR
                    combined.append(it)

                # 5. Update Database rows
                for item in combined:
                    gid = item.get('gid')
                    if not gid: continue

                    # Handle GID following (for magnets/metadata)
                    try:
                        following = item.get('following')
                        if following: self._rekey_download(str(following), str(gid))
                        followed_by = item.get('followedBy') or []
                        if followed_by:
                            new_gid = str(followed_by[0])
                            if new_gid and new_gid != str(gid): self._rekey_download(str(gid), new_gid)
                    except Exception: pass

                    # Sync with DB
                    existing = self.db.get_download(str(gid))
                    if not existing: continue

                    # Map aria2 data
                    try:
                        c_len = int(item.get('completedLength', 0))
                        t_len = int(item.get('totalLength', 0))
                        progress = round(c_len / t_len * 100.0, 2) if t_len > 0 else 0.0
                    except Exception: progress = 0.0

                    dl_rate = float(item.get('downloadSpeed', 0))
                    ul_rate = float(item.get('uploadSpeed', 0))
                    
                    # Update fields
                    existing.state = item.get('_state', existing.state)
                    existing.progress = progress
                    existing.download_rate = dl_rate
                    existing.upload_rate = ul_rate
                    existing.num_peers = int(item.get('numPeers', 0))
                    existing.num_seeds = int(item.get('numSeeders', 0))
                    existing.size_downloaded = c_len
                    existing.size_total = t_len

                    # Update Name from aria2 if DB name is empty or looks like a GID/Hash
                    aria2_name = ""
                    bt_info = item.get('bittorrent', {})
                    if bt_info and bt_info.get('info'):
                        aria2_name = bt_info.get('info', {}).get('name', '')
                    if not aria2_name:
                        files = item.get('files', [])
                        if files and files[0].get('path'):
                            from pathlib import Path
                            aria2_name = Path(files[0]['path']).name
                    if aria2_name:
                        existing.name = aria2_name

                    # Update ETA
                    eta_val = item.get('eta', None)
                    try:
                        eta_val = int(eta_val) if eta_val is not None else None
                    except: eta_val = None
                    if eta_val is None:
                        eta_val = self._compute_eta(str(gid), t_len, c_len, dl_rate)
                    existing.eta = int(max(0, eta_val)) if eta_val is not None else 0

                    # BANDWIDTH TRACKING
                    c_len = int(item.get('completedLength', 0))
                    gid_str = str(gid)
                    if gid_str in self._last_completed_length:
                        delta = c_len - self._last_completed_length[gid_str]
                        if delta > 0:
                            try: self.db.record_bandwidth(delta)
                            except: pass
                    self._last_completed_length[gid_str] = c_len

                    # Recover individual stalls
                    self._maybe_recover_stalled_active(str(gid), item, progress, dl_rate)

                    # LOG SPEED HISTORY
                    if existing.state == DOWNLOAD_STATE_DOWNLOADING:
                         try: self.db.add_speed_record(str(gid), dl_rate)
                         except: pass

                    # Completion Logic
                    if existing.state == DOWNLOAD_STATE_COMPLETED and not existing.completed_at:
                        from datetime import datetime
                        existing.completed_at = datetime.now().isoformat()
                        if existing.save_path:
                            td = Path(existing.save_path)
                            if aria2_name:
                                pot = td / aria2_name
                                if pot.exists() and pot.is_dir(): td = pot
                            if str(gid) not in self._cleaned_downloads:
                                self._cleanup_junk_files(str(td))
                                self._cleaned_downloads.add(str(gid))

                    self.db.add_download(existing)

                # 6. Rebalance Stuck Queue
                self._rebalance_stalled_vs_waiting(active, waiting)

                live_gids = {str(it.get('gid')) for it in all_items if it.get('gid')}
                for gid in list(self._progress_snapshots.keys()):
                    if gid not in live_gids:
                        self._progress_snapshots.pop(gid, None)
                        self._last_completed_length.pop(gid, None)
                        self._stalled_since.pop(gid, None)
                        self._recovery_cooldown.pop(gid, None)
                        self._speed_ema.pop(gid, None)

            except Exception as e:
                logger.debug(f"Error in aria2 poll loop: {e}")

            # Sleep until next poll
            time.sleep(interval)

    def get_files(self, gid: str):
        """Get file list for a download"""
        try:
            return self._rpc_call('aria2.tellStatus', [gid, ['files', 'dir']])
        except Exception:
            return None

    def purge_download(self, gid: str):
        """Completely remove a download from aria2, including result."""
        try:
            # 1. Try remove (for active/waiting)
            try:
                self.remove(gid)
            except Exception:
                pass
            
            # 2. Try purgeDownloadResult (for stopped/error/complete)
            # This is critical to stop aria2 from continually reporting it as 'stopped'
            self._rpc_call('aria2.purgeDownloadResult', [gid])
            logger.info(f"Purged download {gid} from aria2")
            return True
        except Exception as e:
            logger.error(f"Failed to purge download {gid}: {e}")
            return False

    def _cleanup_junk_files(self, save_dir: str):
        """Remove common junk files included in torrents (e.g. YTS site links)."""
        try:
            root = Path(save_dir)
            if not root.exists():
                return
            if root.is_file():
                root = root.parent

            # Rename [YTS.BZ] tag in filenames to [Streamore]
            try:
                for f in root.rglob('*'):
                    if not f.is_file():
                        continue
                    name = f.name
                    if PROMO_TAG_PATTERN.search(name):
                        new_name = PROMO_TAG_PATTERN.sub(f'[{PROMO_TAG}]', name)
                        if new_name != name:
                            target = f.with_name(new_name)
                            if target.exists():
                                # Avoid collisions by appending a suffix
                                stem = target.stem
                                suffix = target.suffix
                                target = target.with_name(f"{stem}-{PROMO_TAG}{suffix}")
                            f.rename(target)
            except Exception as e:
                logger.debug(f"Filename tag rename skipped: {e}")
            
            # Common patterns for YTS/YIFY junk files (targeted)
            junk_patterns = [
                "*YTS*",
                "*YIFY*",
                "www.YTS*",
                "*.url",
                "*.htm*",
                "*.lnk",
            ]
            
            # File extensions to NEVER delete (safety)
            movie_extensions = ['.mp4', '.mkv', '.avi', '.ts', '.m4v', '.mov', '.wmv', '.flv']
            sub_extensions = ['.srt', '.vtt', '.sub', '.idx', '.ass', '.ssa']
            keep_extensions = movie_extensions + sub_extensions
            # User-requested hard cleanup: always remove poster/subtitle sidecar files.
            force_remove_extensions = {'.jpg', '.jpeg', '.srt'}
            
            logger.info(f"Cleaning up junk files in: {save_dir}")
            
            # Recursive search for all junk files
            removed_count = 0
            
            # 1. First, handle files inside the directory (and subdirectories)
            # Use rglob to find files everywhere inside the folder
            promo_lower = PROMO_FILE_NAME.lower()
            for pattern in junk_patterns:
                # We use rglob for matching names anywhere in the tree
                for f in root.rglob(pattern):
                    try:
                        if f.is_file():
                            if f.name.lower() == promo_lower:
                                continue
                            # Safety check: never delete movies or subs
                            ext = f.suffix.lower()
                            if ext in keep_extensions or ext == '.nfo':
                                continue
                            
                            # Additional safety: don't delete large files (junk is usually < 1MB)
                            if f.stat().st_size > 5 * 1024 * 1024: 
                                continue

                            f.unlink()
                            removed_count += 1
                            logger.debug(f"Removed junk file: {f.name}")
                    except Exception as fe:
                        logger.debug(f"Failed to remove {f}: {fe}")

            # Additional targeted cleanup for YTS/YIFY promo files
            try:
                for f in root.rglob('*'):
                    if not f.is_file():
                        continue
                    if f.name.lower() == promo_lower:
                        continue
                    name_lower = f.name.lower()
                    if 'yts' in name_lower or 'yify' in name_lower or 'yts.bz' in name_lower or 'ytsproxies' in name_lower:
                        ext = f.suffix.lower()
                        if ext in keep_extensions or ext == '.nfo':
                            continue
                        if f.stat().st_size > 5 * 1024 * 1024:
                            continue
                        f.unlink()
                        removed_count += 1
                        logger.debug(f"Removed promo file: {f.name}")
            except Exception as fe:
                logger.debug(f"Failed targeted promo cleanup: {fe}")

            # 1b. Force-remove specific sidecar files in all movie folders.
            try:
                for f in root.rglob('*'):
                    if not f.is_file():
                        continue
                    ext = f.suffix.lower()
                    if ext not in force_remove_extensions:
                        continue
                    try:
                        f.unlink()
                        removed_count += 1
                        logger.debug(f"Removed forced sidecar file: {f.name}")
                    except Exception as fe:
                        logger.debug(f"Failed forced remove {f}: {fe}")
            except Exception as fe:
                logger.debug(f"Failed forced sidecar cleanup: {fe}")

            # 2. Second, handle junk folders specifically
            # We look for folders named like YTS or YIFY
            for f in root.iterdir():
                try:
                    if f.is_dir():
                        name_lower = f.name.lower()
                        # Never remove the 'subs' folder
                        if name_lower == 'subs' or name_lower == 'subtitles':
                            continue
                        
                        # If the folder name contains YTS or YIFY and isn't the main movie folder
                        if 'yts' in name_lower or 'yify' in name_lower:
                            # Final safety check: does it contain a movie file?
                            has_movie = any(child.suffix.lower() in movie_extensions for child in f.rglob('*'))
                            if not has_movie:
                                import shutil
                                shutil.rmtree(f)
                                removed_count += 1
                                logger.debug(f"Removed junk folder: {f.name}")
                except Exception as fe:
                    logger.debug(f"Failed to remove {f}: {fe}")
            
            if removed_count > 0:
                logger.info(f"Cleanup finished. Removed {removed_count} junk items from {root.name}")

            # Write our promo file (website name + URL)
            try:
                promo_path = root / PROMO_FILE_NAME
                promo_path.write_text(PROMO_FILE_CONTENT, encoding='utf-8')
            except Exception as e:
                logger.debug(f"Failed to write promo file: {e}")
        except Exception as e:
            logger.warning(f"Failed to run junk file cleanup: {e}")

    def _cleanup_completed_on_start(self):
        """Cleanup junk files for completed downloads on startup."""
        try:
            completed = self.db.get_all_downloads(state=DOWNLOAD_STATE_COMPLETED) or []
            for d in completed:
                if not d or not d.save_path:
                    continue
                gid = str(d.id)
                if gid in self._cleaned_downloads:
                    continue
                target_dir = Path(d.save_path)
                try:
                    self._cleanup_junk_files(str(target_dir))
                    self._cleaned_downloads.add(gid)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Startup cleanup skipped: {e}")

    def stop(self):
        """Stop the poll thread and aria2 process if started by manager."""
        try:
            if hasattr(self, '_stop_event'):
                self._stop_event.set()
            if getattr(self, 'process', None):
                try:
                    self.process.terminate()
                except Exception:
                    pass
        except Exception:
            pass


# Singleton manager
_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = Aria2Manager()
    return _manager












