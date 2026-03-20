import requests

url = "https://yts.bz/torrent/download/5D465A878D2F7DD4FB49928A340261FB37F53914"

print(f"Testing URL: {url}")
print("-" * 60)

try:
    r = requests.get(url, timeout=10, allow_redirects=True)
    print(f"Status Code: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
    print(f"Content-Length: {r.headers.get('Content-Length', 'N/A')}")
    print(f"Final URL (after redirects): {r.url}")
    print("-" * 60)
    
    if r.status_code == 200:
        # Check if it's actually a .torrent file
        if r.content[:11] == b'd8:announce':  # .torrent files start with this
            print("✓ Valid .torrent file!")
            print(f"Size: {len(r.content)} bytes")
        else:
            print("Response content (first 500 chars):")
            print(r.text[:500])
    else:
        print("Response content (first 500 chars):")
        print(r.text[:500])
        
except Exception as e:
    print(f"Error: {e}")
