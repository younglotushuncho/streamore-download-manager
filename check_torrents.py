"""Check which movies have torrents"""
import requests

r = requests.get('http://127.0.0.1:5000/api/movies', params={'limit': 20})
movies = r.json()['movies']

print('Checking movies for torrents...\n')

found_any = False
for m in movies:
    tc = len(m.get('torrents', []))
    title = m['title'][:35].ljust(35)
    print(f'{title} - {tc} torrents')
    
    if tc > 0:
        print(f'  ✓ Movie ID: {m["id"]}')
        print(f'  ✓ Qualities: {", ".join([t.get("quality", "?") for t in m["torrents"]])}')
        found_any = True

if not found_any:
    print('\n❌ No movies have torrents in database!')
    print('💡 The frontend will auto-fetch from YTS when you click a movie.')
    print('💡 Or click "🔄 Refresh Torrents" button in the dialog.')
