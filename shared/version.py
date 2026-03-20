try:
    # Fix for weird PyInstaller/charset_normalizer.md ModuleNotFoundError 
    # when running from a patched source folder.
    import importlib
    importlib.import_module('charset_normalizer.md')
except (ImportError, ModuleNotFoundError):
    pass

__version__ = "3.0.1"
