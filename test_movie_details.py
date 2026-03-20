"""
Test script for MovieDetailsDialog
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from frontend.ui.movie_details import MovieDetailsDialog
from frontend.utils.api_client import APIClient

def test_dialog():
    """Test opening the movie details dialog"""
    print("Initializing test...")
    
    # Create application
    app = QApplication(sys.argv)
    
    # Initialize API client
    api = APIClient()
    
    # Check backend connection
    if not api.health_check():
        print("ERROR: Backend not available. Start backend first:")
        print("  python backend/app.py")
        return 1
    
    print("✓ Backend connected")
    
    # Get list of movies
    movies = api.get_movies()
    if not movies:
        print("ERROR: No movies found in database. Scrape some movies first:")
        print("  Use the 'Scrape YTS' button in the app")
        return 1
    
    print(f"✓ Found {len(movies)} movies in database")
    
    # Get first movie ID
    movie_id = movies[0]['id']
    movie_title = movies[0]['title']
    print(f"✓ Testing with movie: {movie_title} (ID: {movie_id})")
    
    # Create and show dialog
    print("\nOpening movie details dialog...")
    print("(Close the dialog window to exit)")
    dialog = MovieDetailsDialog(movie_id, api)
    dialog.exec()
    
    print("\n✓ Dialog test completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(test_dialog())
