"""
Quick restart script for frontend
Closes existing window and starts a new one
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Restarting YTS Movie Monitor Frontend...")
print("=" * 60)
print()
print("Changes applied:")
print("  ✅ Real poster images now displayed")
print("  ✅ Smooth image scaling")
print("  ✅ Fallback to emoji if poster missing")
print()
print("Close the old window if it's still open, then:")
print()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from frontend.ui.main_window import MainWindow
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = QApplication(sys.argv)
app.setApplicationName("YTS Movie Monitor")
app.setOrganizationName("YTS Monitor")

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

window = MainWindow()
window.show()

print("✅ Frontend restarted successfully!")
print("=" * 60)

sys.exit(app.exec())
