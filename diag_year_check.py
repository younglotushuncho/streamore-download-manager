
import sys, os, logging
sys.path.append(os.getcwd())
logging.basicConfig(level=logging.ERROR)

from backend.scraper import YTSScraper

scraper = YTSScraper()

all_movies = []
for pg in range(1, 6):  # 5 pages
    url = f"https://yts.bz/browse-movies/0/720p/all/0/latest/2026/en?page={pg}"
    soup = scraper._make_request(url)
    cards = soup.select('div.browse-movie-wrap')
    print(f"Page {pg}: {len(cards)} cards")
    for card in cards:
        data = scraper._parse_movie_card(card)
        if data:
            all_movies.append(data)

print(f"\nTotal scraped: {len(all_movies)}")

# Check years
from collections import Counter
years = Counter(m['year'] for m in all_movies)
print(f"Year distribution: {dict(years)}")

# After strict filter for year=2026
filtered = [m for m in all_movies if str(m.get('year','')).strip() == '2026']
print(f"After strict year==2026 filter: {len(filtered)} remain")

# Show discarded
discarded = [m for m in all_movies if str(m.get('year','')).strip() != '2026']
if discarded:
    print(f"\nDiscarded movies (wrong year):")
    for m in discarded:
        print(f"  {m['title']} -> year='{m['year']}'")
