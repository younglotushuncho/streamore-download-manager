"""Write the movie_details.py file"""

content = '''"""Minimal Movie Details Dialog
Shows only: title, synopsis (description), and available qualities with sizes.
Clicking a quality downloads via magnet link.
"""
import logging
import subprocess
import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QTextEdit, QPushButton, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class MovieDetailsDialog(QDialog):
    """Dialog showing movie title, synopsis, and a list of available qualities and sizes."""

    def __init__(self, movie_id: str, api_client, parent=None):
        super().__init__(parent)
        self.movie_id = movie_id
        self.api = api_client

        # Currently selected magnet link (set when user selects a quality)
        self.selected_magnet_link: Optional[str] = None

        self.setWindowTitle("Movie Synopsis")
        self.setMinimumSize(640, 400)

        # Apply dark theme to dialog
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
        """)

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
        self.desc.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #cccccc;
                border: 1px solid #3a3a3a;
                padding: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.desc)

        # Qualities header
        self.qualities_label = QLabel("Available Qualities:")
        self.qualities_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px; font-size: 14px;")
        layout.addWidget(self.qualities_label)

        # Quality list
        self.qualities_list = QListWidget()
        self.qualities_list.setStyleSheet("""
            QListWidget { background-color: #2b2b2b; color: white; border: 1px solid #3a3a3a; font-size: 13px; }
            QListWidget::item { padding: 5px; }
            QListWidget::item:hover { background-color: #3a3a3a; }
            QListWidget::item:selected { background-color: #0078d4; }
        """)
        self.qualities_list.setMaximumHeight(140)
        layout.addWidget(self.qualities_list)

        # Double-click to download
        self.qualities_list.itemDoubleClicked.connect(self.on_quality_double_clicked)

        # Buttons
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton("Download Selected")
        self.download_btn.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: white; border: none; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #1084d8; }
            QPushButton:disabled { background-color: #3a3a3a; color: #666666; }
        """)
        self.download_btn.clicked.connect(self.on_download_clicked)
        self.download_btn.setEnabled(False)
        btn_layout.addWidget(self.download_btn)

        self.copy_magnet_btn = QPushButton("Copy Magnet Link")
        self.copy_magnet_btn.setStyleSheet("""
            QPushButton { background-color: #2b2b2b; color: white; border: 1px solid #0078d4; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:disabled { background-color: #2b2b2b; color: #666666; border: 1px solid #3a3a3a; }
        """)
        self.copy_magnet_btn.clicked.connect(self.on_copy_magnet)
        self.copy_magnet_btn.setEnabled(False)
        btn_layout.addWidget(self.copy_magnet_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #0078d4; font-size: 12px; margin-top: 5px;")
        layout.addWidget(self.status_label)

        # Magnet link preview
        self.magnet_preview_label = QLabel("")
        self.magnet_preview_label.setStyleSheet("color: #cccccc; font-size: 11px; background-color: #2b2b2b; padding: 6px; border: 1px solid #3a3a3a; font-family: monospace;")
        self.magnet_preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.magnet_preview_label.setWordWrap(True)
        layout.addWidget(self.magnet_preview_label)

        # Connect selection change
        self.qualities_list.itemSelectionChanged.connect(self.on_selection_changed)

    def load_movie(self):
        """Fetch movie data from API client and populate the UI."""
        try:
            movie = self.api.get_movie(self.movie_id)
        except Exception as exc:
            logger.exception("Failed to fetch movie: %s", exc)
            movie = None

        if not movie:
            self.title_label.setText("Movie not found")
            self.desc.setPlainText("")
            self.qualities_label.setText("")
            self.qualities_list.clear()
            return

        title = movie.get("title", "Unknown")
        self.title_label.setText(f"{title} Synopsis")

        description = movie.get("description", "No description available.")
        self.desc.setPlainText(description)

        self.qualities_list.clear()
        torrents = movie.get("torrents", []) or []

        if not torrents:
            self.qualities_list.addItem("No quality options available")
            self.qualities_label.setText("Available Qualities: None")
            return

        seen_qualities = []
        for torrent in torrents:
            quality = torrent.get("quality", "Unknown")
            size = torrent.get("size", "Unknown")

            item = QListWidgetItem(f"{quality} - {size}")
            item.setData(Qt.ItemDataRole.UserRole, torrent)
            self.qualities_list.addItem(item)

            if quality not in seen_qualities:
                seen_qualities.append(quality)

        qualities_text = ", ".join(seen_qualities) if seen_qualities else "N/A"
        self.qualities_label.setText(f"Available Qualities: {qualities_text}")

    def on_selection_changed(self):
        """Enable/disable buttons based on selection"""
        has_selection = len(self.qualities_list.selectedItems()) > 0
        self.download_btn.setEnabled(has_selection)
        self.copy_magnet_btn.setEnabled(has_selection)

        item = self.qualities_list.currentItem()
        if item:
            torrent = item.data(Qt.ItemDataRole.UserRole)
            if torrent:
                self.selected_magnet_link = torrent.get("magnet_link")
                self.download_btn.setToolTip(self.selected_magnet_link or "")
                self.copy_magnet_btn.setToolTip(self.selected_magnet_link or "")
                display = (self.selected_magnet_link[:80] + "...") if self.selected_magnet_link and len(self.selected_magnet_link) > 80 else (self.selected_magnet_link or "")
                self.magnet_preview_label.setText(display)
                self.magnet_preview_label.setToolTip(self.selected_magnet_link or "")
            else:
                self.selected_magnet_link = None
                self.download_btn.setToolTip("")
                self.copy_magnet_btn.setToolTip("")
                self.magnet_preview_label.setText("")
                self.magnet_preview_label.setToolTip("")
        else:
            self.selected_magnet_link = None
            self.download_btn.setToolTip("")
            self.copy_magnet_btn.setToolTip("")
            self.magnet_preview_label.setText("")
            self.magnet_preview_label.setToolTip("")

    def on_quality_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on quality item"""
        self.on_download_clicked()

    def on_download_clicked(self):
        """Start download using magnet link"""
        magnet_link = self.selected_magnet_link
        quality = "Unknown"

        item = self.qualities_list.currentItem()
        if item:
            torrent = item.data(Qt.ItemDataRole.UserRole)
            if torrent:
                quality = torrent.get("quality", "Unknown")
                if not magnet_link:
                    magnet_link = torrent.get("magnet_link", "")

        if not magnet_link:
            self.status_label.setText("No magnet link available")
            self.status_label.setStyleSheet("color: #ff4444; font-size: 12px; margin-top: 5px;")
            return

        try:
            if sys.platform == 'win32':
                subprocess.Popen(['start', magnet_link], shell=True)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', magnet_link])
            else:
                subprocess.Popen(['xdg-open', magnet_link])

            self.status_label.setText(f"Started download: {quality}")
            self.status_label.setStyleSheet("color: #0078d4; font-size: 12px; margin-top: 5px;")
            logger.info(f"Started download: {quality} - {magnet_link[:50]}...")

            try:
                movie_title = self.title_label.text().replace(" Synopsis", "")
                try:
                    from PyQt6.QtCore import QSettings
                    settings = QSettings('yts-monitor', 'yts-movie-monitor')
                    organize = settings.value('organize_by_genre', True, type=bool)
                except Exception:
                    organize = True
                # No local genres available in this context; pass empty list
                self.api.start_download(self.movie_id, movie_title, quality, magnet_link, organize_by_genre=organize, genres=[])
            except Exception as e:
                logger.warning(f"Failed to notify API about download: {e}")

        except Exception as e:
            logger.error(f"Failed to start download: {e}")
            self.status_label.setText(f"Failed to start download: {str(e)}")
            self.status_label.setStyleSheet("color: #ff4444; font-size: 12px; margin-top: 5px;")
            
            QMessageBox.warning(
                self,
                "Download Error",
                f"Could not open magnet link.\\n\\nMake sure you have a torrent client installed.\\n\\nError: {str(e)}"
            )

    def on_copy_magnet(self):
        """Copy magnet link to clipboard"""
        magnet_link = self.selected_magnet_link
        quality = "Unknown"

        item = self.qualities_list.currentItem()
        if item:
            torrent = item.data(Qt.ItemDataRole.UserRole)
            if torrent:
                quality = torrent.get("quality", "Unknown")
                if not magnet_link:
                    magnet_link = torrent.get("magnet_link", "")

        if not magnet_link:
            self.status_label.setText("No magnet link available")
            self.status_label.setStyleSheet("color: #ff4444; font-size: 12px; margin-top: 5px;")
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(magnet_link)
        
        self.status_label.setText(f"Copied magnet link for {quality}")
        self.status_label.setStyleSheet("color: #0078d4; font-size: 12px; margin-top: 5px;")
        logger.info(f"Copied magnet link: {quality}")
'''

with open('frontend/ui/movie_details.py', 'w', encoding='utf-8') as f:
    f.write(content)
    
print("File written successfully!")
