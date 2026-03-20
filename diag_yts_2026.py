
import logging
import sys
import os
from curl_cffi import requests
from bs4 import BeautifulSoup

# Add the current directory to sys.path so we can import backend
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)

def diag_scrape():
    url = "https://yts.bz/browse-movies/0/720p/all/0/latest/2026/en"
    print(f"Fetching {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    resp = requests.get(url, headers=headers, impersonate="chrome110", timeout=15)
    print(f"Status: {resp.status_code}")
    
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    # Check H1 or H2 for filter info
    h1 = soup.select_one('h1')
    if h1:
        print(f"H1 Header: {h1.text.strip()}")
    
    h2 = soup.select_one('h2')
    if h2:
        print(f"H2 Header: {h2.text.strip()}")

    # Count movies
    cards = soup.select('div.browse-movie-wrap')
    print(f"Found {len(cards)} movie cards.")
    
    for i, card in enumerate(cards[:5]):
        title_elem = card.select_one('a.browse-movie-title')
        year_elem = card.select_one('.browse-movie-year')
        title = title_elem.text.strip() if title_elem else "Unknown"
        year = year_elem.text.strip() if year_elem else "????"
        link = title_elem.get('href') if title_elem else "N/A"
        print(f" [{i+1}] {title} ({year}) -> {link}")

if __name__ == "__main__":
    diag_scrape()
