"""
Quick test to verify dialog appears
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox
from frontend.ui.movie_details import MovieDetailsDialog
from frontend.utils.api_client import APIClient

def test():
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    
    print("Initializing API client...")
    api = APIClient()
    
    print("Checking backend...")
    if not api.health_check():
        QMessageBox.critical(None, "Error", "Backend not available!\nStart: python backend/app.py")
        return 1
    
    print("✓ Backend connected")
    
    print("Fetching movies...")
    movies = api.get_movies()
    if not movies:
        QMessageBox.critical(None, "Error", "No movies in database!\nRun scraper first.")
        return 1
    
    print(f"✓ Found {len(movies)} movies")
    
    movie_id = movies[0]['id']
    movie_title = movies[0]['title']
    
    print(f"Opening dialog for: {movie_title} (ID: {movie_id})")
    
    # Create and show dialog
    dialog = MovieDetailsDialog(movie_id, api)
    dialog.exec()
    
    print("✓ Dialog closed")
    return 0

if __name__ == '__main__':
    sys.exit(test())
