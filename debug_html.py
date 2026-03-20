"""
Check what HTML we're actually receiving from YTS
"""
from backend.scraper import YTSScraper
from bs4 import BeautifulSoup

scraper = YTSScraper()
movie_url = "https://yts.bz/movies/super-shark-2011"

print(f"Fetching: {movie_url}")
response = scraper._make_request(movie_url)

if not response:
    print("No response!")
    exit(1)

print(f"Status: {response.status_code}")
print(f"URL: {response.url}")
print(f"Content length: {len(response.text)}")
print("=" * 80)

# Save full HTML for inspection
with open('debug_page.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print("Saved full HTML to debug_page.html")

# Check for key indicators
soup = BeautifulSoup(response.text, 'html.parser')
print("\nSearching for torrent-related elements:")
print("-" * 80)

# Check for modal-torrent divs
modals = soup.select('div.modal-torrent')
print(f"div.modal-torrent: {len(modals)} found")

# Check for any divs with 'modal' in class
all_modals = soup.find_all('div', class_=lambda x: x and 'modal' in x)
print(f"Divs with 'modal' in class: {len(all_modals)}")
if all_modals:
    print("Classes found:")
    for m in all_modals[:5]:
        print(f"  - {m.get('class')}")

# Check for download buttons/links
download_links = soup.find_all('a', href=lambda x: x and 'download' in x.lower())
print(f"\nLinks with 'download' in href: {len(download_links)}")
for link in download_links[:10]:
    print(f"  - {link.get('href', '')[:100]}")

# Check for magnet links
magnets = soup.find_all('a', href=lambda x: x and x.startswith('magnet:'))
print(f"\nMagnet links: {len(magnets)}")

# Check if page title is correct
title = soup.select_one('title')
print(f"\nPage title: {title.text if title else 'N/A'}")

# Check if we got a Cloudflare challenge page
if 'cloudflare' in response.text.lower() or 'checking your browser' in response.text.lower():
    print("\n⚠️ WARNING: Might be a Cloudflare challenge page!")

# Check first 1000 chars
print("\nFirst 1000 chars of body:")
print("-" * 80)
body = soup.body
if body:
    print(body.get_text()[:1000])
else:
    print(response.text[:1000])
