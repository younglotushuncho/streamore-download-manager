
import logging
from curl_cffi import requests
from bs4 import BeautifulSoup

def test_bz_filters():
    base = "https://yts.bz"
    # Try different URL patterns for filtering
    tests = [
        # Pattern: /browse-movies/[keywords]/[quality]/[genre]/[rating]/[order_by]/[year]/[language]
        f"{base}/browse-movies/0/all/all/0/latest/2010/en",
        f"{base}/browse-movies/0/all/all/0/latest/2024/en",
        f"{base}/browse-movies/0/720p/all/0/latest/2024/en",
        # Pattern without '0' first:
        f"{base}/browse-movies/all/all/0/latest/2024/en",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for url in tests:
        print(f"\n--- Testing URL: {url} ---")
        try:
            # impersonate chrome to avoid basic bot detection
            resp = requests.get(url, headers=headers, impersonate="chrome110", timeout=15)
            print(f"Status: {resp.status_code}")
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Check h1
            h1 = soup.select_one('h1')
            if h1:
                print(f"H1 Header: {h1.text.strip()}")
            
            # Check if any movies are found
            cards = soup.select('div.browse-movie-wrap')
            print(f"Found {len(cards)} movie cards.")
            
            for i, card in enumerate(cards[:5]):
                title_elem = card.select_one('a.browse-movie-title')
                year_elem = card.select_one('.browse-movie-year')
                title = title_elem.text.strip() if title_elem else "Unknown"
                year = year_elem.text.strip() if year_elem else "????"
                print(f" [{i+1}] {title} ({year})")
        
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_bz_filters()
