from backend.scraper import YTSScraper
from backend.database import get_db
from shared.models import Movie
import time

url = 'https://yts.bz/browse-movies/the%20rip/all/all/0/latest/0/all'
print(f"Fetching and importing movies from: {url}")

scraper = YTSScraper()
soup = scraper._make_request(url)
if not soup:
    print('Failed to fetch the URL')
    exit(1)

cards = soup.select(scraper.YTS_SELECTORS['movie_cards']) if hasattr(scraper, 'YTS_SELECTORS') else soup.select('div.browse-movie-wrap')
# Use the shared selectors from shared.constants
from shared.constants import YTS_SELECTORS
cards = soup.select(YTS_SELECTORS['movie_cards'])
print(f'Found {len(cards)} movie cards on the search URL')

movies = []
for card in cards:
    md = scraper._parse_movie_card(card)
    if md:
        movies.append(md)

print(f'Parsed {len(movies)} movies, adding to DB...')

db = get_db()
added = 0
for m in movies:
    try:
        movie_obj = Movie.from_dict(m)
        db.add_movie(movie_obj)
        added += 1
    except Exception as e:
        print('Failed to add movie:', m.get('title'), e)

print(f'Added {added} movies to database')

# Wait briefly and then print search results via API
import requests, json
time.sleep(1)
r = requests.get('http://127.0.0.1:5000/api/movies', params={'search':'the rip','limit':50})
print('API search status:', r.status_code)
print(json.dumps({'count': r.json().get('count'), 'titles': [m.get('title') for m in r.json().get('movies',[])]}, indent=2))
