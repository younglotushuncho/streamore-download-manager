import subprocess
import time
import requests
import sys

def run_test():
    print("🚀 Starting Streamore Backend for Smoke Test...")
    
    # Start the backend server as a background subprocess
    # We pipe stdout and stderr to capture crashes
    process = subprocess.Popen(
        [sys.executable, "backend/app.py"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    
    # Wait precisely 4 seconds. If there's a typo, Flask crashes instantly.
    time.sleep(4)
    
    # Check if the process died already (e.g. SyntaxError or Port in Use)
    if process.poll() is not None:
        print("❌ Smoke test failed! The backend crashed immediately on startup.")
        out, err = process.communicate()
        print("\n--- Crash Log ---")
        print(err.decode())
        sys.exit(1)
        
    # If it's still running, let's hit the health API
    try:
        print("📡 Pinging /api/health...")
        response = requests.get("http://127.0.0.1:58432/api/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ Smoke test passed! Backend is healthy and responding.")
            process.terminate()
            sys.exit(0)
        else:
            print(f"❌ Smoke test failed! Unexpected status code: {response.status_code}")
            process.terminate()
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print("❌ Smoke test failed! The server is running but the port is unreachable (did it bind to 58432?).")
        process.terminate()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Smoke test failed! Unknown error: {e}")
        process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    run_test()
