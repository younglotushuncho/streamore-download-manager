import time
import requests
import json
import os
import subprocess
from pathlib import Path

# Constants
API_BASE_URL = "http://127.0.0.1:5000/api"
TEST_MAGNET = "magnet:?xt=urn:btih:08ada5a7a610a5675b214b79b0a7b57b0c555b40&dn=Sintel&tr=udp%3A%2F%2Fexplodie.org%3A6969&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80"

def check_backend_running():
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_backend():
    print("🚀 Starting backend server...")
    # Using python -m backend.app to ensure imports work correctly
    # Redirecting output to log file
    log_file = open("backend_test.log", "w", encoding="utf-8")
    process = subprocess.Popen(
        ["python", "backend/app.py"],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    
    # Wait for backend to start
    for i in range(20):
        if check_backend_running():
            print("✅ Backend is running!")
            return process
        time.sleep(1)
    
    print("❌ Failed to start backend within 20 seconds.")
    return None

def test_download():
    # 1. Start backend if needed
    backend_proc = None
    if not check_backend_running():
        backend_proc = start_backend()
        if not backend_proc:
            return

    try:
        # 2. Add magnet link
        print(f"📥 Adding test download: Sintel...")
        payload = {
            "movie_id": "test_sintel",
            "movie_title": "Sintel (Test)",
            "quality": "1080p",
            "magnet_link": TEST_MAGNET,
            "organize_by_genre": False
        }
        
        response = requests.post(f"{API_BASE_URL}/download/start", json=payload)
        if response.status_code != 200:
            print(f"❌ Failed to start download: {response.text}")
            return
            
        data = response.json()
        download_id = data.get("download_id")
        print(f"✅ Download started! ID: {download_id}")

        # 3. Monitor progress
        print("\n📊 Monitoring progress (60 seconds)...")
        print("-" * 60)
        print(f"{'Progress':<10} | {'Speed':<12} | {'Peers':<6} | {'Status':<12}")
        print("-" * 60)
        
        for _ in range(30): # 30 * 2s = 60s
            try:
                # Check downloads via API
                resp = requests.get(f"{API_BASE_URL}/downloads")
                if resp.status_code == 200:
                    downloads = resp.json().get("downloads", [])
                    # Find our download
                    target = next((d for d in downloads if d["id"] == download_id), None)
                    
                    if target:
                        prog = target.get("progress", 0)
                        speed = target.get("download_rate", 0) / 1024 / 1024 # MB/s
                        peers = target.get("num_peers", 0)
                        status = target.get("state", "unknown")
                        
                        print(f"{prog:>8.1f}% | {speed:>8.2f} MB/s | {peers:>6} | {status:<12}", end="\r")
                        
                        if prog >= 100 or status == "completed":
                            print(f"\n✅ Download finished!")
                            break
                    else:
                        print(f"⚠️ Download {download_id} not found in list", end="\r")
            except Exception as e:
                print(f"Error polling: {e}")
                
            time.sleep(2)
        
        print("\n\nTest complete.")
        
        # 4. Clean up (Optional: comment out if you want to keep the download)
        # print("🧹 Cleaning up test download...")
        # requests.post(f"{API_BASE_URL}/download/{download_id}/cancel", json={"delete_files": True})
        
    finally:
        if backend_proc:
            print("🛑 Stopping backend server...")
            backend_proc.terminate()

if __name__ == "__main__":
    test_download()
