import sys

file_path = r'f:\Softwares\projects\movie project\backend\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# I'll identify the start of reset_download_engine and the start of get_movie
# and replace everything in between with a known good version.

start_marker = "def reset_download_engine():"
end_marker = "@app.route('/api/movie/<movie_id>', methods=['GET'])"

start_idx = text.find(start_marker)
end_idx = text.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Error: Markers not found. start={start_idx}, end={end_idx}")
    sys.exit(1)

new_middle = """def reset_download_engine():
    \"\"\"Reset/recover aria2 download engine\"\"\"
    try:
        from backend.downloader import get_manager
        manager = get_manager()
        if not manager: return jsonify({'success': False, 'error': 'aria2 manager not available'}), 503
        out = manager.reset_engine()
        return jsonify({'success': out.get('success', False), 'message': out.get('message', 'Reset done')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        db_stats = db.get_stats()
        return jsonify({'success': True, 'stats': {'database': db_stats}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    try:
        movies = db.get_watchlist()
        m_list = [m.to_dict() for m in movies]
        for m in m_list: m['is_on_watchlist'] = True
        return jsonify({'success': True, 'count': len(m_list), 'movies': m_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/watchlist/toggle', methods=['POST'])
def toggle_watchlist():
    try:
        mid = request.json.get('movie_id')
        res = db.toggle_watchlist(mid)
        return jsonify({'success': True, 'is_on_watchlist': res})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/movies', methods=['GET'])
def get_movies():
    try:
        genre = request.args.get('genre', 'All')
        movies = db.get_all_movies(genre=genre)
        return jsonify({'success': True, 'count': len(movies), 'movies': [m.to_dict() for m in movies]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/movie/details-by-url', methods=['GET'])
def get_movie_details_by_url():
    try:
        yts_url = request.args.get('yts_url', '').strip()
        if not yts_url: return jsonify({'success': False, 'error': 'Missing url'}), 400
        details = scraper.scrape_movie_details(yts_url) if scraper else None
        if not details: return jsonify({'success': False, 'error': 'Failed to scrape'}), 500
        return jsonify({'success': True, **details})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

"""

final_text = text[:start_idx] + new_middle + text[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(final_text)

print("Restoration successful")
