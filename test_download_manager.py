"""
Test script to showcase the Download Manager UI with mock data
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

# Mock API client that returns sample downloads
class MockAPIClient:
    def __init__(self):
        self.downloads = [
            {
                'id': '1',
                'movie_title': 'The Dark Knight',
                'quality': '1080p',
                'state': 'downloading',
                'progress': 45.5,
                'download_rate': 5242880,  # 5 MB/s
                'upload_rate': 1048576,    # 1 MB/s
                'num_peers': 25,
                'num_seeds': 150,
                'size_total': 2147483648,  # 2 GB
                'size_downloaded': 976809984,  # ~931 MB
                'eta': 180
            },
            {
                'id': '2',
                'movie_title': 'Inception',
                'quality': '720p',
                'state': 'downloading',
                'progress': 78.2,
                'download_rate': 3145728,  # 3 MB/s
                'upload_rate': 524288,     # 0.5 MB/s
                'num_peers': 12,
                'num_seeds': 85,
                'size_total': 1610612736,  # 1.5 GB
                'size_downloaded': 1259291648,
                'eta': 90
            },
            {
                'id': '3',
                'movie_title': 'Interstellar',
                'quality': '1080p',
                'state': 'paused',
                'progress': 23.0,
                'download_rate': 0,
                'upload_rate': 0,
                'num_peers': 0,
                'num_seeds': 0,
                'size_total': 2684354560,  # 2.5 GB
                'size_downloaded': 617318195,
                'eta': 0
            },
            {
                'id': '4',
                'movie_title': 'The Matrix',
                'quality': '720p',
                'state': 'completed',
                'progress': 100.0,
                'download_rate': 0,
                'upload_rate': 2097152,  # 2 MB/s (seeding)
                'num_peers': 0,
                'num_seeds': 120,
                'size_total': 1342177280,  # 1.25 GB
                'size_downloaded': 1342177280,
                'eta': 0
            },
            {
                'id': '5',
                'movie_title': 'Avatar',
                'quality': '1080p',
                'state': 'downloading',
                'progress': 12.8,
                'download_rate': 7340032,  # 7 MB/s
                'upload_rate': 1572864,    # 1.5 MB/s
                'num_peers': 45,
                'num_seeds': 200,
                'size_total': 3221225472,  # 3 GB
                'size_downloaded': 412316860,
                'eta': 320
            }
        ]
    
    def get_downloads(self):
        """Return mock downloads"""
        return self.downloads
    
    def pause_download(self, download_id):
        """Mock pause"""
        for d in self.downloads:
            if d['id'] == download_id:
                d['state'] = 'paused'
                d['download_rate'] = 0
                d['upload_rate'] = 0
                return True
        return False
    
    def resume_download(self, download_id):
        """Mock resume"""
        for d in self.downloads:
            if d['id'] == download_id:
                d['state'] = 'downloading'
                return True
        return False
    
    def cancel_download(self, download_id):
        """Mock cancel"""
        self.downloads = [d for d in self.downloads if d['id'] != download_id]
        return True


class DownloadManagerDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Download Manager Demo - YTS Movie Monitor")
        self.setMinimumSize(1000, 600)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        # Create mock API
        self.api = MockAPIClient()
        
        # Import and create download manager
        from frontend.ui.download_manager import DownloadManagerWidget
        self.download_manager = DownloadManagerWidget(self.api)
        
        # Set as central widget
        self.setCentralWidget(self.download_manager)
        
        # Auto-enable refresh
        self.download_manager.auto_refresh_btn.click()
        
        print("=" * 80)
        print("DOWNLOAD MANAGER DEMO")
        print("=" * 80)
        print("\nShowing 5 mock downloads:")
        print("  1. The Dark Knight (1080p) - Downloading 45.5%")
        print("  2. Inception (720p) - Downloading 78.2%")
        print("  3. Interstellar (1080p) - Paused 23%")
        print("  4. The Matrix (720p) - Completed 100%")
        print("  5. Avatar (1080p) - Downloading 12.8%")
        print("\nFeatures:")
        print("  ✓ Real-time progress bars")
        print("  ✓ Speed, peers, and seeds display")
        print("  ✓ Pause/Resume/Cancel buttons")
        print("  ✓ Auto-refresh (enabled)")
        print("  ✓ Clear completed button")
        print("\nTry clicking the buttons to test interactions!")
        print("=" * 80)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set dark palette
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(68, 68, 68))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    
    window = DownloadManagerDemo()
    window.show()
    
    sys.exit(app.exec())
