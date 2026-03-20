
import logging
from curl_cffi import requests
from bs4 import BeautifulSoup

def test_bz_pagination():
    url = "https://yts.bz/browse-movies/0/720p/all/0/latest/2024/en?page=2"
    headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" }
    try:
        resp = requests.get(url, headers=headers, impersonate="chrome110", timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        cards = soup.select('div.browse-movie-wrap')
        print(f"Page 2 cards: {len(cards)}")
        if cards:
            title = card.select_one('a.browse-movie-title').text.strip()
            print(f" First movie on page 2: {title}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bz_pagination()
