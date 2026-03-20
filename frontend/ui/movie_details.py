"""Movie Details dialog: title, synopsis, qualities list, and download actions.
This module provides a compact, well-indented implementation of the
MovieDetailsDialog used by the frontend UI.
"""
import logging
import subprocess
import sys
import os
from typing import Optional

import threading

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QTextEdit, QPushButton, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

logger = logging.getLogger(__name__)


class _DetailsFetcher(QThread):
    """Background thread: fetches description + torrents from YTS by URL."""
    done = pyqtSignal(object)   # emits dict or None

    def __init__(self, api, yts_url: str, movie_id: str = '', has_db_movie: bool = False):
        super().__init__()
        self.api = api
        self.yts_url = yts_url
        self.movie_id = movie_id
        self.has_db_movie = has_db_movie

    def run(self):
        result = {}
        # Preferred path: details-by-url endpoint (works for both DB and live movies)
        if self.yts_url:
            for attempt in range(2):  # retry once on failure
                try:
                    import time
                    if attempt > 0:
                        time.sleep(2)
                    data = self.api.get_movie_details_by_url(self.yts_url)
                    if data:
                        result = data
                        break
                except Exception as e:
                    logger.error(f'_DetailsFetcher url fetch attempt {attempt+1} failed: {e}')

        # Fallback: only call fetch-torrents if we know the movie is in the DB
        if not result.get('torrents') and self.has_db_movie and self.movie_id:
            try:
                res = self.api.fetch_movie_torrents(self.movie_id)
                if res and res.get('torrents'):
                    result['torrents'] = res['torrents']
            except Exception as e:
                logger.error(f'_DetailsFetcher torrents fallback failed: {e}')

        self.done.emit(result if result else None)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PyQt6.QtCore import QUrl, QTimer
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False

if WEB_ENGINE_AVAILABLE:
    class InterceptPage(QWebEnginePage):
        def __init__(self, dialog_instance, parent=None):
            super().__init__(parent)
            self.dialog = dialog_instance
            
        def acceptNavigationRequest(self, qurl, nav_type, isMainFrame):
            url_str = qurl.toString()
            orig = self.dialog.original_target
            nav_host = qurl.host().lower()
            
            # 0. DEBUG: Print current destination navigation
            print(f"[AdBrowser] Navigating to: {url_str}")
            
            # 1. ALWAYS ALLOW: If we are on the ad host itself or its partners (captcha/cloudflare), do NOT intercept.
            # This prevents the dialog from closing on the very first URL load because it contains the target URL as a param.
            ad_hosts = ["ouo.io", "ouo.press", "ouo.today", "google.com", "gstatic.com", "cloudflare.com"]
            if any(h in nav_host for h in ad_hosts) or "recaptcha" in url_str:
                return super().acceptNavigationRequest(qurl, nav_type, isMainFrame)
            
            # 2. INTERCEPT: If the navigation is now headed back to yts.bz (the source) or is a torrent/magnet protocol.
            # This means the user has FINISHED the Ouo.io challenge and is being redirected to their file.
            if url_str.startswith("magnet:") or ".torrent" in url_str.lower():
                print(f"[AdBrowser] SUCCESS: Intercepted payload {url_str}")
                self.dialog.final_url = url_str
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self.dialog.accept)
                return False
                
            if orig in url_str or "yts.bz/torrent/download/" in url_str:
                print(f"[AdBrowser] SUCCESS: Intercepted target URL {url_str}")
                self.dialog.final_url = orig # or url_str
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self.dialog.accept)
                return False
                
            return super().acceptNavigationRequest(qurl, nav_type, isMainFrame)

class AdBrowserDialog(QDialog):
    def __init__(self, monetized_url, original_target, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Please complete the step to unlock your download!")
        self.resize(1000, 700)
        self.original_target = original_target
        self.final_url = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if WEB_ENGINE_AVAILABLE:
            from PyQt6.QtCore import QUrl, QTimer
            self.browser = QWebEngineView(self)
            self.page = InterceptPage(self, self.browser)
            self.browser.setPage(self.page)
            
            def on_download(item):
                url_str = item.url().toString()
                item.cancel()
                self.final_url = url_str
                QTimer.singleShot(0, self.accept)
                
            self.browser.page().profile().downloadRequested.connect(on_download)
            self.browser.setUrl(QUrl(monetized_url))
            layout.addWidget(self.browser)
        else:
            self.final_url = original_target
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.accept)


class MovieDetailsDialog(QDialog):
    def __init__(self, movie_data_or_id, api_client, parent=None):
        super().__init__(parent)
        # Accept either a full movie dict (live-scraped) or a plain ID string (DB movie)
        if isinstance(movie_data_or_id, dict):
            self._movie_data = movie_data_or_id
            self.movie_id = movie_data_or_id.get('id', '')
        else:
            self._movie_data = None
            self.movie_id = str(movie_data_or_id)
        self.api = api_client
        self.selected_magnet_link: Optional[str] = None

        self.setWindowTitle("Movie Synopsis")
        self.setMinimumSize(640, 400)
        self.setStyleSheet("QDialog { background-color: #1e1e1e; }")

        self._build_ui()
        self.load_movie()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        self.title_label = QLabel("Movie Synopsis")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Description
        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        self.desc.setStyleSheet(
            "QTextEdit { background-color: #2b2b2b; color: #cccccc; border: 1px solid #3a3a3a; padding: 10px; font-size: 14px; }"
        )
        layout.addWidget(self.desc)

        # Qualities header
        self.qualities_label = QLabel("Available Qualities:")
        self.qualities_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px; font-size: 14px;")
        layout.addWidget(self.qualities_label)

        # Quality list
        self.qualities_list = QListWidget()
        self.qualities_list.setStyleSheet(
            "QListWidget { background-color: #2b2b2b; color: white; border: 1px solid #3a3a3a; font-size: 13px; }"
        )
        self.qualities_list.setMaximumHeight(140)
        layout.addWidget(self.qualities_list)
        self.qualities_list.itemDoubleClicked.connect(self.on_quality_double_clicked)

        # Buttons (modern compact style)
        btn_layout = QHBoxLayout()

        btn_style_primary = "QPushButton { background-color: #0a84ff; color: #ffffff; border: none; padding:10px 14px; border-radius:8px; font-weight:600; } QPushButton:hover { background-color:#066bd6; }"
        btn_style_secondary = "QPushButton { background-color: #2b2b2b; color: #ffffff; border: 1px solid #3a3a3a; padding:10px 14px; border-radius:8px; } QPushButton:hover { background-color:#393939; }"

        self.download_btn = QPushButton("Get Download Link")
        self.download_btn.clicked.connect(self.on_download_clicked)
        self.download_btn.setEnabled(False)
        self.download_btn.setStyleSheet(btn_style_primary)
        btn_layout.addWidget(self.download_btn)

        self.copy_magnet_btn = QPushButton("Copy Ad-Link")
        self.copy_magnet_btn.clicked.connect(self.on_copy_magnet)
        self.copy_magnet_btn.setEnabled(False)
        self.copy_magnet_btn.setStyleSheet(btn_style_secondary)
        btn_layout.addWidget(self.copy_magnet_btn)

        self.download_torrent_btn = QPushButton("Get .torrent Link")
        self.download_torrent_btn.clicked.connect(self.on_download_torrent)
        self.download_torrent_btn.setEnabled(False)
        self.download_torrent_btn.setStyleSheet(btn_style_secondary)
        btn_layout.addWidget(self.download_torrent_btn)

        self.retry_btn = QPushButton("⟳ Retry")
        self.retry_btn.setToolTip("Reload details and download options from YTS")
        self.retry_btn.clicked.connect(self._on_retry_clicked)
        self.retry_btn.setStyleSheet(
            "QPushButton { background:#2b2b2b; color:#aaa; border:1px solid #555; "
            "padding:10px 12px; border-radius:8px; } "
            "QPushButton:hover { background:#3a3a3a; color:#fff; }"
        )
        btn_layout.addWidget(self.retry_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Status and preview
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #0078d4; font-size: 12px; margin-top: 5px;")
        layout.addWidget(self.status_label)

        self.magnet_preview_label = QLabel("")
        self.magnet_preview_label.setStyleSheet(
            "color: #cccccc; font-size: 11px; background-color: #2b2b2b; padding: 6px; border: 1px solid #3a3a3a; font-family: monospace;"
        )
        self.magnet_preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.magnet_preview_label.setWordWrap(True)
        layout.addWidget(self.magnet_preview_label)

        # Connect
        self.qualities_list.itemSelectionChanged.connect(self.on_selection_changed)

    def load_movie(self):
        """Show available data immediately, then fetch description+torrents in background."""
        # ── Step 1: DB lookup (instant) ──────────────────────────────────────
        db_movie = None
        try:
            db_movie = self.api.get_movie(self.movie_id)
        except Exception:
            pass

        movie = db_movie or (dict(self._movie_data) if self._movie_data else None)

        if not movie:
            self.title_label.setText("Movie not found")
            self.desc.setPlainText("")
            self.qualities_list.clear()
            return

        title = movie.get("title", "Unknown")
        year  = movie.get("year", "N/A")
        self.title_label.setText(f"{title} ({year})")

        genres_raw = movie.get("genres") or movie.get("genre") or []
        if isinstance(genres_raw, str):
            genres_list = [g.strip() for g in genres_raw.split(",") if g.strip()]
        else:
            genres_list = list(genres_raw) if genres_raw else []
        genres_clean = [g for g in genres_list if g and g.lower() != "unknown"]
        genres_text  = " / ".join(genres_clean) if genres_clean else "N/A"
        self._genres_clean = genres_clean  # saved for Retry

        # ── Step 2: Show what we have NOW so the dialog is never blank ───────
        existing_desc     = movie.get("description") or ""
        existing_torrents = movie.get("torrents") or []

        self.desc.setPlainText(
            f"Genres: {genres_text}\n\n" +
            (existing_desc if existing_desc else "Fetching description…")
        )

        if existing_torrents:
            self._populate_torrents(existing_torrents)
        else:
            self.qualities_list.clear()
            self.qualities_list.addItem("Loading…")
            self.qualities_label.setText("Available Qualities: fetching…")

        # ── Step 3: Background fetch for missing description/torrents ─────────
        yts_url = movie.get("yts_url") or movie.get("url") or ""
        self._yts_url = yts_url  # saved for Retry button
        needs_fetch = (not existing_desc or not existing_torrents) and (
            yts_url or (db_movie and self.movie_id)
        )
        if needs_fetch:
            self.status_label.setText("Fetching details from YTS…")
            self.status_label.setStyleSheet("color: #0078d4;")
            fetcher = _DetailsFetcher(
                self.api,
                yts_url,
                movie_id=self.movie_id,
                has_db_movie=bool(db_movie),
            )
            fetcher.done.connect(
                lambda data, gc=genres_clean[:]: self._on_details_fetched(data, gc)
            )
            fetcher.finished.connect(fetcher.deleteLater)
            fetcher.start()
            self._fetcher = fetcher   # prevent GC

    def _on_details_fetched(self, data, genres_clean: list):
        """Main-thread callback when background fetch finishes."""
        try:
            if not data:
                self.status_label.setText("Could not load details — click ⟳ Retry")
                self.status_label.setStyleSheet("color: #ff8800;")
                lw = self.qualities_list
                if lw.count() == 1 and lw.item(0).text() in ("Loading…", "No quality options available"):
                    lw.clear()
                    lw.addItem("No quality options available — click ⟳ Retry")
                    self.qualities_label.setText("Available Qualities: None")
                return

            desc     = data.get("description") or ""
            torrents = data.get("torrents") or []

            if data.get("genres") and not genres_clean:
                genres_clean = data["genres"]
            genres_text = " / ".join(genres_clean) if genres_clean else "N/A"

            if desc:
                self.desc.setPlainText(f"Genres: {genres_text}\n\n{desc}")

            if torrents:
                self._populate_torrents(torrents)
            else:
                lw = self.qualities_list
                if lw.count() == 1 and lw.item(0).text() in ("Loading…",):
                    lw.clear()
                    lw.addItem("No quality options available — click ⟳ Retry")
                    self.qualities_label.setText("Available Qualities: None")
                    self.status_label.setText("No download links on YTS yet — click ⟳ Retry")
                    self.status_label.setStyleSheet("color: #ff8800;")
                    return

            self.status_label.setText("")
        except RuntimeError:
            pass  # Dialog closed before callback arrived

    def _on_retry_clicked(self):
        """Re-trigger background fetch for description + torrents."""
        try:
            yts_url = getattr(self, '_yts_url', '') or ''
            if not yts_url:
                self.status_label.setText("No YTS URL available to retry")
                self.status_label.setStyleSheet("color: #ff4444;")
                return
            self.status_label.setText("Retrying…")
            self.status_label.setStyleSheet("color: #0078d4;")
            self.qualities_list.clear()
            self.qualities_list.addItem("Loading…")
            self.qualities_label.setText("Available Qualities: fetching…")
            genres_clean = getattr(self, '_genres_clean', [])
            fetcher = _DetailsFetcher(
                self.api, yts_url,
                movie_id=self.movie_id,
                has_db_movie=False
            )
            fetcher.done.connect(
                lambda data, gc=genres_clean[:]: self._on_details_fetched(data, gc)
            )
            fetcher.finished.connect(fetcher.deleteLater)
            fetcher.start()
            self._fetcher = fetcher
        except Exception as e:
            logger.error(f"Retry failed: {e}")

    def _populate_torrents(self, torrents: list):
        """Fill the quality list widget from a list of torrent dicts."""
        self.qualities_list.clear()
        seen = []
        for t in torrents:
            q = t.get("quality", "Unknown")
            s = t.get("size", "Unknown")
            item = QListWidgetItem(f"{q} - {s}")
            item.setData(Qt.ItemDataRole.UserRole, t)
            self.qualities_list.addItem(item)
            if q not in seen:
                seen.append(q)
        self.qualities_label.setText("Available Qualities: " + ", ".join(seen))
        self.status_label.setText("")

    def on_selection_changed(self):
        has = len(self.qualities_list.selectedItems()) > 0
        self.download_btn.setEnabled(has)
        self.copy_magnet_btn.setEnabled(has)
        item = self.qualities_list.currentItem()
        if not item:
            self.selected_magnet_link = None
            self.download_torrent_btn.setEnabled(False)
            self.magnet_preview_label.setText("")
            return

        torrent = item.data(Qt.ItemDataRole.UserRole) or {}
        magnet = torrent.get("magnet_link")
        self.selected_magnet_link = str(magnet) if magnet else None
        self.download_torrent_btn.setEnabled(bool(torrent.get("torrent_url") or torrent.get("url")))
        
        # Avoid slicing which triggers weird linter error
        mag_str = str(self.selected_magnet_link) if self.selected_magnet_link else ""
        if len(mag_str) > 80:
            display = mag_str[0:80] + "..."
        else:
            display = mag_str
        self.magnet_preview_label.setText(display)

    def on_quality_double_clicked(self, item: QListWidgetItem):
        self.on_download_clicked()

    def _open_with_system(self, target: str):
        # Clean target: remove surrounding whitespace and any stray newlines
        if not target:
            raise ValueError('Empty target')
        clean_target = target.strip().replace('\r', '').replace('\n', '')

        if sys.platform == 'win32':
            # For magnet links, try creating a .magnet file first (most reliable method)
            if clean_target.startswith('magnet:'):
                try:
                    import tempfile
                    # Create a .magnet file - this is the most reliable way on Windows
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.magnet', mode='w', encoding='utf-8')
                    tmp.write(clean_target)
                    tmp.close()
                    logger.debug(f"Created temporary magnet file: {tmp.name}")
                    os.startfile(tmp.name)
                    logger.info(f"Successfully opened magnet via .magnet file")
                    return
                except Exception as e:
                    logger.warning(f".magnet file method failed: {e}, trying direct methods")
            
            # For non-magnet or if .magnet failed, try os.startfile
            try:
                logger.debug(f"Opening target via os.startfile: {clean_target[:100]}...")
                os.startfile(clean_target)
                return
            except Exception as e:
                logger.warning(f"os.startfile failed: {e}; falling back to cmd start")
                # Fallback to cmd start with proper quoting
                try:
                    # Use PowerShell Start-Process for better handling
                    cmd = ['powershell', '-Command', f'Start-Process "{clean_target}"']
                    subprocess.Popen(cmd, shell=False)
                    return
                except Exception as e2:
                    logger.error(f"PowerShell fallback failed: {e2}")
                    raise
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', clean_target])
        else:
            subprocess.Popen(['xdg-open', clean_target])

    def _generate_ouo_link(self, target_url: str) -> str:
        """Background API fetch to generate an Ouo.io short link."""
        if not target_url:
            return target_url
            
        from urllib.parse import quote
        
        # User's Ouo.io API Key
        API_KEY = "k1e6VX2P" 
        
        # Ouo.io requires fully encoded URLs
        encoded_url = quote(target_url, safe='')
        
        # Notice we use HTTPS to bypass Cloudflare API blocking
        api_url = f"https://ouo.io/api/{API_KEY}?s={encoded_url}"
        
        try:
            import requests
            # Fast timeout so the UI doesn't hang long
            response = requests.get(api_url, timeout=5)
            # Ouo.io API returns plain text, e.g., "https://ouo.io/abcd"
            result = response.text.strip()
            
            if result.startswith("http"):
                return result
        except Exception as e:
            logger.error(f"Failed to generate Ouo link: {e}")
            
        # Fallback to the Quick Link format if the API request failed above
        return f"https://ouo.io/qs/{API_KEY}?s={encoded_url}"

    def _start_backend_download_with_url(self, target_url, quality):
        movie_title = self.title_label.text().replace(" Synopsis", "")
        safe_title = "".join(c for c in movie_title if c.isalnum() or c in (' ', '-', '_')).strip()
        
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings('yts-monitor', 'yts-movie-monitor')
            organize = settings.value('organize_by_genre', True, type=bool)
        except Exception:
            organize = True
            
        genres_arg = getattr(self, '_genres_clean', []) or []
        
        try:
            if target_url.startswith("magnet:"):
                self.status_label.setText("Sending magnet to aria2...")
                self.status_label.setStyleSheet("color: #4CAF50;")
                download_id = self.api.start_download(self.movie_id, movie_title, quality, target_url, organize_by_genre=organize, genres=genres_arg)
            else:
                self.status_label.setText(f"Downloading .torrent file for {quality}...")
                self.status_label.setStyleSheet("color: #0078d4;")
                import requests
                from pathlib import Path
                response = requests.get(target_url, timeout=10)
                response.raise_for_status()
                torrent_filename = f"{safe_title} [{quality}].torrent"
                downloads_dir = Path.home() / "Downloads"
                torrent_path = downloads_dir / torrent_filename
                torrent_path.write_bytes(response.content)
                self.status_label.setText("✓ .torrent saved, sending to download manager...")
                self.status_label.setStyleSheet("color: #4CAF50;")
                download_id = self.api.start_download(self.movie_id, movie_title, quality, str(torrent_path), organize_by_genre=organize, genres=genres_arg)
                
                try:
                    remove_after = settings.value('remove_torrent_after_send', False, type=bool)
                    if remove_after:
                        torrent_path.unlink()
                except:
                    pass
                    
            if download_id:
                self.status_label.setText(f"✓ Download queued with aria2: {quality}")
                self.status_label.setStyleSheet("color: #4CAF50;")
                parent = self.parent()
                if hasattr(parent, 'download_manager'):
                    parent.download_manager.refresh_downloads()
                    try:
                        if not parent.download_manager.refresh_timer.isActive():
                            parent.download_manager.refresh_timer.start()
                    except:
                        pass
                if hasattr(parent, 'mark_movie_downloaded'):
                    parent.mark_movie_downloaded(self.movie_id)
        except Exception as e:
            logger.error(f"Download request failed: {e}")
            self.status_label.setText(f"✗ Download failed: {str(e)[:50]}")
            self.status_label.setStyleSheet("color: #f44336;")

    def on_download_clicked(self):
        """Monetized Flow: Opens internal AdBrowserDialog and automatically downloads via aria2 on completion."""
        item = self.qualities_list.currentItem()
        if not item:
            self.status_label.setText("Please select a quality first")
            self.status_label.setStyleSheet("color: #ff4444;")
            return
        
        torrent = item.data(Qt.ItemDataRole.UserRole) or {}
        quality = torrent.get("quality", "Unknown")
        torrent_url = torrent.get('torrent_url') or torrent.get('url')
        magnet = torrent.get("magnet_link", "")
        
        target_link = torrent_url if torrent_url else magnet
        if not target_link:
            self.status_label.setText("No download link available for this quality")
            self.status_label.setStyleSheet("color: #ff4444;")
            return

        self.status_label.setText("Preparing download link...")
        self.status_label.setStyleSheet("color: #0078d4;")
        QApplication.processEvents()

        monetized_link = self._generate_ouo_link(target_link)
        
        # Open internal browser!
        self.status_label.setText("Please wait... unlocking download.")
        dialog = AdBrowserDialog(monetized_link, target_link, self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted and dialog.final_url:
            self.status_label.setText("✓ Ad completed! Starting download...")
            QApplication.processEvents()
            self._start_backend_download_with_url(dialog.final_url, quality)
        else:
            self.status_label.setText("Ad challenge was closed or incomplete.")
            self.status_label.setStyleSheet("color: #ff8800;")

    def on_copy_magnet(self):
        magnet = self.selected_magnet_link
        if not magnet:
            self.status_label.setText("No magnet link available")
            self.status_label.setStyleSheet("color: #ff4444;")
            return
            
        monetized_link = self._generate_ouo_link(magnet)
        QApplication.clipboard().setText(monetized_link)
        self.status_label.setText("Copied monetized link")

    def on_open_magnet(self):
        self.on_download_clicked()

    def on_download_torrent(self):
        self.on_download_clicked()
    
    def on_refresh_torrents(self):
        """Fetch fresh torrent data from YTS website"""
        self.status_label.setText("Fetching fresh torrents from YTS...")
        self.status_label.setStyleSheet("color: #0078d4;")
        # refresh button removed from UI; just show status
        
        try:
            logger.info(f"Refreshing torrents for movie {self.movie_id}")
            result = self.api.fetch_movie_torrents(self.movie_id)
            
            if not result:
                self.status_label.setText("Failed to fetch torrents from YTS")
                self.status_label.setStyleSheet("color: #ff4444;")
                return
            
            torrents = result.get('torrents', [])
            
            if not torrents:
                self.status_label.setText("No torrents found on YTS")
                self.status_label.setStyleSheet("color: #ff8800;")
                return
            
            # Update the qualities list
            self.qualities_list.clear()
            seen = []
            for t in torrents:
                q = t.get("quality", "Unknown")
                s = t.get("size", "Unknown")
                item = QListWidgetItem(f"{q} - {s}")
                item.setData(Qt.ItemDataRole.UserRole, t)
                self.qualities_list.addItem(item)
                if q not in seen:
                    seen.append(q)
            
            self.qualities_label.setText("Available Qualities: " + ", ".join(seen))
            self.status_label.setText(f"✓ Loaded {len(torrents)} torrents from YTS")
            self.status_label.setStyleSheet("color: #00ff00;")
            logger.info(f"Successfully refreshed {len(torrents)} torrents")
            
        except Exception as e:
            logger.error(f"Error refreshing torrents: {e}")
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: #ff4444;")
        finally:
            # nothing to re-enable; just return
            pass

