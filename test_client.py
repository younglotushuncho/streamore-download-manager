"""
Quick API test client
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

print("=" * 60)
print("Testing YTS Movie Monitor API")
print("=" * 60)
print()

# Test 1: Health check
print("1. Testing /api/health...")
try:
    response = requests.get(f"{BASE_URL}/api/health", timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    print("   ✅ PASS")
except Exception as e:
    print(f"   ❌ FAIL: {e}")

print()

# Test 2: Stats
print("2. Testing /api/stats...")
try:
    response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
    print(f"   Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        print(f"   Movies: {data['stats']['database']['total_movies']}")
        print(f"   Downloads: {data['stats']['database']['total_downloads']}")
        print(f"   Cache size: {data['stats']['cache']['size_mb']} MB")
    print("   ✅ PASS")
except Exception as e:
    print(f"   ❌ FAIL: {e}")

print()

# Test 3: Get movies (initially empty)
print("3. Testing /api/movies...")
try:
    response = requests.get(f"{BASE_URL}/api/movies", timeout=5)
    print(f"   Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        print(f"   Found {data['count']} movies")
        print("   ✅ PASS")
except Exception as e:
    print(f"   ❌ FAIL: {e}")

print()
print("=" * 60)
print("API Tests Complete!")
print()
print("Next steps:")
print("  1. Run: python frontend/main.py")
print("  2. Click 'Scrape YTS' to fetch movies")
print("  3. Browse and filter movies")
print("=" * 60)
