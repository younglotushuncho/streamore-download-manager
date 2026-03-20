import sys
sys.path.insert(0, '.')
from frontend.utils.api_client import APIClient

client = APIClient()
print('API base_url=', client.base_url)
res = client.browse_scrape(keyword='', quality='720p', genre='all', rating=0, year='2026', order_by='latest', page=1, max_pages=50)
if res is None:
    print('ERROR: API call failed or backend unreachable')
    sys.exit(2)

raw = len(res)
strict = sum(1 for m in res if str(m.get('year')) == '2026')
others = [m for m in res if str(m.get('year')) != '2026']
print(f'raw_scraped={raw}')
print(f'strict_year_2026={strict}')
print(f'non2026_count={len(others)}')

for m in others[:5]:
    print(f"- {m.get('title')} ({m.get('year')})  {m.get('yts_url')}")
