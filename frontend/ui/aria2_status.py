"""
Aria2 Status Widget - Shows real-time aria2 daemon health and statistics
"""
import logging
from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal  # type: ignore

logger = logging.getLogger(__name__)


class Aria2Worker(QThread):
    """Background worker for aria2 status updates"""
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url

    def run(self):
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/aria2/status", timeout=5)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    self.error.emit('Invalid JSON')
                    return
                self.result.emit(data)
            else:
                self.error.emit(f'HTTP {resp.status_code}')
        except BaseException as e:
            # Catch BaseException to handle KeyboardInterrupt as well
            try:
                self.error.emit(str(e))
            except Exception:
                pass


class Aria2StatusWidget(QWidget):
    """Widget displaying aria2 daemon status and statistics"""
    
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self._aria2_worker = None
        self.setup_ui()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(3000)  # 3 seconds
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start()
        
        # Initial refresh
        self.refresh_status()
    
    def setup_ui(self):
        """Setup the widget UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)
        
        # Header
        header = QLabel("aria2 Download Manager Status")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        layout.addWidget(header)
        
        # Status indicator
        status_row = QHBoxLayout()
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("font-size: 16px; color: #888888;")
        status_row.addWidget(self.status_indicator)
        
        self.status_label = QLabel("Checking...")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 13px;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #444444;")
        layout.addWidget(separator)
        
        # Stats grid
        stats_layout = QVBoxLayout()
        
        self.version_label = QLabel("Version: --")
        self.version_label.setStyleSheet("color: #cccccc;")
        stats_layout.addWidget(self.version_label)
        
        self.active_label = QLabel("Active Downloads: --")
        self.active_label.setStyleSheet("color: #cccccc;")
        stats_layout.addWidget(self.active_label)
        
        self.waiting_label = QLabel("Waiting: --")
        self.waiting_label.setStyleSheet("color: #cccccc;")
        stats_layout.addWidget(self.waiting_label)
        
        self.stopped_label = QLabel("Stopped: --")
        self.stopped_label.setStyleSheet("color: #cccccc;")
        stats_layout.addWidget(self.stopped_label)
        
        self.download_speed_label = QLabel("Download Speed: --")
        self.download_speed_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        stats_layout.addWidget(self.download_speed_label)
        
        self.upload_speed_label = QLabel("Upload Speed: --")
        self.upload_speed_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        stats_layout.addWidget(self.upload_speed_label)
        
        layout.addLayout(stats_layout)
        layout.addStretch()
        
        # Manual refresh button removed; status auto-refreshes every 3s
    
    def refresh_status(self):
        """Start a background worker to fetch and update aria2 status."""
        try:
            # Avoid starting multiple concurrent workers
            if getattr(self, '_aria2_worker', None) and self._aria2_worker.isRunning():
                return
            
            # Prevent starting a new thread if we are already shutting down
            if not hasattr(self, 'api') or self.refresh_timer.isActive() == False:
                 # If timer is stopped, don't trigger new status refresh
                 return

            self._aria2_worker = Aria2Worker(self.api.base_url)
            self._aria2_worker.result.connect(self._on_refresh_result)
            self._aria2_worker.error.connect(self._set_error_state)
            # Safe cleanup: don't nullify the reference in the signal handler
            # to avoid premature destruction of the QThread object.
            self._aria2_worker.start()

        except KeyboardInterrupt:
            # Stop the timer so Ctrl+C in the console doesn't produce a traceback
            try:
                if getattr(self, 'refresh_timer', None):
                    self.refresh_timer.stop()
            except Exception:
                pass
            logger.info('refresh_status interrupted by KeyboardInterrupt')
        except Exception as e:
            logger.debug(f'refresh_status error: {e}')

    def shutdown(self, wait_ms: int = 2000):
        """Stop the refresh timer and ensure any running worker is finished.

        wait_ms: milliseconds to wait for a running QThread before forcing termination.
        """
        try:
            if getattr(self, 'refresh_timer', None):
                self.refresh_timer.stop()
        except Exception:
            pass

        worker = getattr(self, '_aria2_worker', None)
        if worker and worker.isRunning():
            try:
                # Ask the thread to quit and wait briefly. Note: if the thread
                # is blocked in a requests call, quit() may not stop it; we
                # still wait and then attempt terminate as a last resort.
                worker.quit()
                # QThread.wait() expects milliseconds; pass wait_ms directly.
                worker.wait(wait_ms)
            except Exception:
                pass
            # If still running, terminate (last resort)
            try:
                if worker.isRunning():
                    worker.terminate()
                    # Give terminate up to 1s to stop
                    worker.wait(1000)
            except Exception:
                pass
        try:
            setattr(self, '_aria2_worker', None)
        except Exception:
            pass

    def _on_refresh_result(self, data: dict):
        """Handle successful refresh results from worker (runs in main thread)."""
        if data.get('success'):
            # Update status indicator
            self.status_indicator.setStyleSheet("font-size: 16px; color: #4CAF50;")
            self.status_label.setText("Running")

            # Update stats
            self.version_label.setText(f"Version: {data.get('version', 'unknown')}")
            self.active_label.setText(f"Active Downloads: {data.get('active_downloads', 0)}")
            self.waiting_label.setText(f"Waiting: {data.get('waiting_downloads', 0)}")
            self.stopped_label.setText(f"Stopped: {data.get('stopped_downloads', 0)}")

            # Format speeds
            try:
                dl_speed = int(data.get('download_speed', 0))
            except Exception:
                dl_speed = 0
            try:
                ul_speed = int(data.get('upload_speed', 0))
            except Exception:
                ul_speed = 0

            self.download_speed_label.setText(f"Download Speed: {self._format_speed(dl_speed)}")
            self.upload_speed_label.setText(f"Upload Speed: {self._format_speed(ul_speed)}")
        else:
            self._set_error_state(data.get('error', 'Unknown error'))
    
    def _set_error_state(self, error_msg: str):
        """Set widget to error state"""
        self.status_indicator.setStyleSheet("font-size: 16px; color: #f44336;")
        self.status_label.setText(f"Error: {error_msg[:50]}")  # type: ignore
        self.version_label.setText("Version: --")
        self.active_label.setText("Active Downloads: --")
        self.waiting_label.setText("Waiting: --")
        self.stopped_label.setText("Stopped: --")
        self.download_speed_label.setText("Download Speed: --")
        self.upload_speed_label.setText("Upload Speed: --")
    
    def _format_speed(self, bytes_per_sec: int) -> str:
        """Format speed in human-readable format"""
        if bytes_per_sec == 0:
            return "0 B/s"
        
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        unit_index = 0
        speed = float(bytes_per_sec)
        
        while speed >= 1024 and unit_index < len(units) - 1:
            speed /= 1024
            unit_index += 1
        
        return f"{speed:.2f} {units[unit_index]}"
