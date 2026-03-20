try:
    from PyQt6.QtCore import QT_VERSION_STR
    print(f"PyQt6.QtCore loaded successfully. Version: {QT_VERSION_STR}")
except Exception as e:
    print(f"Failed to load PyQt6.QtCore: {e}")

try:
    from PyQt6.QtNetwork import QLocalServer
    print("PyQt6.QtNetwork loaded successfully.")
except Exception as e:
    print(f"Failed to load PyQt6.QtNetwork: {e}")
