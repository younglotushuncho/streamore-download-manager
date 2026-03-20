
import logging
from curl_cffi import requests
from bs4 import BeautifulSoup

def test_exact_user_url():
    url = "https://yts.bz/browse-movies/0/720p/all/0/latest/2026/en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, impersonate="chrome110", timeout=15)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.content, 'html.parser')
        h1 = soup.select_one('h1')
        print(f"Header: {h1.text.strip() if h1 else 'None'}")
        cards = soup.select('div.browse-movie-wrap')
        print(f"Total cards: {len(cards)}")
        for i, card in enumerate(cards[:10]):
            title = card.select_one('a.browse-movie-title').text.strip()
            year = card.select_one('.browse-movie-year').text.strip()
            print(f" [{i+1}] {title} ({year})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_exact_user_url()
