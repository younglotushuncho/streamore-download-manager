"""
Auto-update installer script.

This script is launched by the main app after downloading an update.
It waits for the old app to close, replaces it with the new version, 
and launches the new version.
"""
import sys
import time
import shutil
import subprocess
from pathlib import Path
import psutil


def wait_for_process_exit(pid: int, timeout: int = 30):
    """Wait for a process to exit."""
    try:
        process = psutil.Process(pid)
        for _ in range(timeout * 10):  # Check every 100ms
            if not process.is_running():
                return True
            time.sleep(0.1)
        return False
    except psutil.NoSuchProcess:
        # Process already exited
        return True


def install_update(new_exe: str, old_exe: str, old_pid: int):
    """Install update by replacing old exe with new exe."""
    new_exe = Path(new_exe)
    old_exe = Path(old_exe)
    
    print(f"Waiting for old process (PID {old_pid}) to exit...")
    if not wait_for_process_exit(old_pid):
        print(f"Warning: Process {old_pid} did not exit within timeout")
    
    # Additional safety delay
    time.sleep(1)
    
    # If the "old_exe" path does not look like a Windows executable (e.g. running
    # in development mode where current_exe is a .py script), do not attempt to
    # replace it. Instead simply launch the downloaded new executable and exit.
    try:
        if not new_exe.exists():
            print(f"New executable not found: {new_exe}")
            sys.exit(1)

        if old_exe.suffix.lower() != '.exe' or not old_exe.exists():
            # Development or non-executable scenario: just launch the new exe
            print("Old executable not present or not an .exe — launching new executable directly.")
            try:
                subprocess.Popen([str(new_exe)], cwd=str(new_exe.parent))
                print("Launched new executable. Exiting installer.")
                sys.exit(0)
            except Exception as e:
                print(f"Failed to launch new executable: {e}")
                sys.exit(1)

        # Backup and replace the real executable
        backup_path = old_exe.with_suffix('.exe.bak')
        if old_exe.exists():
            print(f"Backing up old executable to {backup_path}")
            shutil.copy2(old_exe, backup_path)

        print(f"Copying new executable to {old_exe}")
        shutil.copy2(new_exe, old_exe)

        print(f"Launching new version: {old_exe}")
        subprocess.Popen([str(old_exe)], cwd=str(old_exe.parent))

        # Clean up backup after successful launch
        time.sleep(2)
        if backup_path.exists():
            try:
                backup_path.unlink()
            except Exception:
                pass

        print("Update installed successfully!")
    except Exception as e:
        print(f"Error during update: {e}")
        # Try to restore from backup
        try:
            if 'backup_path' in locals() and backup_path.exists() and not old_exe.exists():
                print("Restoring from backup...")
                shutil.copy2(backup_path, old_exe)
        except Exception:
            pass
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: install_update.py <new_exe> <old_exe> <old_pid>")
        sys.exit(1)
    
    new_exe = sys.argv[1]
    old_exe = sys.argv[2]
    old_pid = int(sys.argv[3])
    
    install_update(new_exe, old_exe, old_pid)
