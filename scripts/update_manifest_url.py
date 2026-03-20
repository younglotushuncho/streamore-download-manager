"""Update manifest with the actual GitHub release asset URL."""
import os
import sys
import json
import requests


def main():
    token = os.environ['GITHUB_TOKEN']
    owner, repo = os.environ['GITHUB_REPOSITORY'].split('/')
    tag = os.environ['TAG']
    
    headers = {'Authorization': f'token {token}'}
    r = requests.get(
        f'https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}',
        headers=headers
    )
    r.raise_for_status()
    
    release = r.json()
    assets = release.get('assets', [])
    name = f"StreamoreMonitor-{tag}.zip"
    
    url = None
    for a in assets:
        if a.get('name') == name:
            url = a.get('browser_download_url')
            break
    
    if not url:
        print(f'Error: Asset {name} not found in release', file=sys.stderr)
        sys.exit(1)
    
    with open('manifest.json', 'r') as f:
        manifest = json.load(f)
    
    manifest['assets'][0]['url'] = url
    
    with open('manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f'Updated manifest.json with URL: {url}')


if __name__ == '__main__':
    main()
