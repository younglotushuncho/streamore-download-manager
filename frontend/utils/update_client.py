import os
import sys

# --- PERMANENT SSL FIX ---
# Import shared.sanitize so stale SSL env vars are cleaned before requests is loaded.
try:
    import shared.sanitize
except ImportError:
    # Fallback if running in isolation
    for _v in ['SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE']:
        _p = os.environ.get(_v)
        if _p and '_MEI' in _p and not os.path.exists(_p):
            os.environ.pop(_v, None)
    try:
        import certifi as _c
        os.environ.setdefault('SSL_CERT_FILE', _c.where())
        os.environ.setdefault('REQUESTS_CA_BUNDLE', _c.where())
    except Exception:
        pass
# -------------------------

import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
import requests
import certifi

from shared.version import __version__

logger = logging.getLogger(__name__)

REPO_OWNER = "younglotushuncho"
REPO_NAME  = "moviedownloader"


def _ca():
    """Return the best available CA bundle path."""
    ca = os.environ.get('SSL_CERT_FILE') or os.environ.get('REQUESTS_CA_BUNDLE')
    if ca and os.path.isfile(ca):
        return ca
    try:
        return certifi.where()
    except Exception:
        return True


def _get(url, **kwargs):
    """requests.get wrapper that always uses the correct CA bundle."""
    kwargs.setdefault('verify', _ca())
    kwargs.setdefault('timeout', 15)
    return requests.get(url, **kwargs)


def _get_latest_release() -> dict:
    """Fetch the latest GitHub release JSON."""
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    resp = _get(api_url)
    resp.raise_for_status()
    return resp.json()


def _find_installer_asset(release: dict) -> Optional[dict]:
    """Find the Setup.exe asset in a release."""
    for asset in release.get('assets', []):
        name = asset.get('name', '').lower()
        if name.endswith('.exe') and ('setup' in name or 'installer' in name or 'install' in name):
            return asset
    # Fallback: any .exe
    for asset in release.get('assets', []):
        if asset.get('name', '').lower().endswith('.exe'):
            return asset
    return None


def _parse_version(v: str) -> tuple:
    try:
        return tuple(map(int, str(v).lstrip('v').split('.')))
    except Exception:
        return (0,)


def check_for_updates(progress_callback=None) -> Optional[dict]:
    """Check GitHub for a newer version. If found, download and launch the installer.

    Returns:
        None  — already up to date or check failed silently.
        dict  — {'version': ..., 'installer_path': ...} if installer is ready to run.
    """
    try:
        release = _get_latest_release()
    except Exception as e:
        logger.warning(f"Update check failed (network): {e}")
        return None

    latest_tag = release.get('tag_name', '').lstrip('v')
    if not latest_tag:
        return None

    if _parse_version(latest_tag) <= _parse_version(__version__):
        logger.info(f"Already on latest version {__version__}")
        return None

    logger.info(f"New version available: {latest_tag} (current: {__version__})")

    # Find the Setup.exe installer asset
    asset = _find_installer_asset(release)
    if not asset:
        logger.warning("No installer (.exe) asset found in the latest release.")
        return None

    download_url = asset.get('browser_download_url')
    asset_name   = asset.get('name', f'Setup-{latest_tag}.exe')
    asset_size   = asset.get('size', 0)

    if not download_url:
        return None

    # Download to a temp folder
    dest_dir = Path(tempfile.gettempdir()) / "StreamoreUpdate"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / asset_name

    logger.info(f"Downloading installer: {asset_name} ({asset_size // 1024 // 1024} MB)...")

    try:
        with _get(download_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(downloaded, total)
    except Exception as e:
        logger.error(f"Failed to download installer: {e}")
        return None

    logger.info(f"Installer downloaded to: {dest}")
    return {
        'version': latest_tag,
        'installer_path': str(dest),
        'asset_name': asset_name,
    }


def launch_installer(installer_path: str):
    """Launch the downloaded installer and close the app."""
    logger.info(f"Launching installer: {installer_path}")
    try:
        # Launch the Inno Setup installer with flags to forcefully update and restart
        cmd = [
            installer_path,
            '/SILENT',                # Show progress dialog, but no wizard pages
            '/CLOSEAPPLICATIONS',     # Automatically close the running app (releases file locks)
            '/RESTARTAPPLICATIONS'    # Restarts the app after installation finishes
        ]
        
        if sys.platform == 'win32':
            subprocess.Popen(
                cmd,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:
            subprocess.Popen(cmd)
    except Exception as e:
        logger.error(f"Failed to launch installer: {e}")
        raise
