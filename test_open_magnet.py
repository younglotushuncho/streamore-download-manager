"""Test opening a real magnet link using the same code as the dialog"""
import sys
import os
import subprocess
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Get the real magnet from Super Shark
import requests
r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 20})
movies = r.json()['movies']

magnet = None
movie_title = None
for m in movies:
    if m.get('torrents') and len(m['torrents']) > 0:
        magnet = m['torrents'][0].get('magnet_link')
        movie_title = m['title']
        quality = m['torrents'][0].get('quality')
        break

if not magnet:
    print("❌ No magnet found")
    exit(1)

print(f"🎬 Testing download for: {movie_title} ({quality})")
print(f"📏 Magnet length: {len(magnet)} chars")
print(f"🔍 Preview: {magnet[:80]}...\n")

# Use the same opener logic as movie_details.py
def open_with_system(target: str):
    """Same logic as MovieDetailsDialog._open_with_system"""
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    
    # Clean target
    if not target:
        raise ValueError('Empty target')
    clean_target = target.strip().replace('\r', '').replace('\n', '')
    
    print(f"✓ Cleaned magnet length: {len(clean_target)} chars")
    
    if sys.platform == 'win32':
        try:
            logger.debug(f"Opening target via os.startfile: {clean_target[:80]}...")
            os.startfile(clean_target)
            print("✅ SUCCESS: Opened with os.startfile")
            return
        except Exception as e:
            logger.warning(f"os.startfile failed: {e}; falling back to cmd start")
            print(f"⚠️  os.startfile failed: {e}")
            
            # Fallback to cmd start
            try:
                quoted = '"' + clean_target.replace('"', '\\"') + '"'
                cmd = f'start "" {quoted}'
                print(f"Trying cmd start with quoted magnet...")
                subprocess.Popen(cmd, shell=True)
                print("✅ SUCCESS: Opened with cmd start")
                return
            except Exception as e2:
                logger.error(f"cmd start fallback failed: {e2}; attempting .magnet file fallback")
                print(f"⚠️  cmd start failed: {e2}")
                
                # Final fallback: .magnet file
                try:
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.magnet', mode='w', encoding='utf-8')
                    tmp.write(clean_target)
                    tmp.close()
                    logger.debug(f"Created temporary magnet file: {tmp.name}")
                    print(f"Created temp file: {tmp.name}")
                    os.startfile(tmp.name)
                    print("✅ SUCCESS: Opened .magnet file")
                    return
                except Exception as e3:
                    logger.exception(f"Final magnet file fallback failed: {e3}")
                    print(f"❌ FAILED: All methods failed")
                    raise
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', clean_target])
        print("✅ SUCCESS: Opened with 'open' (macOS)")
    else:
        subprocess.Popen(['xdg-open', clean_target])
        print("✅ SUCCESS: Opened with 'xdg-open' (Linux)")

print("=" * 60)
print("Attempting to open magnet in qBittorrent...")
print("=" * 60)

try:
    open_with_system(magnet)
    print("\n✅ Magnet launched successfully!")
    print("   Check qBittorrent - it should show the torrent being added")
    print(f"   Movie: {movie_title}")
except Exception as e:
    print(f"\n❌ Failed to open magnet: {e}")
    print("\n💡 Try manual test:")
    print("   1. Copy the magnet above")
    print("   2. Open qBittorrent → File → Add torrent link (Ctrl+U)")
    print("   3. Paste and click OK")
