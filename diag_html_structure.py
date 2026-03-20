
import sys
import os
from curl_cffi import requests
from bs4 import BeautifulSoup

def diag_html():
    url = "https://yts.bz/browse-movies/0/720p/all/0/latest/2026/en"
    print(f"Fetching {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, impersonate="chrome110", timeout=15)
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    cards = soup.select('div.browse-movie-wrap')
    print(f"Found {len(cards)} cards")
    
    if cards:
        card = cards[0]
        print("\n--- FIRST CARD HTML STRUCTURE ---")
        # Print all children summary
        for i, child in enumerate(card.find_all(recursive=False)):
            print(f"Child {i}: {child.name} class={child.get('class')}")
        
        # Look for the internal tags
        print("\nDetail info:")
        title = card.select_one('a.browse-movie-title')
        if title:
            print(f"Title: {title.text.strip()} (class={title.get('class')})")
        
        year = card.select_one('.browse-movie-year')
        if year:
            print(f"Year: {year.text.strip()} (class={year.get('class')})")
        
        # All h4 tags
        h4s = card.select('h4')
        for i, h in enumerate(h4s):
            print(f"H4[{i}]: text='{h.text.strip()}' class={h.get('class')}")

if __name__ == "__main__":
    diag_html()
