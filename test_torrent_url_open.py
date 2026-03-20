"""Test what happens when opening a .torrent URL with os.startfile"""
import os
import sys
import time

test_url = "https://yts.bz/torrent/download/4ECA6CD134DA7DCEA2B3B844E2AA0D1FFE9D05111"

print("🔍 Testing .torrent URL opening behavior...\n")
print(f"URL: {test_url}\n")
print("=" * 60)

if sys.platform == 'win32':
    print("Platform: Windows")
    print("\nMethod: os.startfile()")
    print("\nAttempting to open .torrent URL...")
    print("This should:")
    print("  1. Open default browser")
    print("  2. Browser downloads .torrent file")
    print("  3. File saved to Downloads folder\n")
    
    try:
        print("Calling os.startfile()...")
        os.startfile(test_url)
        print("✓ os.startfile() returned successfully!")
        print("\nWaiting 3 seconds to see what happens...")
        time.sleep(3)
        
        print("\n" + "=" * 60)
        print("RESULT:")
        print("=" * 60)
        print("✓ Command executed without error")
        print("\nCheck if:")
        print("  1. Browser opened? (Chrome, Edge, Firefox, etc.)")
        print("  2. .torrent file downloading?")
        print("  3. File in C:\\Users\\LOTUS\\Downloads\\?")
        
        print("\n💡 If nothing happened:")
        print("  - Windows might be blocking the download")
        print("  - Browser might have popup blocker enabled")
        print("  - Try opening this URL manually:")
        print(f"    {test_url}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        
else:
    print(f"Platform: {sys.platform}")
    print("This test is for Windows only")
