import requests, json, sys

BASE = 'http://127.0.0.1:5000'

def main():
    start_url = BASE + '/api/download/start'
    downloads_url = BASE + '/api/downloads'
    data = {
        'movie_id': 'auto-test-001',
        'movie_title': 'Auto Test Movie',
        'quality': '720p',
        'magnet_link': 'magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=AutoTest'
    }
    try:
        r = requests.post(start_url, json=data, timeout=10)
        print('POST /api/download/start ->', r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text)
    except Exception as e:
        print('POST failed:', e)

    try:
        r2 = requests.get(downloads_url, timeout=5)
        print('\nGET /api/downloads ->', r2.status_code)
        try:
            print(json.dumps(r2.json(), indent=2))
        except Exception:
            print(r2.text)
    except Exception as e:
        print('GET failed:', e)

if __name__ == '__main__':
    main()
