
from curl_cffi import requests
from bs4 import BeautifulSoup

def inspect_card_html():
    url = "https://yts.bz/browse-movies/0/all/all/0/latest/0/all"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, impersonate="chrome110")
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    # Try finding move cards
    cards = soup.select('div.browse-movie-wrap')
    print(f"Found {len(cards)} cards with 'div.browse-movie-wrap'")
    
    if cards:
        print("\nHTML of first card:")
        print(cards[0].prettify()[:1000])
    else:
        # Try finding title and go up
        title = soup.select_one('a.browse-movie-title')
        if title:
            print("\nFound title element, printing its parent:")
            print(title.parent.prettify()[:1000])

if __name__ == "__main__":
    inspect_card_html()
