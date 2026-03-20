"""Debug script to find where QWidget is created before QApplication"""
import sys
import traceback

try:
    # Try importing the module that's causing issues
    from frontend.ui.movie_details import MovieDetailsDialog
    print("Import successful!")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
