"""PyInstaller runtime hook to set Qt plugin path for PyQt6."""
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Clean up stale _MEI* temp folders from previous PyInstaller runs.
# The onefile bootloader sometimes can't delete its temp dir on exit
# (locked DLLs, update subprocess, etc.), so we clean them on next launch.
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    try:
        _meipass = getattr(sys, '_MEIPASS', None)
        if _meipass:
            _tmp = Path(_meipass).parent  # e.g. C:\Users\X\AppData\Local\Temp
            _current_name = Path(_meipass).name  # e.g. _MEI12345
            for _old in _tmp.glob('_MEI*'):
                if _old.name != _current_name and _old.is_dir():
                    try:
                        import shutil
                        shutil.rmtree(str(_old), ignore_errors=True)
                    except Exception:
                        pass
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Delta-patch override directory
# When a patch is applied (via the delta updater), changed .py files are
# placed in _src_patches/ next to the .exe.  Insert it at sys.path[0] so
# patched modules always shadow the compiled-in versions.
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    _exe_dir = Path(sys.executable).resolve().parent
    _patches_dir = _exe_dir / '_src_patches'
    _app_name = 'Streamore Monitor' # Stable name for folder in LocalAppData
    
    _found_patches = None
    if _patches_dir.exists():
        _found_patches = _patches_dir
    else:
        # If the app cannot write to the install directory (e.g. Program Files),
        # a fallback patch location under the current user's LocalAppData may
        # be used by the updater. Check and add that too.
        try:
            _local = os.getenv('LOCALAPPDATA') or None
            if _local:
                _local_patches = Path(_local) / _app_name / '_src_patches'
                if _local_patches.exists():
                    _found_patches = _local_patches
        except Exception:
            pass
            
    if _found_patches:
        # SAFETY CHECK: If the patch contains a broken 'charset_normalizer' package
        # (e.g. empty __init__.py, or missing md submodule), it will shadow the
        # working one in the EXE and cause a crash on startup.
        _cn_dir = _found_patches / 'charset_normalizer'
        if _cn_dir.exists():
            _cn_init = _cn_dir / '__init__.py'
            _cn_md = _cn_dir / 'md.py'
            # Broken if: init is too small OR 'md' submodule is missing
            _broken = (_cn_init.exists() and _cn_init.stat().st_size < 10) or (not _cn_md.exists())
            if _broken:
                print(f"Runtime Hook: Ignoring BROKEN patch directory at {_found_patches} "
                      f"(incomplete charset_normalizer — missing md.py or empty __init__.py)")
                _found_patches = None

    if _found_patches:
        sys.path.insert(0, str(_found_patches))
        os.environ['APP_PATCH_PATH'] = str(_found_patches)
        print(f"Runtime Hook: Loading patches from {_found_patches}")

# ---------------------------------------------------------------------------
# Qt plugin path setup
# ---------------------------------------------------------------------------
# When frozen, set QT_PLUGIN_PATH to the bundled plugins directory
if getattr(sys, 'frozen', False):
    # PyInstaller sets sys._MEIPASS to the bundle directory
    bundle_dir = Path(sys._MEIPASS)
    
    # In PyInstaller bundles, Qt files are in _internal/PyQt6/Qt6
    qt_plugins = bundle_dir / 'PyQt6' / 'Qt6' / 'plugins'
    if qt_plugins.exists():
        os.environ['QT_PLUGIN_PATH'] = str(qt_plugins)
        # Also ensure platform plugin path is explicitly set
        platforms = qt_plugins / 'platforms'
        if platforms.exists():
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(platforms)
    
    # Add Qt bin directory to PATH so Qt DLLs are found
    # This is CRITICAL for Windows to find the Qt and MSVC runtime DLLs
    qt_bin = bundle_dir / 'PyQt6' / 'Qt6' / 'bin'
    if qt_bin.exists():
        # Prepend to PATH (highest priority)
        os.environ['PATH'] = str(qt_bin) + os.pathsep + os.environ.get('PATH', '')
        
        # Also use Windows-specific DLL directory APIs for more reliable loading
        try:
            # Add to DLL search path (Windows 7+)
            os.add_dll_directory(str(qt_bin))
        except (AttributeError, OSError):
            pass
        
        # Try using SetDllDirectory as well (affects current process)
        try:
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            # SetDllDirectoryW sets the DLL search directory
            kernel32.SetDllDirectoryW(str(qt_bin))
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Fix certifi SSL/TLS CA bundle path for frozen PyInstaller apps
# Without this, requests raises:
#   "Could not find a suitable TLS CA certificate bundle, invalid path: ..._MEIxxxxx\certifi\cacert.pem"
# The fix: point SSL_CERT_FILE / REQUESTS_CA_BUNDLE at the certifi bundle
# that PyInstaller extracted into sys._MEIPASS.
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    _meipass = getattr(sys, '_MEIPASS', None)
    if _meipass:
        import os as _os
        _ca = _os.path.join(_meipass, 'certifi', 'cacert.pem')
        if _os.path.isfile(_ca):
            _os.environ['SSL_CERT_FILE'] = _ca
            _os.environ['REQUESTS_CA_BUNDLE'] = _ca
    # Also tell certifi where its bundle is via the certifi env var
    try:
        import certifi as _certifi
        _ca2 = _certifi.where()
        if _ca2 and _os.path.isfile(_ca2):
            _os.environ['SSL_CERT_FILE'] = _ca2
            _os.environ['REQUESTS_CA_BUNDLE'] = _ca2

    except Exception:
        pass
