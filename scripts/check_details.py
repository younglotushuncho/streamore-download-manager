import sys, json
sys.path.insert(0, '.')
from frontend.utils.api_client import APIClient

url = 'https://yts.bz/movies/accused-the-karen-read-story-2026'
client = APIClient()
res = client.get_movie_details_by_url(url)
print('REQUEST URL:', url)
print('RESPONSE:')
print(json.dumps(res, indent=2, ensure_ascii=False))
