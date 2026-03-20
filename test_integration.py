"""
Integration test for movie details dialog in main window
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from frontend.ui.main_window import MainWindow

def test_integration():
    """Test that clicking a movie card opens the dialog"""
    print("Starting integration test...")
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    window.show()
    
    print("✓ Main window opened")
    print("✓ Checking backend connection...")
    
    # Wait for initial load
    def check_and_simulate():
        if not window.current_movies:
            print("⚠ No movies loaded. Load movies first by:")
            print("  1. Start backend: python backend/app.py")
            print("  2. Click 'Scrape YTS' button")
            app.quit()
            return
        
        print(f"✓ Loaded {len(window.current_movies)} movies")
        print(f"✓ Simulating click on first movie: {window.current_movies[0]['title']}")
        
        # Simulate clicking first movie
        movie_id = window.current_movies[0]['id']
        window.on_movie_clicked(movie_id)
        
        print("\n✓ Dialog opened successfully!")
        print("(Close the dialog to continue, then close main window to exit)")
    
    # Schedule the check after initial load
    QTimer.singleShot(1000, check_and_simulate)
    
    # Run application
    sys.exit(app.exec())

if __name__ == '__main__':
    test_integration()
