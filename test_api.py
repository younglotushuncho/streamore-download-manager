"""
Quick test script to verify backend API endpoints
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.app import app

print("=" * 60)
print("YTS Movie Monitor - API Endpoints")
print("=" * 60)
print()

# List all routes
routes = []
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        routes.append({
            'endpoint': rule.rule,
            'methods': methods,
            'function': rule.endpoint
        })

# Sort by endpoint
routes.sort(key=lambda x: x['endpoint'])

print(f"Total endpoints: {len(routes)}")
print()

for route in routes:
    print(f"  {route['methods']:<12} {route['endpoint']}")

print()
print("=" * 60)
print("Backend is ready to start!")
print()
print("To run the server:")
print("  python backend/app.py")
print()
print("To test an endpoint:")
print("  curl http://127.0.0.1:5000/api/health")
print("=" * 60)
