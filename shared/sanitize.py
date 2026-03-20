"""
Global environment sanitation utility for Streamore Monitor.
Ensures that stale environment variables (like SSL paths from temporary PyInstaller folders)
do not break the application.
"""
import os
import sys
from pathlib import Path

def sanitize_ssl_env():
    """ Clean up SSL environment variables if they point to non-existent paths. """
    changed = False
    for env_var in ['SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE']:
        path = os.environ.get(env_var)
        if path:
            # Check if path contains the characteristic PyInstaller temp folder pattern
            is_stale_mei = "_MEI" in path and "\\Temp\\" in path
            
            if not os.path.exists(path) or is_stale_mei:
                # Forcefully remove invalid or suspicious temp paths
                os.environ.pop(env_var, None)
                changed = True

    # If in frozen mode, ensure we use the internal CA bundle
    if getattr(sys, 'frozen', False):
        _meipass = getattr(sys, '_MEIPASS', None)
        if _meipass:
            _ca = os.path.join(_meipass, 'certifi', 'cacert.pem')
            if os.path.isfile(_ca):
                os.environ['SSL_CERT_FILE'] = _ca
                os.environ['REQUESTS_CA_BUNDLE'] = _ca
                changed = True

    # Final verification: if still missing or invalid, use certifi fallback
    curr_ca = os.environ.get('SSL_CERT_FILE')
    if not curr_ca or not os.path.exists(curr_ca):
        try:
            import certifi
            _ca_bundle = certifi.where()
            if _ca_bundle and os.path.isfile(_ca_bundle):
                os.environ['SSL_CERT_FILE'] = _ca_bundle
                os.environ['REQUESTS_CA_BUNDLE'] = _ca_bundle
                changed = True
        except Exception:
            pass
            
    return changed

# Run immediately on import
sanitize_ssl_env()
