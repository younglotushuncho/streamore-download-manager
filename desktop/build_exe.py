import subprocess
import os
import sys
import shutil
from pathlib import Path

# â”€â”€â”€ Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
APP_NAME = "StreamoreManager"
ENTRY_POINT = "desktop/downloader_app.py"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _add_data_arg(path: Path, target: str) -> str:
    # PyInstaller on Windows expects "SRC;DEST" for --add-data.
    return f"--add-data={path};{target}"

def _ensure_aria2c_bin():
    """Ensure aria2c binary exists under ./bin so it gets bundled."""
    bin_dir = PROJECT_ROOT / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target_name = "aria2c.exe" if os.name == "nt" else "aria2c"
    target = bin_dir / target_name
    if target.exists():
        return
    found = shutil.which("aria2c")
    if not found:
        print("Warning: aria2c not found on PATH and bin is missing; downloads will fail.")
        return
    try:
        shutil.copy(found, target)
        print(f"Copied aria2c from {found} to {target}")
    except Exception as e:
        print(f"Warning: Failed to copy aria2c from {found} to {target}: {e}")

def build():
    print(f"--- Starting Build for {APP_NAME} ---")
    
    # Target directories
    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build"
    desktop_icon = PROJECT_ROOT / "desktop" / "icon.ico"
    root_icon = PROJECT_ROOT / "icon.ico"
    chosen_icon = desktop_icon if desktop_icon.exists() else (root_icon if root_icon.exists() else None)
    icon_path = str(chosen_icon) if chosen_icon else ""
    entry_path = str(PROJECT_ROOT / ENTRY_POINT)
    
    # 1. Clear old builds
    print("Cleaning old build folders...")
    for d in [dist_dir, build_dir]:
        if d.exists():
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"Warning: Could not delete {d}: {e}")
    
    # 2. Locate the python executable in the env
    py_exe = str(PROJECT_ROOT / "env" / "Scripts" / "python.exe")
    if not os.path.exists(py_exe):
        py_exe = "python" # fallback
    _ensure_aria2c_bin()

    # 3. PyInstaller command
    # We use --collect-all for PyQt6 to ensure all DLLs and plugins are grabbed.
    cmd = [
        py_exe, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",           # Create a folder containing the exe and dependencies
        f"--name={APP_NAME}",
        "--paths", str(PROJECT_ROOT),
    ]

    # Build GUI mode by default so end users never see a terminal window.
    if os.getenv('STREAMORE_DEBUG_CONSOLE') == '1':
        print('Debug console enabled (STREAMORE_DEBUG_CONSOLE=1).')
    else:
        cmd.append('--windowed')
    if chosen_icon:
        cmd.append(f"--icon={icon_path}")
    else:
        print("Warning: No icon.ico found (desktop/icon.ico or icon.ico). Building without custom icon.")

    # Core data directories. Some repos/runners may not include all of them.
    data_dirs = [
        (PROJECT_ROOT / "backend", "backend"),
        (PROJECT_ROOT / "shared", "shared"),
        (PROJECT_ROOT / "bin", "bin"),  # optional in CI
    ]
    for src_path, dest_name in data_dirs:
        if src_path.exists():
            cmd.append(_add_data_arg(src_path, dest_name))
        else:
            print(f"Warning: Optional data directory not found, skipping: {src_path}")

    cmd.extend([
        # Force PyInstaller to find PyQt6 DLLs correctly.
        "--collect-all", "PyQt6",
        # Ensure HTTP client stack is bundled even when optional imports are used.
        "--collect-all", "requests",
        # Exclude QtWebEngine components (not used, avoids missing QtWebEngineProcess)
        "--exclude-module", "PyQt6.QtWebEngineCore",
        "--exclude-module", "PyQt6.QtWebEngineWidgets",
        "--exclude-module", "PyQt6.QtWebEngineQuick",
        # Bundle backend code as importable modules in frozen mode.
        "--hidden-import", "backend.app",
        "--collect-submodules", "backend",
        "--collect-submodules", "shared",
        "--hidden-import", "engineio.async_drivers.threading",
        "--hidden-import", "urllib3",
        "--hidden-import", "idna",
        "--hidden-import", "charset_normalizer",
        "--hidden-import", "certifi",
        entry_path
    ])
    
    print(f"Running PyInstaller: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
        print("\n--- PyInstaller Build Complete! ---")
        
        # Copy icon into the dist folder (for Inno Setup)
        if chosen_icon and os.path.exists(icon_path):
            shutil.copy(icon_path, dist_dir / APP_NAME / "icon.ico")
            
    except subprocess.CalledProcessError as e:
        print(f"\nError during PyInstaller build: {e}")
        sys.exit(1)

    # 4. Build the Installer (Inno Setup)
    print("\n--- Starting Installer Build (Inno Setup) ---")
    iscc = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    iss_file = PROJECT_ROOT / "desktop" / "installer.iss"
    
    if not os.path.exists(iscc):
        print(f"Warning: ISCC.exe not found at {iscc}. Skipping installer creation.")
        return

    try:
        print(f"Running: {iscc} {iss_file}")
        subprocess.run([iscc, str(iss_file)], check=True)
        print("\n--- INSTALLER CREATED SUCCESSFULLY! ---")
        print(f"Check the 'desktop/Output' folder for StreamoreSetup.exe")
    except subprocess.CalledProcessError as e:
        print(f"\nError during Inno Setup build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()



