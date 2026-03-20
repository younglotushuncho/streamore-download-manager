
from curl_cffi import requests
from bs4 import BeautifulSoup

def inspect_user_url_html():
    url = "https://yts.bz/browse-movies/0/720p/all/0/latest/2026/en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, impersonate="chrome110")
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    # Try finding move cards
    cards = soup.select('div.browse-movie-wrap')
    print(f"URL: {url}")
    print(f"Found {len(cards)} cards with 'div.browse-movie-wrap'")
    
    if len(cards) == 0:
        # If 0 cards found, print first 2000 chars to see structure
        print("\nStructure doesn't match! First 2000 chars of HTML:")
        print(resp.text[:2000])
        
        # Try finding ANY link with 'browse-movie-' in class
        links = soup.find_all('a', class_=lambda x: x and 'browse-movie-' in x)
        print(f"\nFound {len(links)} links with 'browse-movie-' in class.")
        for l in links[:5]:
            print(f" - Link: {l.get('class')} Text: {l.text.strip()}")

if __name__ == "__main__":
    inspect_user_url_html()
