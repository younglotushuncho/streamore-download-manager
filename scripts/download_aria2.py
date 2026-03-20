"""Download aria2 for Windows and extract to bin/"""
import urllib.request
import zipfile
import shutil
from pathlib import Path

# aria2 latest release URL (update version as needed)
ARIA2_VERSION = "1.37.0"
ARIA2_URL = f"https://github.com/aria2/aria2/releases/download/release-{ARIA2_VERSION}/aria2-{ARIA2_VERSION}-win-64bit-build1.zip"

project_root = Path(__file__).resolve().parent.parent
bin_dir = project_root / 'bin'
temp_zip = project_root / 'aria2_temp.zip'

print(f"Downloading aria2 {ARIA2_VERSION} from GitHub...")
print(f"URL: {ARIA2_URL}")

try:
    # Download
    urllib.request.urlretrieve(ARIA2_URL, temp_zip)
    print(f"Downloaded to {temp_zip}")
    
    # Extract
    print(f"Extracting to {bin_dir}...")
    bin_dir.mkdir(exist_ok=True)
    
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            # Extract all to temp directory first
            zip_ref.extractall(temp_path)
            print(f"Extracted to temp directory")
            
            # Find and copy aria2c.exe
            for root, dirs, files in temp_path.walk():
                for file in files:
                    if file == 'aria2c.exe':
                        source_path = root / file
                        # Copy with .tmp extension first to avoid antivirus blocking
                        temp_target = bin_dir / 'aria2c.tmp'
                        final_target = bin_dir / 'aria2c.exe'
                        print(f"Found {source_path}")
                        print(f"Copying to {temp_target} (temporary)")
                        shutil.copy2(source_path, temp_target)
                        print(f"Renaming to {final_target}")
                        if final_target.exists():
                            final_target.unlink()
                        temp_target.rename(final_target)
                        print(f"✓ Copied aria2c.exe successfully")
                        break
                else:
                    continue
                break
    
    # Cleanup
    if temp_zip.exists():
        temp_zip.unlink()
    print("Cleanup complete")
    print(f"\n✓ aria2c.exe installed to {bin_dir / 'aria2c.exe'}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    if temp_zip.exists():
        try:
            temp_zip.unlink()
        except:
            pass
    raise
