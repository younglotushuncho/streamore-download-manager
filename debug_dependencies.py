import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print("Testing imports...")
try:
    import requests
    print("Requests imported successfully")
except Exception as e:
    print(f"FAILED to import requests: {e}")
    import traceback
    traceback.print_exc()

try:
    import charset_normalizer
    print("charset_normalizer imported successfully")
    from charset_normalizer import md
    print("charset_normalizer.md imported successfully")
except Exception as e:
    print(f"FAILED to import charset_normalizer context: {e}")
    import traceback
    traceback.print_exc()
