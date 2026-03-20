import requests

# Correct hash from website (40 chars)
correct_url = "https://yts.bz/torrent/download/5826DC2904F26EAFC7E29F2931122B436E41BCB6"

# Wrong hash app is using (41 chars - extra 1 at end)
wrong_url = "https://yts.bz/torrent/download/5826DC2904F26EAFC7E29F2931122B436E41BCB61"

print("Testing CORRECT hash (from website HTML):")
print(f"URL: {correct_url}")
try:
    r = requests.get(correct_url, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        is_torrent = r.content[:11] == b'd8:announce'
        print(f"Valid .torrent file: {is_torrent}")
        print(f"Size: {len(r.content)} bytes")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*60 + "\n")

print("Testing WRONG hash (app is using - has extra '1'):")
print(f"URL: {wrong_url}")
try:
    r = requests.get(wrong_url, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print("Valid .torrent file!")
    else:
        print(f"Response: {r.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
