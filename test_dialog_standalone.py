"""
Standalone test - Shows dialog with sample data
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from frontend.ui.movie_details import MovieDetailsDialog

class MockAPIClient:
    """Mock API client with sample movie data"""
    def get_movie(self, movie_id):
        return {
            'id': '6dc08678abfe',
            'title': 'Symbol',
            'description': 'A Japanese man in polka-dot pajamas wakes up in a room with no doors. Meanwhile, a middle-aged Mexican wrestler prepares for his most challenging match ever.',
            'torrents': [
                {'quality': '720p', 'size': '850MB', 'magnet_link': 'magnet:...'},
                {'quality': '1080p', 'size': '1.8GB', 'magnet_link': 'magnet:...'},
                {'quality': '2160p', 'size': '4.2GB', 'magnet_link': 'magnet:...'},
            ]
        }

    def start_download(self, movie_id, title, quality, magnet):
        # Minimal stub for standalone tests: log the call and return success
        print(f"[MockAPIClient] start_download called: {title} - {quality} - {magnet[:60]}...")
        return {'success': True}

def main():
    app = QApplication(sys.argv)
    
    # Dark theme for the application
    app.setStyleSheet("""
        QApplication {
            background-color: #1e1e1e;
        }
    """)
    
    api = MockAPIClient()
    
    print("Opening Movie Details Dialog with sample data...")
    print("Title: Symbol")
    print("Description: Japanese man in polka-dot pajamas...")
    print("Qualities: 720p, 1080p, 2160p")
    print("\nClose the dialog window to exit.")
    
    dialog = MovieDetailsDialog('test_id', api)
    dialog.show()
    
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
