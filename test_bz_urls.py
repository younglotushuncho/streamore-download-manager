
from curl_cffi import requests
from bs4 import BeautifulSoup

def test_url_variations():
    # Attempt to find the correct path structure for yts.bz
    variations = [
        # Standard: query/quality/genre/rating/order/year/lang
        "https://yts.bz/browse-movies/0/all/all/0/latest/2010/all",
        # Swapped: query/quality/genre/rating/year/order/lang
        "https://yts.bz/browse-movies/0/all/all/0/2010/latest/all",
        # No keyword: quality/genre/rating/order/year/lang
        "https://yts.bz/browse-movies/all/all/0/latest/2010/all",
        # Lang as 'en' standard:
        "https://yts.bz/browse-movies/0/all/all/0/latest/2010/en",
    ]
    
    for url in variations:
        print(f"\nTesting URL: {url}")
        try:
            resp = requests.get(url, impersonate="chrome110", timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Look for "720p 2010 YIFY Movies" in the header
            header = soup.select_one('h1')
            if header:
                print(f"Header: {header.text.strip()}")
            
            # Check first few movies
            cards = soup.select('div.browse-movie-wrap')
            print(f"Found {len(cards)} cards")
            for i, card in enumerate(cards[:3]):
                title = card.select_one('a.browse-movie-title').text.strip()
                year = card.select_one('.browse-movie-year').text.strip()
                print(f"[{i+1}] {title} ({year})")
                
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    test_url_variations()
