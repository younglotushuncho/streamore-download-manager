"""backend/torrent_manager.py

Libtorrent-based TorrentManager focusing on DHT startup and routers.

This is a compact, self-contained implementation that:
- creates a libtorrent session with DHT enabled
- adds standard DHT routers
- starts a background alerts loop
- exposes add/pause/resume/cancel/get_status/get_all_downloads

If `libtorrent` is not installed OR if lt.session() crashes (known issue on
some Windows builds due to MSVCP140 ABI), the manager is gracefully disabled
and logs a warning.  Downloads will fall back to aria2.

HOW TO FIX LIBTORRENT ON WINDOWS (if it crashes at startup):
  1. Install Miniconda: https://docs.conda.io/en/latest/miniconda.html
  2. conda create -n streamore python=3.12
  3. conda activate streamore
  4. conda install -c conda-forge libtorrent
  5. pip install the rest of requirements.txt
  - OR -
  Download the latest Visual C++ Redistributable 2022 x64 and install it:
  https://aka.ms/vs/17/release/vc_redist.x64.exe
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import hashlib
from threading import Thread, Event
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── import libtorrent ──────────────────────────────────────────────────────────
try:
    import libtorrent as lt
    _LT_IMPORTED = True
except Exception as e:
    lt = None
    _LT_IMPORTED = False
    logger.warning(f"libtorrent import failed: {e}")


def _probe_lt_session() -> bool:
    """Run lt.session() in a subprocess to verify it doesn't crash.

    On some Windows systems (CRT ABI mismatch) lt.session() causes a fatal
    access-violation that cannot be caught by Python's try/except.  Running
    the probe in a child process ensures the parent process stays alive.
    Returns True only when the subprocess exits cleanly with output 'ok'.
    """
    if not _LT_IMPORTED:
        return False
    try:
        probe = subprocess.run(
            [sys.executable, '-c',
             'import libtorrent as lt; s = lt.session(); print("ok")'],
            capture_output=True,
            timeout=12,
        )
        ok = probe.returncode == 0 and b'ok' in probe.stdout
        if not ok:
            logger.warning(
                "libtorrent session() crashed in probe subprocess "
                f"(exit={probe.returncode}). TorrentManager disabled.\n"
                "See module docstring for fix instructions."
            )
        return ok
    except subprocess.TimeoutExpired:
        logger.warning("libtorrent session() probe timed out. TorrentManager disabled.")
        return False
    except Exception as exc:
        logger.warning(f"libtorrent probe error: {exc}")
        return False


# Evaluated once at import-time; subsequent instantiations skip the probe.
_LIBTORRENT_OK: bool = _probe_lt_session()


class TorrentManager:
    def __init__(self, download_path: str = 'downloads'):
        self.download_path = os.path.abspath(download_path)
        os.makedirs(self.download_path, exist_ok=True)
        self.session = None
        self.downloads: Dict[str, dict] = {}
        self._alerts_thread: Optional[Thread] = None
        self._alerts_stop = Event()

        if not _LIBTORRENT_OK:
            logger.error('libtorrent not available or crashes on this system; TorrentManager disabled (using aria2 fallback)')
            return

        self.session = self._create_optimized_session()
        self._alerts_thread = Thread(target=self._process_alerts_loop, daemon=True, name='lt-alerts')
        self._alerts_thread.start()

    def _create_optimized_session(self):
        sess = lt.session()

        # Listen on a conventional port range (min_port, max_port)
        try:
            sess.listen_on(6881, 6889)
            logger.info('libtorrent: listening on ports 6881-6889')
        except Exception:
            logger.debug('listen_on may not be supported on this libtorrent build')
            # Some libtorrent builds prefer configuring listen_interfaces
            # via the settings pack. Try a best-effort fallback so the
            # manager attempts to bind the conventional torrent ports.
            try:
                fb = sess.get_settings()
                fb['listen_interfaces'] = '0.0.0.0:6881-6889'
                sess.apply_settings(fb)
                logger.info('libtorrent: applied listen_interfaces fallback 0.0.0.0:6881-6889')
            except Exception:
                logger.debug('listen_interfaces fallback not supported in this libtorrent build')

        # Tune a small set of settings for peer discovery and connectivity
        try:
            s = sess.get_settings()
            s['enable_dht'] = True
            s['enable_lsd'] = True
            s['enable_upnp'] = True
            s['enable_natpmp'] = True
            s['download_rate_limit'] = 0
            s['upload_rate_limit'] = 0
            s['connections_limit'] = 200
            s['connections_limit_per_torrent'] = 50
            s['active_downloads'] = 5
            s['active_seeds'] = 5
            s['request_queue_size'] = 64
            s['max_out_request_queue'] = 500
            s['max_allowed_in_request_queue'] = 500
            s['cache_size'] = 512
            s['announce_to_all_tiers'] = True
            s['announce_to_all_trackers'] = True
            sess.apply_settings(s)
        except Exception:
            logger.debug('failed to apply some session settings (libtorrent variant differences)')

        # Encryption settings (enc_policy/enc_level may not exist in all builds)
        try:
            enc = sess.get_settings()
            enc['in_enc_policy'] = lt.enc_policy.enabled
            enc['out_enc_policy'] = lt.enc_policy.enabled
            enc['allowed_enc_level'] = lt.enc_level.both
            sess.apply_settings(enc)
        except Exception:
            logger.debug('encryption policy settings not available in this libtorrent build')

        # Start DHT and add routers
        try:
            sess.start_dht()
            routers = [
                'router.bittorrent.com:6881',
                'router.utorrent.com:6881',
                'dht.transmissionbt.com:6881',
                'dht.aelitis.com:6881'
            ]
            for r in routers:
                try:
                    sess.add_dht_router(r)
                    logger.info(f'Added DHT router: {r}')
                except Exception:
                    logger.debug(f'Could not add DHT router: {r}')
        except Exception as e:
            logger.warning(f'Could not start DHT: {e}')

        return sess

    def _process_alerts_loop(self):
        while not self._alerts_stop.is_set():
            try:
                alerts = self.session.pop_alerts()
                if not alerts:
                    time.sleep(1)
                    continue

                for a in alerts:
                    name = type(a).__name__
                    try:
                        if name == 'listen_succeeded_alert':
                            ep = getattr(a, 'endpoint', None)
                            logger.info(f'listen succeeded: {ep}')
                        elif name == 'listen_failed_alert':
                            msg = getattr(a, 'message', None) or getattr(a, 'error', None)
                            logger.warning(f'listen failed: {msg}')
                        elif name == 'tracker_reply_alert':
                            tr = getattr(a, 'tracker', None) or getattr(a, 'url', None)
                            logger.info(f'tracker reply from {tr}: {a}')
                        elif name == 'tracker_error_alert':
                            tr = getattr(a, 'tracker', None) or getattr(a, 'url', None)
                            logger.warning(f'tracker error from {tr}: {a}')
                        elif name == 'dht_reply_alert':
                            logger.info(f'DHT reply: {a}')
                        elif name == 'metadata_received_alert':
                            try:
                                h = a.handle
                                nm = None
                                try:
                                    nm = h.name()
                                except Exception:
                                    pass
                                logger.info(f'metadata received for: {nm or getattr(a, "info_hash", None)}')
                            except Exception:
                                logger.info(f'metadata received: {a}')
                        elif name == 'torrent_finished_alert':
                            try:
                                h = a.handle
                                nm = None
                                try:
                                    nm = h.name()
                                except Exception:
                                    pass
                                logger.info(f'torrent finished: {nm or getattr(a, "name", None)}')
                            except Exception:
                                logger.info(f'torrent finished: {a}')
                        else:
                            logger.debug(f'libtorrent alert: {name} - {a}')
                    except Exception:
                        logger.exception('error handling libtorrent alert')

                time.sleep(1)
            except Exception:
                logger.exception('error while polling libtorrent alerts')
                time.sleep(1)

    def _gen_id(self, title: str, quality: str) -> str:
        return hashlib.sha1(f"{title}|{quality}|{time.time()}".encode()).hexdigest()[:16]

    def add_download(self, movie_title: str, magnet_link: str, quality: str = '') -> Optional[str]:
        if not _LIBTORRENT_OK or self.session is None:
            return None
        did = self._gen_id(movie_title, quality)
        try:
            # Preferred API in libtorrent 2.x; falls back to legacy add_magnet_uri
            try:
                atp = lt.parse_magnet_uri(magnet_link)
                atp.save_path = self.download_path
                atp.storage_mode = lt.storage_mode_t.storage_mode_sparse
                handle = self.session.add_torrent(atp)
            except AttributeError:
                # libtorrent 1.x fallback
                params = {
                    'save_path': self.download_path,
                    'storage_mode': lt.storage_mode_t.storage_mode_sparse
                }
                handle = lt.add_magnet_uri(self.session, magnet_link, params)
            # add extra trackers best-effort (enhances peer discovery)
            try:
                self._add_extra_trackers(handle)
            except Exception:
                logger.debug('failed to add extra trackers')
            self.downloads[did] = {
                'id': did,
                'title': movie_title,
                'quality': quality,
                'magnet': magnet_link,
                'handle': handle,
                'status': 'downloading',
                'added_at': time.time()
            }
            Thread(target=self._wait_for_metadata, args=(did,), daemon=True).start()
            return did
        except Exception:
            logger.exception('failed to add magnet')
            return None

    def _wait_for_metadata(self, did: str, timeout: int = 60):
        entry = self.downloads.get(did)
        if not entry:
            return
        h = entry['handle']
        start = time.time()
        received = False
        while time.time() - start < timeout:
            try:
                if hasattr(h, 'has_metadata') and h.has_metadata():
                    received = True
                    logger.info(f'metadata for {did} received')
                    break
            except Exception:
                logger.debug('error while checking metadata availability', exc_info=True)
            time.sleep(1)

        if not received:
            logger.warning(f'metadata not received for {did} within {timeout}s')
            return

        # Allow a short grace period for peers to connect
        time.sleep(4)
        try:
            st = h.status()
            peers = getattr(st, 'num_peers', None) or getattr(st, 'num_peers_total', None)
            seeds = getattr(st, 'num_seeds', None)
            progress = getattr(st, 'progress', 0.0) * 100.0
            logger.info(f'post-metadata: {did} peers={peers} seeds={seeds} progress={progress:.1f}%')
            # record status for UI/backend queries
            entry['status'] = 'downloading'
            entry['last_status'] = {
                'progress': progress,
                'num_peers': peers,
                'num_seeds': seeds,
            }
        except Exception:
            logger.exception('failed to get status after metadata')

    def _add_extra_trackers(self, handle) -> None:
        """Add a short list of public UDP trackers to a torrent handle.

        Each tracker is added with tier 0 to prioritize them. Failures are
        logged but do not raise.
        """
        trackers = [
            'udp://tracker.opentrackr.org:1337/announce',
            'udp://open.stealth.si:80/announce',
            'udp://tracker.torrent.eu.org:451/announce',
            'udp://exodus.desync.com:6969/announce',
            'udp://tracker.moeking.me:6969/announce',
        ]
        for tr in trackers:
            try:
                handle.add_tracker({'url': tr, 'tier': 0})
                logger.info(f'Added tracker {tr}')
            except Exception as e:
                logger.debug(f'Could not add tracker {tr}: {e}')

    def get_status(self, did: str) -> Optional[dict]:
        entry = self.downloads.get(did)
        if not entry:
            return None
        try:
            st = entry['handle'].status()
            progress = getattr(st, 'progress', 0.0) * 100.0
            download_rate = getattr(st, 'download_rate', 0)
            upload_rate = getattr(st, 'upload_rate', 0)
            total_wanted = getattr(st, 'total_wanted', None) or getattr(st, 'total_wanted_done', None)
            total_wanted_done = getattr(st, 'total_wanted_done', None)
            total_upload = getattr(st, 'total_payload_upload', None) or getattr(st, 'total_upload', None)
            state = getattr(st, 'state', None)
            eta = self._calculate_eta(st)
            return {
                'id': did,
                'title': entry.get('title'),
                'quality': entry.get('quality'),
                'status': entry.get('status'),
                'progress': progress,
                'download_rate': download_rate / 1000.0,
                'upload_rate': upload_rate / 1000.0,
                'num_peers': getattr(st, 'num_peers', 0),
                'num_seeds': getattr(st, 'num_seeds', 0),
                'total_download': total_wanted_done,
                'total_wanted': total_wanted,
                'total_upload': total_upload,
                'state': str(state),
                'eta': eta,
            }
        except Exception:
            logger.exception('failed to get status')
            return None

    def _calculate_eta(self, status) -> Optional[str]:
        try:
            remaining = None
            total = getattr(status, 'total_wanted', None)
            done = getattr(status, 'total_wanted_done', None)
            if total is not None and done is not None:
                remaining = max(0, total - done)
            else:
                return None

            dl_rate = getattr(status, 'download_rate', 0)
            if not dl_rate:
                return None
            secs = int(remaining / dl_rate) if dl_rate > 0 else None
            if secs is None:
                return None
            if secs < 60:
                return f"{secs}s"
            mins = secs // 60
            if mins < 60:
                return f"{mins}m"
            hrs = mins // 60
            mins = mins % 60
            return f"{hrs}h {mins}m"
        except Exception:
            return None

    def pause_download(self, did: str) -> bool:
        entry = self.downloads.get(did)
        if not entry:
            return False
        try:
            entry['handle'].pause()
            return True
        except Exception:
            logger.exception('pause failed')
            return False

    def resume_download(self, did: str) -> bool:
        entry = self.downloads.get(did)
        if not entry:
            return False
        try:
            entry['handle'].resume()
            return True
        except Exception:
            logger.exception('resume failed')
            return False

    def cancel_download(self, did: str) -> bool:
        entry = self.downloads.get(did)
        if not entry:
            return False
        try:
            self.session.remove_torrent(entry['handle'])
        except Exception:
            try:
                self.session.remove_torrent(entry['handle'].info_hash())
            except Exception:
                logger.exception('remove failed')
        try:
            del self.downloads[did]
        except KeyError:
            pass
        return True

    def get_all_downloads(self):
        return [self.get_status(d) for d in list(self.downloads.keys())]

    def shutdown(self):
        try:
            self._alerts_stop.set()
            if self._alerts_thread and self._alerts_thread.is_alive():
                self._alerts_thread.join(timeout=2)
        except Exception:
            pass
        try:
            if self.session:
                self.session.pause()
                try:
                    self.session.stop_dht()
                except Exception:
                    pass
        except Exception:
            pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if not _LIBTORRENT_OK:
        print('libtorrent not available or session() crashes on this system.')
        print('See module docstring for fix instructions (Miniconda or VC++ Redist).')
    else:
        tm = TorrentManager()
        print('TorrentManager started. Add a magnet with tm.add_download(...)')
