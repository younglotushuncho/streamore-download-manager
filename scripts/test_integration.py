"""
Complete end-to-end test for the download manager integration
"""
import requests
import json
import time

BASE_URL = 'http://127.0.0.1:5000'

def test_health():
    """Test backend health"""
    print("=" * 60)
    print("1. Testing Backend Health")
    print("=" * 60)
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"Status: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}")
        return r.status_code == 200
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def test_aria2_status():
    """Test aria2 status endpoint"""
    print("\n" + "=" * 60)
    print("2. Testing aria2 Status")
    print("=" * 60)
    try:
        r = requests.get(f"{BASE_URL}/api/aria2/status", timeout=5)
        print(f"Status: {r.status_code}")
        data = r.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if data.get('success'):
            print(f"\n✓ aria2 is running!")
            print(f"  Version: {data.get('version')}")
            print(f"  Active: {data.get('active_downloads')}")
            print(f"  Download Speed: {data.get('download_speed')} B/s")
            return True
        else:
            print(f"\n✗ aria2 error: {data.get('error')}")
            return False
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def test_start_download():
    """Test starting a download"""
    print("\n" + "=" * 60)
    print("3. Testing Download Start")
    print("=" * 60)
    
    test_data = {
        'movie_id': 'integration-test-001',
        'movie_title': 'Integration Test Movie',
        'quality': '1080p',
        'magnet_link': 'magnet:?xt=urn:btih:fedcba9876543210fedcba9876543210fedcba98&dn=IntegrationTest'
    }
    
    try:
        print(f"Sending: {json.dumps(test_data, indent=2)}")
        r = requests.post(
            f"{BASE_URL}/api/download/start",
            json=test_data,
            timeout=10
        )
        print(f"\nStatus: {r.status_code}")
        data = r.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if data.get('success'):
            print(f"\n✓ Download started!")
            print(f"  Download ID (GID): {data.get('download_id')}")
            return data.get('download_id')
        else:
            print(f"\n✗ Download failed: {data.get('error')}")
            return None
    except Exception as e:
        print(f"FAILED: {e}")
        return None

def test_list_downloads():
    """Test listing downloads"""
    print("\n" + "=" * 60)
    print("4. Testing Download List")
    print("=" * 60)
    try:
        r = requests.get(f"{BASE_URL}/api/downloads", timeout=5)
        print(f"Status: {r.status_code}")
        data = r.json()
        
        if data.get('success'):
            count = data.get('count', 0)
            print(f"\n✓ Found {count} download(s)")
            
            for i, dl in enumerate(data.get('downloads', []), 1):
                print(f"\n  Download #{i}:")
                print(f"    Title: {dl.get('movie_title')}")
                print(f"    Quality: {dl.get('quality')}")
                print(f"    State: {dl.get('state')}")
                print(f"    Progress: {dl.get('progress')}%")
                print(f"    GID: {dl.get('id')}")
            
            return count > 0
        else:
            print(f"\n✗ Failed: {data.get('error')}")
            return False
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "YTS Movie Monitor - Integration Test" + " " * 11 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = {}
    
    # Test 1: Health
    results['health'] = test_health()
    time.sleep(0.5)
    
    # Test 2: aria2 Status
    results['aria2'] = test_aria2_status()
    time.sleep(0.5)
    
    # Test 3: Start Download
    download_id = test_start_download()
    results['start'] = download_id is not None
    time.sleep(1)
    
    # Test 4: List Downloads
    results['list'] = test_list_downloads()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name.upper():20} {status}")
    
    all_passed = all(results.values())
    print("\n" + ("=" * 60))
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nThe download manager is working correctly!")
        print("\nNext steps:")
        print("  1. Start the frontend: python -m frontend.main")
        print("  2. Click on a movie card")
        print("  3. Click 'Download Selected'")
        print("  4. Switch to 'Downloads' tab")
        print("  5. Watch your download appear with live progress!")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease check:")
        print("  - Is the backend running? (python -m backend.app)")
        print("  - Is aria2c running on port 6800?")
        print("  - Check backend logs for errors")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    exit(main())
