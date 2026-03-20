"""
Download Manager Widget for YTS Movie Monitor
Displays and manages active downloads with progress bars and controls
"""
import logging
from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QListWidget, QListWidgetItem,
    QSizePolicy, QMessageBox, QMenu
)
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem  # type: ignore
from PyQt6.QtCore import Qt, QTimer, QUrl, QSize  # type: ignore
from PyQt6.QtGui import QFont, QDesktopServices, QIcon  # type: ignore
from PyQt6.QtWidgets import QStyle  # type: ignore
import os
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

# Modern button styles used across the downloads tab
MODERN_BTN_STYLE = """
QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
}
QPushButton:hover { background-color: #1084d8; }
QPushButton:pressed { background-color: #0064b0; }
"""

ICON_BTN_STYLE = """
QPushButton {
    background-color: rgba(255,255,255,0.02);
    color: #dfe7ff;
    border: none;
    border-radius: 6px;
    padding: 4px;
}
QPushButton:hover { background-color: rgba(255,255,255,0.04); }
"""

WHITE_ICON_BTN_STYLE = """
QPushButton {
    background-color: white;
    color: #111;
    border: none;
    border-radius: 6px;
    padding: 4px;
}
QPushButton:hover { background-color: #f0f0f0; }
"""

BLUE_ICON_BTN_STYLE = """
QPushButton {
    background-color: transparent;
    color: #2a6fdb;
    border: none;
    border-radius: 6px;
}
QPushButton:hover { background-color: rgba(42,111,219,0.08); }
"""

RED_ICON_BTN_STYLE = """
QPushButton {
    background-color: transparent;
    color: #ff6b6b;
    border: none;
    border-radius: 6px;
}
QPushButton:hover { background-color: rgba(255,107,107,0.08); }
"""

from PyQt6.QtWidgets import QDialog, QCheckBox, QDialogButtonBox, QVBoxLayout, QLabel, QHBoxLayout  # type: ignore

class DeleteConfirmationDialog(QDialog):
    """Custom dialog for confirming download deletion with optional file removal"""
    def __init__(self, title, message, parent=None):
        super().__init__(parent)  # type: ignore
        self.setWindowTitle(title)
        self.setFixedSize(450, 180)
        self.should_delete_files = False
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Message with icon (simulated with layout)
        msg_layout = QHBoxLayout()
        icon_label = QLabel("⚠️") # Simple emoji icon for now
        icon_label.setStyleSheet("font-size: 32px;")
        msg_layout.addWidget(icon_label)
        
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 13px; color: #ddd;")
        msg_layout.addWidget(lbl, 1) # stretch
        layout.addLayout(msg_layout)
        
        # Checkbox
        self.cb = QCheckBox("Also remove the content files")
        self.cb.setStyleSheet("color: #aaa; margin-left: 45px;")
        layout.addWidget(self.cb)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        buttons.button(QDialogButtonBox.StandardButton.Yes).setText("Remove")
        buttons.button(QDialogButtonBox.StandardButton.No).setText("Cancel")
        
        # Style buttons roughly like the screenshot (light/dark theme dependent)
        buttons.button(QDialogButtonBox.StandardButton.Yes).setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #c9302c; }
        """)
        buttons.button(QDialogButtonBox.StandardButton.No).setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
    def accept(self):
        self.should_delete_files = self.cb.isChecked()
        super().accept()


class DownloadItemWidget(QWidget):
    """Widget representing a single download item with progress and controls"""
    
    def __init__(self, download_data, api_client, parent=None):
        super().__init__(parent)  # type: ignore
        self.download_data = download_data
        self.api = api_client
        self.download_id = download_data.get('id')
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the download item UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        # Left section: Title and info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Title
        title = self.download_data.get('movie_title', 'Unknown')
        quality = self.download_data.get('quality', '')
        title_label = QLabel(f"{title} ({quality})")
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        title_label.setMaximumWidth(300)
        info_layout.addWidget(title_label)
        
        # Status info
        state = (self.download_data.get('state', 'unknown') or '').lower()
        progress = self.download_data.get('progress', 0)
        speed = self.download_data.get('download_rate', 0) / 1024 / 1024  # MB/s
        peers = self.download_data.get('num_peers', 0)
        seeds = self.download_data.get('num_seeds', 0)
        
        status_text = f"State: {state} | {progress:.1f}% | {speed:.2f} MB/s | Peers: {peers} | Seeds: {seeds}"
        self.status_label = QLabel(status_text)
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(progress))
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(f"{progress:.1f}%")
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress_bar.setMinimumWidth(200)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #2b2b2b;
                text-align: center;
                color: white;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #6ac045;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Control buttons
        # Use icon/button styles defined at module level for a modern look
        button_style = MODERN_BTN_STYLE
        
        self.pause_btn = QPushButton("Pause")
        pause_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        self.pause_btn.setIcon(pause_icon)
        self.pause_btn.setIconSize(QSize(16, 16))
        # icon-only button
        self.pause_btn.setText("")
        self.pause_btn.setToolTip("Pause")
        self.pause_btn.setFixedSize(QSize(36, 28))
        # If this item is currently downloading/active, visually highlight controls
        if state in ('downloading', 'active', 'running', 'progressing'):
            self.pause_btn.setStyleSheet(WHITE_ICON_BTN_STYLE)
        else:
            self.pause_btn.setStyleSheet(ICON_BTN_STYLE)
        self.pause_btn.clicked.connect(self.pause_download)
        layout.addWidget(self.pause_btn)
        
        self.resume_btn = QPushButton("Resume")
        resume_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.resume_btn.setIcon(resume_icon)
        self.resume_btn.setIconSize(QSize(16, 16))
        # icon-only button
        self.resume_btn.setText("")
        self.resume_btn.setToolTip("Resume")
        self.resume_btn.setFixedSize(QSize(36, 28))
        if state in ('downloading', 'active', 'running', 'progressing'):
            self.resume_btn.setStyleSheet(WHITE_ICON_BTN_STYLE)
        else:
            self.resume_btn.setStyleSheet(ICON_BTN_STYLE)
        self.resume_btn.clicked.connect(self.resume_download)
        layout.addWidget(self.resume_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        cancel_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        self.cancel_btn.setIcon(cancel_icon)
        self.cancel_btn.setIconSize(QSize(16, 16))
        # icon-only button
        self.cancel_btn.setText("")
        self.cancel_btn.setToolTip("Cancel")
        self.cancel_btn.setFixedSize(QSize(36, 28))
        # cancel stays red to warn user, but use white background if actively downloading
        if state in ('downloading', 'active', 'running', 'progressing'):
            self.cancel_btn.setStyleSheet("""
                QPushButton { background-color: white; color: #ff6b6b; border: none; border-radius: 6px; padding: 4px; }
                QPushButton:hover { background-color: #f0f0f0; }
            """)
        else:
            self.cancel_btn.setStyleSheet(RED_ICON_BTN_STYLE)
        self.cancel_btn.clicked.connect(self.cancel_download)
        layout.addWidget(self.cancel_btn)

        # Link (open folder) button
        self.link_btn = QPushButton("")
        link_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        self.link_btn.setIcon(link_icon)
        self.link_btn.setIconSize(QSize(16, 16))
        self.link_btn.setToolTip("Open folder")
        self.link_btn.setFixedSize(QSize(36, 28))
        if state in ('downloading', 'active', 'running', 'progressing'):
            self.link_btn.setStyleSheet(WHITE_ICON_BTN_STYLE)
        else:
            self.link_btn.setStyleSheet(BLUE_ICON_BTN_STYLE)
        self.link_btn.clicked.connect(self.open_location)
        layout.addWidget(self.link_btn)

        # Remove (trash) button - remove entry (and backend cancel if available)
        self.remove_btn = QPushButton("")
        remove_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        self.remove_btn.setIcon(remove_icon)
        self.remove_btn.setIconSize(QSize(16, 16))
        self.remove_btn.setToolTip("Remove")
        self.remove_btn.setFixedSize(QSize(36, 28))
        self.remove_btn.setStyleSheet(BLUE_ICON_BTN_STYLE)
        self.remove_btn.clicked.connect(self.remove_entry)
        layout.addWidget(self.remove_btn)
        
        self.setLayout(layout)
        
        # Update button states based on download state
        self.update_button_states()
    
    def update_button_states(self):
        """Update button enabled/disabled states based on download state"""
        state = self.download_data.get('state', 'unknown')
        
        if state == 'downloading':
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)
        elif state == 'paused':
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)
        elif state == 'completed':
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.cancel_btn.setText("Remove")
        else:
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(True)
    
    def update_data(self, new_data):
        """Update the widget with new download data"""
        self.download_data = new_data
        
        # Update progress bar
        progress = new_data.get('progress', 0)
        self.progress_bar.setValue(int(progress))
        self.progress_bar.setFormat(f"{progress:.1f}%")
        
        # Update status label
        state = new_data.get('state', 'unknown')
        speed = new_data.get('download_rate', 0) / 1024 / 1024  # MB/s
        peers = new_data.get('num_peers', 0)
        seeds = new_data.get('num_seeds', 0)
        status_text = f"State: {state} | {progress:.1f}% | {speed:.2f} MB/s | Peers: {peers} | Seeds: {seeds}"
        self.status_label.setText(status_text)
        
        # Update button states
        self.update_button_states()
    
    def pause_download(self):
        """Pause this download"""
        try:
            success = self.api.pause_download(self.download_id)
            if success:
                logger.info(f"Paused download: {self.download_id}")
                self.download_data['state'] = 'paused'
                self.update_button_states()
            else:
                logger.error(f"Failed to pause download: {self.download_id}")
                QMessageBox.warning(self, "Error", "Failed to pause download")
        except Exception as e:
            logger.error(f"Error pausing download: {e}")
            QMessageBox.warning(self, "Error", f"Failed to pause download: {str(e)}")
    
    def resume_download(self):
        """Resume this download"""
        try:
            success = self.api.resume_download(self.download_id)
            if success:
                logger.info(f"Resumed download: {self.download_id}")
                self.download_data['state'] = 'downloading'
                self.update_button_states()
            else:
                logger.error(f"Failed to resume download: {self.download_id}")
                QMessageBox.warning(self, "Error", "Failed to resume download")
        except Exception as e:
            logger.error(f"Error resuming download: {e}")
            QMessageBox.warning(self, "Error", f"Failed to resume download: {str(e)}")
    
    def cancel_download(self):
        """Cancel/remove this download"""
        try:
            reply = QMessageBox.question(
                self,
                "Confirm Cancel",
                f"Cancel download: {self.download_data.get('movie_title')}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.api.cancel_download(self.download_id)
                if success:
                    logger.info(f"Cancelled download: {self.download_id}")
                    # Signal the download manager to remove this item. We can't assume
                    # self.parent() is the DownloadManagerWidget, so walk ancestors.
                    manager = None
                    p = self.parent()
                    while p is not None:
                        if hasattr(p, 'remove_download_item'):
                            manager = p
                            break
                        p = p.parent()

                    if manager is not None:
                        manager.remove_download_item(self.download_id)  # type: ignore
                    else:
                        # As a fallback, try to find the widget's top-level window and
                        # search for a child DownloadManagerWidget
                        try:
                            top = self.window()
                            dm = top.findChild(type(self))
                            if dm and hasattr(dm, 'remove_download_item'):
                                dm.remove_download_item(self.download_id)
                        except Exception:
                            logger.warning('Could not locate DownloadManagerWidget to remove item')
                else:
                    logger.error(f"Failed to cancel download: {self.download_id}")
                    QMessageBox.warning(self, "Error", "Failed to cancel download")
        except Exception as e:
            logger.error(f"Error cancelling download: {e}")
            QMessageBox.warning(self, "Error", f"Failed to cancel download: {str(e)}")

    def open_location(self):
        """Open the download folder for this item (no prompts)."""
        try:
            dl = self.api.get_download(self.download_id)
            if not dl:
                QMessageBox.warning(self, 'Open', 'Download info not found')
                return
            save_path = dl.get('save_path') or dl.get('savePath') or ''
            if not save_path:
                QMessageBox.warning(self, 'Open', 'No save path available for this download')
                return
            p = Path(save_path)
            if p.is_dir():
                if os.name == 'nt':
                    os.startfile(str(p))  # type: ignore
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
            else:
                parent = p.parent
                if os.name == 'nt':
                    os.startfile(str(parent))  # type: ignore
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(parent)))
        except Exception:
            logger.exception('Failed to open location')
            QMessageBox.warning(self, 'Open', 'Failed to open location')

    def _safe_remove_path(self, p: Path) -> bool:
        """Attempt to remove a file or directory robustly. Returns True on success."""
        try:
            logger.info(f"Attempting to remove path: {p}")
            if p.is_dir():
                def _onerror(func, path, exc_info):
                    try:
                        os.chmod(path, 0o700)
                        func(path)
                    except Exception:
                        logger.exception(f"Failed retrying remove for {path}")
                shutil.rmtree(p, onerror=_onerror)
            else:
                # file
                os.remove(p)
            logger.info(f"Removed path: {p}")
            return True
        except Exception:
            logger.exception(f"Failed removing path: {p}")
            return False

    def remove_entry(self):
        """Remove the download entry from UI and attempt backend cancel silently."""
        try:
            # Confirmation dialog with "delete files" checkbox
            cb = None
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle('Remove Download')
            msg.setText(f"Remove download: {self.download_data.get('movie_title', '')} ?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            from PyQt6.QtWidgets import QCheckBox  # type: ignore
            cb = QCheckBox('Also delete files from disk')
            msg.setCheckBox(cb)
            resp = msg.exec()
            if resp != QMessageBox.StandardButton.Yes:
                return

            delete_files = cb.isChecked() if cb is not None else False

            try:
                self.api.cancel_download(self.download_id)
            except Exception:
                logger.exception('Failed to cancel backend during remove')

            # If requested, attempt to delete files on disk
            if delete_files:
                try:
                    dl = self.api.get_download(self.download_id)
                    save_path = dl.get('save_path') or dl.get('savePath') or ''
                    if save_path:
                        p = Path(save_path)
                        if p.exists():
                            ok = self._safe_remove_path(p)
                            if not ok:
                                QMessageBox.warning(self, 'Remove', f'Failed to delete files: {p}')
                except Exception:
                    logger.exception('Failed deleting files for download')

            # find manager and remove UI entry
            manager = None
            p = self.parent()
            while p is not None:
                if hasattr(p, 'remove_download_item'):
                    manager = p
                    break
                p = p.parent()  # type: ignore

            if manager is not None:
                manager.remove_download_item(self.download_id)  # type: ignore
            else:
                try:
                    top = self.window()
                    dm = top.findChild(type(self))
                    if dm and hasattr(dm, 'remove_download_item'):
                        dm.remove_download_item(self.download_id)
                except Exception:
                    logger.warning('Could not locate DownloadManagerWidget to remove item')
        except Exception:
            logger.exception('Error removing entry')


class DownloadManagerWidget(QWidget):
    """Main download manager widget"""
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)  # type: ignore
        self.api = api_client
        self.download_widgets = {}  # {download_id: DownloadItemWidget}
        self.auto_refresh_enabled = True
        self.current_filter = 'all'  # all, downloading, seeding, completed, running, stopped
        self.all_downloads = []  # Store all downloads for filtering
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """Setup the download manager UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Downloads Manager")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Control buttons
        # Manual refresh button removed; auto-refresh runs automatically
        
        # Auto-refresh is always enabled; manual toggle and clear button removed
        
        layout.addLayout(header_layout)
        
        # Status filters
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(5, 10, 5, 10)
        filter_layout.setSpacing(10)
        
        filter_label = QLabel("STATUS")
        filter_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        filter_layout.addWidget(filter_label)
        
        # Create filter buttons
        self.filter_buttons = {}
        filters = [
            ('all', '📊 All'),
            ('downloading', '⬇️ Downloading'),
            ('seeding', '⬆️ Seeding'),
            ('completed', '✅ Completed'),
            ('running', '▶️ Running'),
            ('stopped', '⏸️ Stopped'),
            ('error', '❌ Error')
        ]
        
        for filter_id, label_text in filters:
            btn = QPushButton(f"{label_text} (0)")
            btn.setCheckable(True)
            btn.setStyleSheet(self.get_filter_button_style(False))
            btn.clicked.connect(lambda checked, fid=filter_id: self.set_filter(fid))
            self.filter_buttons[filter_id] = btn
            filter_layout.addWidget(btn)
        
        # Set 'all' as default
        self.filter_buttons['all'].setChecked(True)
        self.filter_buttons['all'].setStyleSheet(self.get_filter_button_style(True))
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Modern table view for downloads
        self.downloads_table = QTableWidget()
        self.downloads_table.setColumnCount(10)
        self.downloads_table.setHorizontalHeaderLabels([
            'Title', 'Status', 'Progress', 'DL Speed', 'UL Speed', 'Peers', 'Seeds', 'ETA', 'Size', 'Actions'
        ])
        self.downloads_table.verticalHeader().setVisible(False)
        self.downloads_table.setShowGrid(False)
        self.downloads_table.setStyleSheet("""
            QTableWidget { background-color: #1e1e1e; border: 1px solid #3a3a3a; }
            QHeaderView::section { background-color: #2b2b2b; color: #ddd; padding: 6px; }
            QTableWidget::item:selected { background-color: #2a6fdb; color: white; }
        """)
        # Allow single-row selection so the entire file panel highlights on click
        self.downloads_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.downloads_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.downloads_table.setAlternatingRowColors(True)
        self.downloads_table.setColumnWidth(0, 300)
        self.downloads_table.setColumnWidth(2, 160)
        self.downloads_table.setColumnWidth(9, 200)
        # Enable custom context menu for per-row actions
        self.downloads_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.downloads_table.customContextMenuRequested.connect(self._on_table_context_menu)
        # Double-clicking a row will attempt to play the downloaded file
        self.downloads_table.cellDoubleClicked.connect(self._on_table_cell_double_clicked)
        # Single-click selects/highlights the whole row
        self.downloads_table.cellClicked.connect(self._on_table_cell_clicked)
        layout.addWidget(self.downloads_table)

        # Fallback legacy list (kept for compatibility but hidden)
        self.downloads_list = QListWidget()
        self.downloads_list.setVisible(False)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)

        # track current selected download id
        self._selected_download_id = None
    
    def setup_timer(self):
        """Setup auto-refresh timer"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(2000)  # 2 seconds
        self.refresh_timer.timeout.connect(self.refresh_downloads)
        # Auto-refresh always on
        try:
            self.refresh_timer.start()
            self.status_label.setText("Auto-refresh enabled (every 2s)")
        except Exception:
            logger.exception('Failed to start refresh timer')

    def _on_table_cell_clicked(self, row: int, col: int) -> None:
        """Handle single-click on a table cell: select the whole row and
        mark it as highlighted for the UI."""
        try:
            # select the row visually
            self.downloads_table.selectRow(row)
            # read download id stored in column 0 user role (if present)
            item = self.downloads_table.item(row, 0)
            if item is not None:
                gid = item.data(Qt.ItemDataRole.UserRole)
                self._selected_download_id = gid
                logger.info(f"Selected download row {row} gid={gid}")
        except Exception:
            logger.exception('error selecting table row')
    
    def toggle_auto_refresh(self):
        # Manual toggle removed; auto-refresh is always enabled.
        pass
    
    def get_filter_button_style(self, active=False):
        """Get stylesheet for filter buttons"""
        if active:
            return """
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: 2px solid #0078d4;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #2a2a2a;
                    color: #aaa;
                    border: 1px solid #444;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #333;
                    color: white;
                    border-color: #666;
                }
            """
    
    def set_filter(self, filter_id):
        """Set the active status filter"""
        self.current_filter = filter_id
        
        # Update button styles
        for fid, btn in self.filter_buttons.items():
            is_active = (fid == filter_id)
            btn.setChecked(is_active)
            btn.setStyleSheet(self.get_filter_button_style(is_active))
        
        # Refresh downloads with new filter
        self.apply_filter()
    
    def apply_filter(self):
        """Apply current filter to the visible downloads.

        The UI uses a table view in `refresh_downloads()`. When a filter
        button is pressed we should rebuild the table according to the
        current filter. To avoid duplicating the table population logic,
        call `refresh_downloads()` which already respects
        `self.current_filter`.
        """
        # Keep legacy list cleared, but refresh the main table which
        # uses `self.current_filter` to build rows.
        try:
            self.downloads_list.clear()
            self.download_widgets.clear()
            self.refresh_downloads()
        except Exception:
            logger.exception('apply_filter failed')
    
    def filter_downloads(self, downloads):
        """Filter downloads based on current filter.

        DB state values: queued, downloading, paused, completed, error
        """
        if self.current_filter == 'all':
            return downloads

        filtered = []
        for d in downloads:
            state = d.get('state', '').lower()

            if self.current_filter == 'downloading' and state in ['downloading', 'active', 'queued']:
                filtered.append(d)
            elif self.current_filter == 'seeding' and state == 'seeding':
                filtered.append(d)
            elif self.current_filter == 'completed' and state == 'completed':
                filtered.append(d)
            elif self.current_filter == 'running' and state in ['downloading', 'active', 'queued', 'seeding']:
                filtered.append(d)
            elif self.current_filter == 'stopped' and state in ['paused', 'stopped']:
                filtered.append(d)
            elif self.current_filter == 'error' and state == 'error':
                filtered.append(d)

        return filtered
    
    def update_filter_counts(self, downloads):
        """Update the count badges on filter buttons"""
        # Count downloads by status
        counts = {
            'all': len(downloads),
            'downloading': 0,
            'seeding': 0,
            'completed': 0,
            'running': 0,
            'stopped': 0,
            'error': 0
        }
        
        for d in downloads:
            state = d.get('state', '').lower()

            if state in ['downloading', 'active', 'queued']:
                counts['downloading'] += 1
                counts['running'] += 1
            elif state == 'seeding':
                counts['seeding'] += 1
                counts['running'] += 1
            elif state == 'completed':
                counts['completed'] += 1
            elif state in ['paused', 'stopped']:
                counts['stopped'] += 1
            elif state == 'error':
                counts['error'] += 1
        
        # Update button labels
        labels = {
            'all': '📊 All',
            'downloading': '⬇️ Downloading',
            'seeding': '⬆️ Seeding',
            'completed': '✅ Completed',
            'running': '▶️ Running',
            'stopped': '⏸️ Stopped',
            'error': '❌ Error'
        }
        
        for fid, btn in self.filter_buttons.items():
            btn.setText(f"{labels[fid]} ({counts[fid]})")
    
    def refresh_downloads(self):
        """Fetch downloads from backend and update UI"""
        try:
            downloads = self.api.get_downloads()
            
            is_stale = False
            if downloads is None:
                if self.all_downloads:
                    downloads = self.all_downloads
                    is_stale = True
                    logger.debug("API returned None, using stale download data")
                else:
                    downloads = []
                    is_stale = True
                    self.status_label.setText("❌ Offline (Backend unreachable)")
                    logger.debug("Failed to fetch downloads from API and no cache available")
            
            # Store all downloads for filtering
            self.all_downloads = downloads
            
            # Update filter counts
            self.update_filter_counts(downloads)
            
            if not downloads:
                # No downloads
                self.downloads_list.clear()
                self.download_widgets.clear()
                
                # Show empty state
                empty_item = QListWidgetItem()
                empty_widget = QWidget()
                empty_layout = QVBoxLayout()
                empty_layout.setContentsMargins(20, 40, 20, 40)
                
                empty_label = QLabel("No active downloads")
                empty_label.setStyleSheet("color: #666; font-size: 14px;")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(empty_label)
                
                hint_label = QLabel("Click Download on any movie to start")
                hint_label.setStyleSheet("color: #555; font-size: 12px;")
                hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(hint_label)
                
                empty_widget.setLayout(empty_layout)
                empty_item.setSizeHint(empty_widget.sizeHint())
                
                self.downloads_list.addItem(empty_item)
                self.downloads_list.setItemWidget(empty_item, empty_widget)
                
                self.status_label.setText(f"No downloads (refreshed: {self._get_time()})")
                return
            
            # Apply current filter and populate table
            filtered_downloads = self.filter_downloads(downloads)

            # Build table rows
            self.downloads_table.setRowCount(len(filtered_downloads))
            for row, d in enumerate(filtered_downloads):
                # Title
                title = f"{d.get('movie_title','Unknown')} ({d.get('quality','')})"
                title_item = QTableWidgetItem(title)
                # store gid for easy lookup from UI interactions
                title_item.setData(Qt.ItemDataRole.UserRole, d.get('id'))
                self.downloads_table.setItem(row, 0, title_item)

                # Status
                state = d.get('state', 'unknown')
                self.downloads_table.setItem(row, 1, QTableWidgetItem(state))

                # Progress (use progress bar widget)
                progress = float(d.get('progress', 0))
                pb = QProgressBar()
                pb.setRange(0, 100)
                pb.setValue(int(progress))
                pb.setFormat(f"{progress:.1f}%")
                pb.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #555;
                        border-radius: 4px;
                        background-color: #2b2b2b;
                        text-align: center;
                        color: white;
                        height: 22px;
                    }
                    QProgressBar::chunk {
                        background-color: #6ac045;
                        border-radius: 3px;
                    }
                """)
                self.downloads_table.setCellWidget(row, 2, pb)

                # DL / UL speeds
                dl = int(d.get('download_rate', 0))
                ul = int(d.get('upload_rate', 0))
                self.downloads_table.setItem(row, 3, QTableWidgetItem(self._format_speed(dl)))
                self.downloads_table.setItem(row, 4, QTableWidgetItem(self._format_speed(ul)))

                # Peers / Seeds
                peers = str(d.get('num_peers', 0))
                seeds = str(d.get('num_seeds', 0))
                self.downloads_table.setItem(row, 5, QTableWidgetItem(peers))
                self.downloads_table.setItem(row, 6, QTableWidgetItem(seeds))

                # ETA
                eta = d.get('eta')
                try:
                    eta_text = self._format_eta(int(eta)) if eta is not None else '--'
                except Exception:
                    eta_text = '--'
                self.downloads_table.setItem(row, 7, QTableWidgetItem(eta_text))

                # Size
                size = int(d.get('size_total', 0))
                self.downloads_table.setItem(row, 8, QTableWidgetItem(self._format_size(size)))

                # Actions (Pause/Resume/Cancel)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout()
                actions_layout.setContentsMargins(0, 0, 0, 0)
                actions_layout.setSpacing(6)
                pause_btn = QPushButton('Pause')
                pause_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
                pause_btn.setIcon(pause_icon)
                pause_btn.setIconSize(QSize(14, 14))
                pause_btn.setText("")
                pause_btn.setToolTip('Pause')
                pause_btn.setFixedSize(QSize(28, 28))
                dstate = (d.get('state') or '').lower()
                if dstate in ('downloading', 'active', 'running', 'progressing'):
                    pause_btn.setStyleSheet(WHITE_ICON_BTN_STYLE)
                else:
                    pause_btn.setStyleSheet(ICON_BTN_STYLE)
                resume_btn = QPushButton('Resume')
                resume_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                resume_btn.setIcon(resume_icon)
                resume_btn.setIconSize(QSize(14, 14))
                resume_btn.setText("")
                resume_btn.setToolTip('Resume')
                resume_btn.setFixedSize(QSize(28, 28))
                if dstate in ('downloading', 'active', 'running', 'progressing'):
                    resume_btn.setStyleSheet(WHITE_ICON_BTN_STYLE)
                else:
                    resume_btn.setStyleSheet(ICON_BTN_STYLE)
                cancel_btn = QPushButton('Cancel')
                cancel_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
                cancel_btn.setIcon(cancel_icon)
                cancel_btn.setIconSize(QSize(14, 14))
                cancel_btn.setText("")
                cancel_btn.setToolTip('Cancel')
                cancel_btn.setFixedSize(QSize(28, 28))
                if dstate in ('downloading', 'active', 'running', 'progressing'):
                    cancel_btn.setStyleSheet("""
                        QPushButton { background-color: white; color: #ff6b6b; border: none; border-radius: 6px; padding: 4px; }
                        QPushButton:hover { background-color: #f0f0f0; }
                    """)
                else:
                    cancel_btn.setStyleSheet(RED_ICON_BTN_STYLE)
                # link / open folder
                link_btn = QPushButton('')
                link_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
                link_btn.setIcon(link_icon)
                link_btn.setIconSize(QSize(14, 14))
                link_btn.setToolTip('Open folder')
                link_btn.setFixedSize(QSize(28, 28))
                link_btn.setProperty('gid', d.get('id'))
                link_btn.setStyleSheet(BLUE_ICON_BTN_STYLE)
                link_btn.clicked.connect(lambda _, b=link_btn: self._open_link_from_btn(b))
                actions_layout.addWidget(link_btn)

                # remove (trash)
                remove_btn = QPushButton('')
                remove_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
                remove_btn.setIcon(remove_icon)
                remove_btn.setIconSize(QSize(14, 14))
                remove_btn.setToolTip('Remove')
                remove_btn.setFixedSize(QSize(28, 28))
                remove_btn.setProperty('gid', d.get('id'))
                remove_btn.setStyleSheet(BLUE_ICON_BTN_STYLE)
                remove_btn.clicked.connect(lambda _, b=remove_btn: self._remove_from_btn(b))
                actions_layout.addWidget(remove_btn)
                pause_btn.setProperty('gid', d.get('id'))
                resume_btn.setProperty('gid', d.get('id'))
                cancel_btn.setProperty('gid', d.get('id'))
                pause_btn.clicked.connect(lambda _, b=pause_btn: self._pause_from_btn(b))
                resume_btn.clicked.connect(lambda _, b=resume_btn: self._resume_from_btn(b))
                cancel_btn.clicked.connect(lambda _, b=cancel_btn: self._cancel_from_btn(b))
                actions_layout.addWidget(pause_btn)
                actions_layout.addWidget(resume_btn)
                actions_layout.addWidget(cancel_btn)
                actions_widget.setLayout(actions_layout)
                self.downloads_table.setCellWidget(row, 9, actions_widget)

            # ensure table items are not editable and have consistent text color
            for r in range(self.downloads_table.rowCount()):
                for c in range(self.downloads_table.columnCount()):
                    it = self.downloads_table.item(r, c)
                    if it:
                        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)

            total_count = len(downloads)
            filtered_count = len(filtered_downloads)
            suffix = " [OFFLINE]" if is_stale else ""
            if self.current_filter == 'all':
                self.status_label.setText(f"✓ {total_count} download{'s' if total_count != 1 else ''} (refreshed: {self._get_time()}){suffix}")
            else:
                self.status_label.setText(f"✓ Showing {filtered_count} of {total_count} downloads (filter: {self.current_filter}) (refreshed: {self._get_time()}){suffix}")
            logger.info(f"Refreshed downloads: {total_count} total, {filtered_count} filtered")
            
        except Exception as e:
            logger.error(f"Error refreshing downloads: {e}")
            self.status_label.setText(f"❌ Error: {str(e)}")
    
    def _add_download_widget(self, download_data):
        """Deprecated: kept for compatibility. New UI uses QTableWidget."""
        download_id = download_data.get('id')
        logger.info(f"(legacy) Added download widget: {download_id}")
    
    def remove_download_item(self, download_id, refresh=True):
        """Remove a download item from the list"""
        # Remove from table rows
        found = False
        for r in range(self.downloads_table.rowCount()):
            cell_widget = self.downloads_table.cellWidget(r, 9)
            if cell_widget:
                # check buttons for gid property
                btn = cell_widget.findChild(QPushButton)
                if btn and btn.property('gid') == download_id:
                    self.downloads_table.removeRow(r)
                    found = True
                    break
        if not found:
            # Legacy list fallback
            for i in range(self.downloads_list.count()):
                item = self.downloads_list.item(i)
                widget = self.downloads_list.itemWidget(item)
                if isinstance(widget, DownloadItemWidget) and widget.download_id == download_id:
                    self.downloads_list.takeItem(i)
                    found = True
                    break
        logger.info(f"Removed download widget: {download_id}")
        
        if refresh:
            self.refresh_downloads()
    
    def clear_completed(self):
        """Clear all completed downloads"""
        completed_ids = []
        for download_id, widget in self.download_widgets.items():
            if widget.download_data.get('state') == 'completed':
                completed_ids.append(download_id)
        
        for download_id in completed_ids:
            try:
                self.api.cancel_download(download_id)  # Remove from backend
                self.remove_download_item(download_id, refresh=False)
            except Exception as e:
                logger.error(f"Error clearing completed download {download_id}: {e}")
        
        if completed_ids:
            self.refresh_downloads()
            self.status_label.setText(f"✓ Cleared {len(completed_ids)} completed download(s)")
        else:
            self.status_label.setText("No completed downloads to clear")
    
    def _get_time(self):
        """Get current time string"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def _format_speed(self, bytes_per_sec: int) -> str:
        if not bytes_per_sec:
            return '0 B/s'
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        i = 0
        val = float(bytes_per_sec)
        while val >= 1024 and i < len(units) - 1:
            val /= 1024
            i += 1
        return f"{val:.2f} {units[i]}"

    def _format_size(self, size_bytes: int) -> str:
        if not size_bytes:
            return '0 B'
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        val = float(size_bytes)
        while val >= 1024 and i < len(units) - 1:
            val /= 1024
            i += 1
        return f"{val:.2f} {units[i]}"

    def _format_eta(self, seconds: int) -> str:
        if seconds is None or seconds <= 0:
            return '--'
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def _pause_from_btn(self, btn: QPushButton):
        gid = btn.property('gid')
        try:
            self.api.pause_download(gid)
            self.refresh_downloads()
        except Exception as e:
            logger.error(f"Pause failed: {e}")

    def _resume_from_btn(self, btn: QPushButton):
        gid = btn.property('gid')
        try:
            self.api.resume_download(gid)
            self.refresh_downloads()
        except Exception as e:
            logger.error(f"Resume failed: {e}")

    def _cancel_from_btn(self, btn: QPushButton):
        """Cancel a download after a confirmation prompt."""
        gid = btn.property('gid')
        try:
            reply = QMessageBox.question(
                self,
                "Confirm Cancel",
                "Are you sure you want to cancel this download?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            try:
                self.api.cancel_download(gid)
                self.remove_download_item(gid)
            except Exception as e:
                logger.error(f"Cancel failed: {e}")
        except Exception:
            logger.exception('Error in cancel from button')

    def _open_link_from_btn(self, btn: QPushButton):
        gid = btn.property('gid')
        try:
            if gid:
                self._play_download(gid)
        except Exception as e:
            logger.error(f"Open folder failed: {e}")

    def _remove_from_btn(self, btn: QPushButton):
        gid = btn.property('gid')
        
        # Get title for better message
        title = "this download"
        # Try to find the title from the table
        try:
             # Find the row for this gid
             for r in range(self.downloads_table.rowCount()):
                 if self._get_gid_from_row(r) == gid:
                     item = self.downloads_table.item(r, 0)
                     if item:
                         full_text = item.text()
                         # Text is "Title (Quality)", extract Title
                         if " (" in full_text:
                             title = f"'{full_text.rsplit(' (', 1)[0]}'"
                         else:
                             title = f"'{full_text}'"
                     break
        except Exception:
            pass

        # Use our custom dialog
        dlg = DeleteConfirmationDialog(
            "Remove Download",
            f"Are you sure you want to remove {title} from the transfer list?",
            self
        )
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            delete_files = dlg.should_delete_files
            try:
                try:
                    # Pass delete_files flag
                    self.api.cancel_download(gid, delete_files=delete_files)
                except Exception:
                    logger.exception('Backend cancel failed during remove')
                self.remove_download_item(gid)
            except Exception as e:
                logger.error(f"Remove failed: {e}")

    def _get_gid_from_row(self, row: int):
        item = self.downloads_table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_table_context_menu(self, pos):
        try:
            row = self.downloads_table.rowAt(pos.y())
            if row < 0:
                return
            gid = self._get_gid_from_row(row)
            if not gid:
                return

            menu = QMenu(self)
            play_action = menu.addAction('Play')
            open_folder_action = menu.addAction('Open folder location')
            pause_action = menu.addAction('Pause')
            resume_action = menu.addAction('Resume')
            cancel_action = menu.addAction('Cancel')
            force_action = menu.addAction('Force Start')

            action = menu.exec(self.downloads_table.viewport().mapToGlobal(pos))
            if action is play_action:
                self._play_download(gid)
            elif action is open_folder_action:
                try:
                    dl = self.api.get_download(gid)
                    if not dl:
                        return
                    save_path = dl.get('save_path') or dl.get('savePath') or ''
                    if not save_path:
                        QMessageBox.warning(self, 'Open folder', 'No save path available')
                        return
                    p = Path(save_path)
                    target = p if p.is_dir() else p.parent
                    if os.name == 'nt':
                        os.startfile(str(target))  # type: ignore
                    else:
                        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
                except Exception:
                    logger.exception('Open folder action failed')
                    QMessageBox.warning(self, 'Open folder', 'Failed to open folder')
            elif action is pause_action:
                self.api.pause_download(gid)
                self.refresh_downloads()
            elif action is resume_action:
                self.api.resume_download(gid)
                self.refresh_downloads()
            elif action is cancel_action:
                self.api.cancel_download(gid)
                self.remove_download_item(gid)
            elif action is force_action:
                # Force start: try resume and refresh UI
                try:
                    self.api.resume_download(gid)
                    self.refresh_downloads()
                except Exception:
                    logger.exception('Force start failed')
        except Exception as e:
            logger.error(f"Context menu error: {e}")

    def _on_table_cell_double_clicked(self, row, col):
        try:
            gid = self._get_gid_from_row(row)
            if gid:
                self._play_download(gid)
        except Exception as e:
            logger.error(f"Double click handler error: {e}")

    def _play_download(self, gid: str):
        """Attempt to open the largest video file in the download folder, or open the folder."""
        try:
            dl = self.api.get_download(gid)
            if not dl:
                QMessageBox.warning(self, 'Play', 'Download info not found')
                return
            save_path = dl.get('save_path') or dl.get('savePath') or ''
            if not save_path:
                QMessageBox.warning(self, 'Play', 'No save path available for this download')
                return

            p = Path(save_path)
            if not p.exists():
                # If save_path points to a directory that doesn't exist, try parent
                QMessageBox.warning(self, 'Play', f'Path does not exist: {save_path}')
                return

            # If save_path is a directory, search for video files
            target_file = None
            if p.is_dir():
                video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
                candidates = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in video_exts]
                if candidates:
                    # pick largest file
                    target_file = max(candidates, key=lambda f: f.stat().st_size)
            else:
                # save_path might be the file itself
                if p.suffix.lower() in {'.mp4', '.mkv', '.avi', '.mov', '.webm'}:
                    target_file = p

            if target_file and target_file.exists():
                try:
                    if os.name == 'nt':
                        os.startfile(str(target_file))  # type: ignore
                    else:
                        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_file)))
                except Exception:
                    # fallback: open containing folder
                    logger.exception('Failed to open file, opening folder instead')
                    if os.name == 'nt':
                        os.startfile(str(target_file.parent))  # type: ignore
                    else:
                        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_file.parent)))
            else:
                # no video file found; open folder
                try:
                    if p.is_dir():
                        if os.name == 'nt':
                            os.startfile(str(p))  # type: ignore
                        else:
                            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
                    else:
                        # path is a file but not a video; open parent folder
                        parent = p.parent
                        if os.name == 'nt':
                            os.startfile(str(parent))  # type: ignore
                        else:
                            QDesktopServices.openUrl(QUrl.fromLocalFile(str(parent)))
                except Exception:
                    logger.exception('Failed to open folder')
                    QMessageBox.warning(self, 'Play', f'Failed to open location: {save_path}')
        except Exception as e:
            logger.error(f"Play action failed for {gid}: {e}")
            QMessageBox.warning(self, 'Play', f'Error: {e}')
