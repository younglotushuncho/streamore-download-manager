"""
Main entry point for YTS Movie Monitor application
"""
import sys
import os
import subprocess
import logging
import threading
import ctypes
import traceback
import time
from pathlib import Path

# Add project root to path so 'shared' can be imported when running directly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- CRITICAL HOTFIXES: SSL & CHARSET_NORMALIZER ---
import shared.sanitize  # Force environment sanitation before requests is imported
from types import ModuleType

# 1. SSL Path Correction for restarts
if getattr(sys, 'frozen', False):
    _meipass = getattr(sys, '_MEIPASS', None)
    if _meipass:
        _ca = os.path.join(_meipass, 'certifi', 'cacert.pem')
        if os.path.isfile(_ca):
            os.environ['SSL_CERT_FILE'] = _ca
            os.environ['REQUESTS_CA_BUNDLE'] = _ca

# 2. Removed the Import Interceptor as it completely breaks the `requests` library.

# ----------------------------------------------------

# Add project root to path
if getattr(sys, 'frozen', False):
    # For frozen app, the true base is where the .exe lives
    project_root = Path(sys.executable).resolve().parent
    # NOTE: Do NOT manipulate sys.path here for frozen mode.
    # The runtime hook (runtime_hook_pyqt6.py) already correctly inserts
    # _src_patches/ at sys.path[0] before this file runs. Any additional
    # sys.path manipulation here would shadow the frozen bundle's compiled
    # modules (e.g. charset_normalizer.md) with an incomplete copy and
    # cause ModuleNotFoundError on startup.
else:
    # For development/source mode
    project_root = Path(__file__).resolve().parent.parent

    _parts = project_root.parts
    if '_src_patches' in _parts:
        idx = _parts.index('_src_patches')
        # Use a list comprehension to avoid slice indexing which is confusing the IDE
        project_root = Path(*[p for i, p in enumerate(_parts) if i < idx])

    sys.path.insert(0, str(project_root))


def _is_actually_writable(path: Path) -> bool:
    """Robust check if a directory is actually writable on Windows."""
    test_file = path / f".write_test_{os.getpid()}"
    try:
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError, PermissionError):
        return False

def _diagnose_dlls(note: str | None = None):
    """Write diagnostic info about DLL search paths and Qt DLLs to a log file."""
    try:
        if getattr(sys, 'frozen', False):
            log_dir = Path(sys.executable).resolve().parent
        else:
            log_dir = project_root
            
        # If the app folder is read-only (e.g. Program Files), use LocalAppData for logs
        if not _is_actually_writable(log_dir):
            _local = os.getenv('LOCALAPPDATA')
            if _local:
                log_dir = Path(_local) / 'Streamore Monitor'
                log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / "movie_app_diagnose.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if note:
                f.write(f"Note: {note}\n")
            f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
            f.write(f"Executable: {sys.executable}\n")
            f.write("Environment PATH entries:\n")
            for p in os.environ.get("PATH", "").split(os.pathsep):
                f.write(f"  {p}\n")

            # Find any Qt6Core.dll files on PATH
            f.write("Detected Qt6Core.dll files:\n")
            detected = []
            for p in os.environ.get("PATH", "").split(os.pathsep):
                try:
                    candidate = Path(p) / "Qt6Core.dll"
                    if candidate.exists():
                        detected.append(str(candidate))
                        f.write(f"  {candidate}\n")
                except Exception:
                    pass

            # Check bundled location for frozen app
            bundled = None
            if getattr(sys, 'frozen', False):
                try:
                    meipass = Path(sys._MEIPASS)  # type: ignore
                    bundled = meipass / 'PyQt6' / 'Qt6' / 'bin' / 'Qt6Core.dll'
                    f.write(f"Bundled candidate: {bundled}\n")
                    if bundled.exists():
                        f.write("  (exists)\n")
                except Exception:
                    f.write("  (unable to inspect bundle path)\n")

            # Attempt to load the bundled DLL (if present) to capture OS error
            if bundled and bundled.exists():
                try:
                    f.write("Attempting ctypes.WinDLL load of bundled Qt6Core.dll...\n")
                    ctypes.WinDLL(str(bundled))  # type: ignore
                    f.write("ctypes.WinDLL load succeeded\n")
                except Exception as e:
                    f.write(f"ctypes.WinDLL load failed: {e}\n")
                    f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        # Never raise from diagnostics -- best-effort logging
        try:
            pass
        except Exception:
            pass



# Ensure Qt DLLs from the venv PyQt6 package are available on Windows.
# This helps avoid "DLL load failed while importing QtCore" issues caused by
# missing or mis-resolved Qt runtime DLLs. We add the PyQt6 Qt6/bin directory
# to the DLL search path before importing PyQt6.
_diagnose_dlls("before add_dll_directory")

try:
    # For development environment (venv)
    qt_bin = project_root / 'venv' / 'Lib' / 'site-packages' / 'PyQt6' / 'Qt6' / 'bin'
    if qt_bin.exists():
        os.add_dll_directory(str(qt_bin))  # type: ignore
    
    # If running as a PyInstaller bundle, add the bundled Qt bin dir
    if getattr(sys, 'frozen', False):
        # sys._MEIPASS points to the _internal directory in PyInstaller bundles
        meipass = Path(sys._MEIPASS)  # type: ignore
        bundled_qt_bin = meipass / 'PyQt6' / 'Qt6' / 'bin'
        if bundled_qt_bin.exists():
            os.add_dll_directory(str(bundled_qt_bin))  # type: ignore
    _diagnose_dlls("after add_dll_directory")
except Exception:
    # Best-effort; if this fails, importing PyQt6 will raise the original error.
    pass

# Try importing PyQt6 and capture any errors to the diagnostic log
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox  # type: ignore
    from PyQt6.QtCore import Qt, QTimer, QTranslator, QLocale, QSettings  # type: ignore
    from frontend.ui.main_window import MainWindow  # type: ignore
except Exception as e:
    _diagnose_dlls(f"FATAL: PyQt6 import failed: {e.__class__.__name__}: {e}")
    import sys
    # Try to show a message box using ctypes if possible
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(  # type: ignore
            0, 
            f"Failed to load PyQt6:\n\n{e.__class__.__name__}: {e}\n\nCheck movie_app_diagnose.log for details.",
            "MovieApp - Startup Error",
            0x10  # MB_ICONERROR
        )
    except Exception:
        pass
    sys.exit(1)

# Import config
from backend.config import Config  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_for_updates(parent=None):
    """Check for updates in the background and notify user if available."""
    # Run network check off the main thread to avoid blocking Qt startup.
    def _worker():
        try:
            logger.info(f"Checking for updates (current version: {Config.VERSION})...")
            result = None
            try:
                # Lazy import to avoid crashing startup if dependency is missing in old bundle
                from frontend.utils.update_client import check_for_updates as check_updates_api  # type: ignore
                result = check_updates_api()
            except (ImportError, ModuleNotFoundError) as ie:
                logger.warning(f"Update check skipped: dependency missing in this build ({ie})")
                return
            except Exception as e:
                logger.debug(f"Update check exception: {e}")
                return

            if result:
                # Do the heavy download in the worker thread before bothering the main thread
                setup_url = result.get('setup_url')
                setup_name = result.get('setup_name')
                if setup_url:
                    import tempfile, requests as _req  # type: ignore
                    dl_dir = tempfile.mkdtemp()
                    setup_path = os.path.join(dl_dir, setup_name)
                    logger.info(f"Downloading setup installer in background: {setup_url}")
                    try:
                        with _req.get(setup_url, stream=True, timeout=120) as r:
                            r.raise_for_status()
                            with open(setup_path, 'wb') as f:
                                for chunk in r.iter_content(65536):
                                    if chunk:
                                        f.write(chunk)
                        result['downloaded_setup_path'] = setup_path
                    except Exception as e:
                        logger.error(f"Background download failed: {e}")

            def _handle():
                try:
                    if result:
                        version = result.get('version')
                        path = result.get('path')
                        exe_path = result.get('exe_path', path)
                        # update_client.check_for_updates() already downloads the
                        # installer and returns 'installer_path'; fall back to the
                        # legacy 'downloaded_setup_path' key for older code paths.
                        setup_path = (result.get('installer_path')
                                      or result.get('downloaded_setup_path'))
                        is_patch = result.get('is_patch', False)
                        
                        logger.info(f"Update available: {version}. Installing automatically...")
                        
                        try:
                            if is_patch:
                                logger.info("Delta patch applied. Restarting app...")
                                from updater.delta_updater import restart_app  # type: ignore
                                restart_app() # This calls sys.exit(0) internally
                                return

                            if setup_path:
                                logger.info(f"Running setup installer: {setup_path}")
                                # /VERYSILENT: hides all windows
                                # /SUPPRESSMSGBOXES: auto-answers 'Yes' to overwrite prompts etc
                                # /SP-: disables 'This will install...' prompt
                                # /CLOSEAPPLICATIONS: closes running instances
                                # /RESTARTAPPLICATIONS: restarts apps closed by the installer (extra safety)
                                subprocess.Popen(
                                    [setup_path, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/SP-', '/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS'],
                                    creationflags=subprocess.DETACHED_PROCESS,  # type: ignore
                                )
                            else:
                                # Fallback: batch trampoline for frozen, or install_update for dev
                                current_exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
                                current_pid = os.getpid()
                                if getattr(sys, 'frozen', False):
                                    import tempfile
                                    bat_path = os.path.join(tempfile.gettempdir(), 'streamore_update.bat')
                                    with open(bat_path, 'w') as bf:
                                        bf.write('@echo off\n')
                                        bf.write('echo Updating Streamore Monitor...\n')
                                        bf.write(f'taskkill /PID {current_pid} /F >nul 2>&1\n')
                                        bf.write('timeout /t 3 /nobreak >nul\n')
                                        bf.write(f'copy /y "{exe_path}" "{current_exe}"\n')
                                        bf.write(f'start "" "{current_exe}"\n')
                                        bf.write('del "%~f0"\n')
                                    subprocess.Popen(
                                        ['cmd', '/c', bat_path],
                                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,  # type: ignore
                                        close_fds=True
                                    )
                                else:
                                    installer_script = project_root / 'updater' / 'install_update.py'
                                    subprocess.Popen(
                                        [sys.executable, str(installer_script), exe_path, current_exe, str(current_pid)]
                                    )

                            logger.info("Update installer launched, exiting app...")
                            # Close the main window first so its QThread workers
                            # (Aria2Worker, MovieLoader, etc.) are stopped cleanly
                            # before QApplication.quit() ends the event loop.
                            try:
                                if parent and hasattr(parent, 'close'):
                                    parent.close()
                            except Exception:
                                pass
                            QApplication.quit()
                        except Exception as e:
                            logger.error(f"Failed to launch installer: {e}")
                            # Silent fail - don't bother the user with a dialog
                    else:
                        logger.info("No updates available")
                except Exception as e:
                    logger.warning(f"Update handling failed: {e}")

            # Post handling back to main Qt thread
            QTimer.singleShot(0, _handle)
        except Exception as e:
            logger.debug(f"Update worker failed: {e}")

    import threading
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def main():
    """Main application entry point"""
    logger.info(f"Starting Streamore Monitor v{Config.VERSION} (Delta Patch Test Ready)...")
    
    # Enable high DPI scaling - MUST be before QApplication
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Streamore Monitor")
    app.setOrganizationName("Streamore")
    
    # Load translations based on saved settings
    try:
        settings = QSettings('yts-monitor', 'yts-movie-monitor')
        lang = settings.value('language', None, type=str)
        if lang:
            translator = QTranslator()
            # Look for translations in common locations (patch, frozen, and source)
            candidates = []
            
            # 1. Local/Relative Patch Path (highest priority)
            patch_path = os.environ.get('APP_PATCH_PATH')
            if not patch_path:
                # In Dev/Source mode, check if _src_patches exists in root
                dev_patch = project_root / '_src_patches'
                if dev_patch.exists():
                    patch_path = str(dev_patch)
                    # Add to path for dev convenience if not already there
                    if patch_path not in sys.path:
                        sys.path.insert(0, patch_path)
            
            if patch_path:
                p = Path(patch_path)
                candidates.append(p / 'translations')
                candidates.append(p / 'frontend' / 'resources' / 'translations')

            # 2. Bundled paths
            if getattr(sys, 'frozen', False):
                try:
                    meipass = Path(sys._MEIPASS)  # type: ignore
                    candidates.append(meipass / 'translations')
                    candidates.append(meipass / 'frontend' / 'resources' / 'translations')
                except Exception:
                    pass
            
            # 3. Source paths
            candidates.append(project_root / 'frontend' / 'resources' / 'translations')
            candidates.append(project_root / 'resources' / 'translations')

            found = None
            for c in candidates:
                try:
                    p = Path(c)
                    if not p.exists():
                        continue
                    for name in (f"{lang}.qm", f"app_{lang}.qm", f"movie_{lang}.qm"):
                        f = p / name
                        if f.exists():
                            found = str(f)
                            break
                except Exception:
                    continue
                if found:
                    break

            if found and translator.load(found):
                app.installTranslator(translator)
                logger.info(f"Loaded translator for {lang}: {found}")
            else:
                logger.info(f"No translator found for {lang}")
    except Exception:
        pass

    # Create and show main window
    window = MainWindow()
    window.show()

    # Ensure all QThread workers are cleanly stopped whenever the event loop ends
    # (e.g. QApplication.quit() called by the update handler, or normal close).
    app.aboutToQuit.connect(window.close)

    logger.info("Application started successfully")
    
    # Check for updates immediately (non-blocking)
    QTimer.singleShot(0, lambda: check_for_updates(window))
    
    # Run event loop — catch KeyboardInterrupt (Ctrl+C / watcher SIGINT) so the
    # terminal doesn't print a confusing traceback on clean shutdown.
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down cleanly.")
        try:
            window.close()
        except Exception:
            pass
        sys.exit(0)


if __name__ == '__main__':
    main()
