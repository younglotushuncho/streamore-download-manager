"""
Flask API server for YTS Movie Monitor
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import shared.sanitize  # Force environment sanitation early

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import threading
import time
import os
import re
from datetime import datetime

from backend.config import Config
from backend.database import get_db
try:
    from backend.scraper import YTSScraper
    SCRAPER_IMPORT_ERROR = ''
except Exception as e:
    YTSScraper = None
    SCRAPER_IMPORT_ERROR = str(e)
from backend.poster_cache import get_poster_cache
from shared.models import Movie, Torrent
from shared.models import Download
from backend.downloader import get_manager
from shared.constants import (
    DOWNLOAD_STATE_QUEUED,
    DOWNLOAD_STATE_DOWNLOADING,
    DOWNLOAD_STATE_PAUSED,
    DOWNLOAD_STATE_COMPLETED,
    DOWNLOAD_STATE_ERROR
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security Hardening: Audit Logger
audit_logger = logging.getLogger('audit')
try:
    audit_handler = logging.FileHandler('audit.log')
    audit_handler.setFormatter(logging.Formatter('%(asctime)s - AUDIT - %(message)s'))
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
except Exception:
    pass

# Backend Error Tracking for Desktop Alerts
_INTERNAL_ERRORS = [] # List of (timestamp, message)

def log_internal_error(msg: str):
    """Log a critical error for the desktop app to display."""
    _INTERNAL_ERRORS.append((datetime.now().isoformat(), msg))
    if len(_INTERNAL_ERRORS) > 50:
        _INTERNAL_ERRORS.pop(0)

def apply_log_level(level_name: str):
    """Dynamically update the global log level."""
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR
    }
    level = levels.get(str(level_name).upper(), logging.INFO)
    logging.getLogger().setLevel(level)
    # Also update child loggers just in case
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).setLevel(level)
    logger.info(f"Log level dynamically updated to {level_name}")

# Create Flask app
app = Flask(__name__)

# Security Hardening: Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://"
)

def sanitize_download_path(path_str: str) -> str:
    """Security Hardening: Prevent directory traversal into sensitive OS folders."""
    import os
    from pathlib import Path
    try:
        if not path_str:
            return str(Path.home() / 'Downloads')
        p = Path(path_str).resolve()
        p_str = str(p).lower()
        # Block Windows/System32 or other highly sensitive roots
        if 'windows\\system32' in p_str or p_str.startswith('c:\\windows'):
            return str(Path.home() / 'Downloads')
        return str(p)
    except Exception:
        return str(Path.home() / 'Downloads')

# Use a strong secret key — set via SECRET_KEY env var in production
_secret = os.getenv('SECRET_KEY', 'streamore-dev-secret-change-me-in-prod')
app.config['SECRET_KEY'] = _secret

# CORS: allow specific origins in production via ALLOWED_ORIGINS env var
# e.g.  ALLOWED_ORIGINS=https://my-app.vercel.app,https://my-custom-domain.com
# In development, falls back to "*" (allow all)
_raw_origins = os.getenv('ALLOWED_ORIGINS', '')
_cors_origins = [o.strip() for o in _raw_origins.split(',') if o.strip()] or '*'
CORS(app, resources={r"/api/*": {"origins": _cors_origins}, r"/socket.io/*": {"origins": _cors_origins}})
# engineio requires its async driver to be importable at init-time.
# In PyInstaller bundles the threading driver must be explicitly imported first
# so that the frozen importer has it available before SocketIO is created.
import engineio.async_drivers.threading  # noqa: F401 – required for frozen builds
socketio = SocketIO(app, cors_allowed_origins=_cors_origins, async_mode='threading')

# Initialize components
db = get_db()
scraper = None
if YTSScraper:
    try:
        scraper = YTSScraper()
    except Exception as e:
        SCRAPER_IMPORT_ERROR = str(e)
        logger.warning(f"Scraper init failed: {e}")
poster_cache = get_poster_cache()

def _scraper_unavailable_response():
    return jsonify({
        'success': False,
        'error': 'Scraper unavailable',
        'details': SCRAPER_IMPORT_ERROR
    }), 503
# Initialize aria2 manager (if available) to start background poller
try:
    from backend.downloader import get_manager as _get_aria2_manager
    _aria2_manager = _get_aria2_manager()
    logger.info('aria2 manager initialized')
except Exception as e:
    logger.warning(f'Could not initialize aria2 manager: {e}')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/errors/latest', methods=['GET'])
def get_latest_errors():
    """Endpoint for desktop app to poll for critical backend errors."""
    return jsonify({
        'success': True,
        'errors': _INTERNAL_ERRORS
    })


@app.route('/')
@app.route('/downloads')
def desktop_ui():
    """
    Serve the standalone Download Manager UI for the desktop app window.
    Uses pywebview to load this page in a native OS window.
    """
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>YTS Download Manager</title>
  <script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0d0d1a; --bg-card: #13131f; --accent: #6c63ff;
      --success: #22c55e; --error: #ef4444; --warning: #f59e0b;
      --text: #f1f1f5; --text-secondary: #8b8b9e; --border: #1e1e2e;
    }
    body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; }
    .wrap { max-width: 900px; margin: 0 auto; padding: 32px 24px; }
    h1 { font-size: 26px; font-weight: 800; margin-bottom: 20px; display:flex; align-items:center; gap:10px; }
    .dot { width:10px; height:10px; border-radius:50%; background:var(--error); transition: background .3s; }
    .dot.live { background: var(--success); animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
    .tabs { display:flex; gap:8px; margin-bottom:20px; background:rgba(255,255,255,.03); border:1px solid var(--border); border-radius:12px; padding:4px; overflow-x:auto; }
    .tab { flex:1; min-width:fit-content; padding:10px 16px; border-radius:10px; border:none; background:transparent; color:var(--text-secondary); font-weight:600; font-size:13px; cursor:pointer; transition:.2s; }
    .tab.active { background:var(--accent); color:#fff; }
    .empty { text-align:center; padding:80px 20px; color:var(--text-secondary); background:var(--bg-card); border-radius:20px; border:1px solid var(--border); }
    .empty-icon { font-size:60px; margin-bottom:12px; }
    .list { display:flex; flex-direction:column; gap:12px; }
    .card { background:var(--bg-card); border:1px solid var(--border); border-radius:16px; padding:20px; }
    .card-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; }
    .title { font-weight:700; font-size:15px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; min-width:0; }
    .badge { font-size:12px; font-weight:600; padding:3px 10px; border-radius:20px; display:inline-block; margin-top:4px; }
    .pct { font-size:22px; font-weight:800; margin-left:16px; }
    .bar-bg { height:6px; background:rgba(255,255,255,.08); border-radius:3px; margin-bottom:10px; overflow:hidden; }
    .bar { height:100%; border-radius:3px; background:linear-gradient(90deg,var(--accent),#a78bfa); transition:width .5s; }
    .bar.done { background:var(--success); }
    .stats { display:flex; gap:20px; flex-wrap:wrap; font-size:13px; color:var(--text-secondary); margin-bottom:16px; }
    .actions { display:flex; gap:8px; flex-wrap:wrap; }
    .btn { padding:8px 14px; border-radius:10px; border:1px solid; font-size:13px; font-weight:600; cursor:pointer; transition:.2s; }
    .btn:hover { filter:brightness(1.2); }
  </style>
</head>
<body>
<div class="wrap">
  <h1>⬇️ Download Manager <div class="dot" id="dot"></div></h1>
  <div class="tabs" id="tabs">
    <button class="tab active" data-tab="all">📁 All <span id="cnt-all">0</span></button>
    <button class="tab" data-tab="downloading">⬇️ Downloading <span id="cnt-downloading">0</span></button>
    <button class="tab" data-tab="paused">⏸ Paused <span id="cnt-paused">0</span></button>
    <button class="tab" data-tab="completed">✅ Completed <span id="cnt-completed">0</span></button>
    <button class="tab" data-tab="error">❌ Errors <span id="cnt-error">0</span></button>
  </div>
  <div id="list"></div>
</div>

<script>
const API = '';
let downloads = [], activeTab = 'all';

const stateColor = { active:'#6c63ff', downloading:'#6c63ff', waiting:'#f59e0b', queued:'#f59e0b', complete:'#22c55e', completed:'#22c55e', error:'#ef4444', paused:'#64748b', pausing:'#64748b', removed:'#64748b' };
const stateLabel = { active:'⬇️ Downloading', downloading:'⬇️ Downloading', waiting:'⏳ Queued', queued:'⏳ Queued', complete:'✅ Complete', completed:'✅ Complete', error:'❌ Error', paused:'⏸ Paused', pausing:'⏸ Pausing', removed:'🗑 Removed' };

function fmt(b){ if(!b||b===0)return'0 B'; if(b<1024)return b+' B'; if(b<1048576)return(b/1024).toFixed(1)+' KB'; if(b<1073741824)return(b/1048576).toFixed(1)+' MB'; return(b/1073741824).toFixed(2)+' GB'; }
function fmtSpeed(b){ return b?fmt(b)+'/s':'0 B/s'; }

function filterDownloads(tab){
  return downloads.filter(d=>{
    if(tab==='all') return true;
    if(tab==='downloading') return ['active','downloading','waiting','queued'].includes(d.state);
    if(tab==='paused') return ['paused','pausing'].includes(d.state);
    if(tab==='completed') return ['complete','completed'].includes(d.state);
    if(tab==='error') return d.state==='error';
    return true;
  });
}

function render(){
  const tabs=['all','downloading','paused','completed','error'];
  tabs.forEach(t=>{ document.getElementById('cnt-'+t).textContent=filterDownloads(t).length; });
  const list=filterDownloads(activeTab);
  const el=document.getElementById('list');
  if(!list.length){ el.innerHTML=`<div class="empty"><div class="empty-icon">📭</div><p style="font-size:18px;font-weight:600;margin-bottom:8px">${activeTab==='all'?'No downloads yet':'No '+activeTab+' downloads'}</p><p style="font-size:14px">Browse movies and click Download to start</p></div>`; return; }
  el.innerHTML=list.map(d=>{
    const c=stateColor[d.state]||'#64748b';
    const done=d.state==='complete'||d.state==='completed';
    return `<div class="card">
      <div class="card-header">
        <div style="flex:1;min-width:0">
          <div class="title">${d.movie_title||'Unknown'}${d.quality?' · '+d.quality:''}</div>
          <span class="badge" style="background:${c}22;color:${c}">${stateLabel[d.state]||d.state}</span>
        </div>
        <div class="pct" style="color:${c}">${(d.progress||0).toFixed(1)}%</div>
      </div>
      <div class="bar-bg"><div class="bar${done?' done':''}" style="width:${d.progress||0}%"></div></div>
      <div class="stats">
        <span>📦 ${fmt(d.size_downloaded)} / ${fmt(d.size_total)}</span>
        ${d.download_rate>0?`<span>⬇ ${fmtSpeed(d.download_rate)}</span>`:''}
        ${d.upload_rate>0?`<span>⬆ ${fmtSpeed(d.upload_rate)}</span>`:''}
        ${d.num_peers>0?`<span>👥 ${d.num_peers} peers</span>`:''}
        ${d.num_seeds>0?`<span>🌱 ${d.num_seeds} seeds</span>`:''}
        ${d.eta>0&&['downloading','active'].includes(d.state)?`<span>⏱ ETA ${d.eta}s</span>`:''}
        ${d.error_message?`<span style="color:var(--error)">⚠ ${d.error_message}</span>`:''}
      </div>
      <div class="actions">
        ${done
          ?`<button class="btn" onclick="action('${d.id}','play')" style="color:#22c55e;border-color:#22c55e33;background:#22c55e15">▶️ Play</button>`
          :`<button class="btn" onclick="action('${d.id}','${d.state==='paused'?'resume':'pause'}')" style="color:${d.state==='paused'?'#6c63ff':'#f59e0b'};border-color:${d.state==='paused'?'#6c63ff33':'#f59e0b33'};background:${d.state==='paused'?'#6c63ff15':'#f59e0b15'}">${d.state==='paused'?'▶️ Resume':'⏸ Pause'}</button>`
        }
        <button class="btn" onclick="action('${d.id}','open-folder')" style="color:var(--accent);border-color:var(--accent)33;background:var(--accent)15">📂 Open Folder</button>
        <button class="btn" onclick="stop('${d.id}')" style="color:#ef4444;border-color:#ef444433;background:#ef444415">🛑 Stop</button>
      </div>
    </div>`;
  }).join('');
}

async function action(id, act){
  try{
    const r=await fetch(`${API}/api/download/${id}/${act}`,{method:'POST',headers:{'Content-Type':'application/json'},body:act==='cancel'?JSON.stringify({delete_files:true}):undefined});
    const d=await r.json(); if(!d.success) alert('Error: '+d.error);
  }catch(e){ alert('Failed: '+e); }
}
function stop(id){ if(confirm('Stop and remove this download?')) action(id,'cancel'); }

// Tabs
document.getElementById('tabs').addEventListener('click',e=>{
  const t=e.target.closest('.tab'); if(!t) return;
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  t.classList.add('active'); activeTab=t.dataset.tab; render();
});

// Socket.IO live updates
const socket = io(API, {transports:['websocket','polling']});
socket.on('connect',()=>document.getElementById('dot').className='dot live');
socket.on('disconnect',()=>document.getElementById('dot').className='dot');
socket.on('downloads_update', data=>{ downloads=data.downloads||[]; render(); });

// REST poll fallback every 5s
async function poll(){ try{ const r=await fetch(`${API}/api/downloads`); const d=await r.json(); if(d.downloads){downloads=d.downloads; render();} }catch{} }
poll(); setInterval(poll,5000);
</script>
</body>
</html>"""
    from flask import Response
    return Response(html, mimetype='text/html')


def proxy_poster():
    """Proxy or serve cached movie posters for the web frontend"""
    url = request.args.get('url')
    if not url:
        return "Missing URL", 400
        
    from flask import send_file
    import requests
    import os
    import io
    
    # Check if we have it in cache first
    cached_path = poster_cache.get_cached_path(url)
    if cached_path and os.path.exists(cached_path):
        return send_file(cached_path, mimetype='image/jpeg')
        
    # If not, download and cache it on the fly
    try:
        cache_fn = poster_cache.get_cache_filename(url)
        save_path = os.path.join(Config.POSTER_CACHE_DIR, cache_fn)
        if scraper and scraper.download_poster(url, save_path):
            return send_file(save_path, mimetype='image/jpeg')
            
        # Fallback to direct download and stream if saving fails
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        return send_file(io.BytesIO(r.content), mimetype=r.headers.get('Content-Type', 'image/jpeg'))
    except Exception as e:
        return "Failed to load poster", 500

@app.route('/api/shorten', methods=['GET'])
def shorten_link():
    """Generate an Ouo.io shortlink securely using the background API"""
    target = request.args.get('url')
    if not target:
        return jsonify({'error': 'URL required'}), 400
        
    from urllib.parse import quote
    import requests
    api_key = "k1e6VX2P"
    safe_url = quote(target, safe="")
    api_url = f"https://ouo.io/api/{api_key}?s={safe_url}"
    
    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        short_url = resp.text.strip()
        if "ouo" in short_url.lower():
            return jsonify({'success': True, 'short_url': short_url})
    except Exception as e:
        logger.error(f"Shortcut error: {e}")
        
    return jsonify({'success': False, 'error': 'Failed to shorten'}), 500


@app.route('/api/aria2/status', methods=['GET'])
def get_aria2_status():
    """Get aria2 daemon status and statistics"""
    try:
        manager = get_manager()
        if not manager:
            return jsonify({
                'success': False,
                'error': 'aria2 manager not available',
                'status': 'unavailable'
            }), 503

        # Try to get aria2 version
        try:
            version_info = manager._rpc_call('aria2.getVersion')
            if version_info:
                # Get global stats
                global_stats = manager._rpc_call('aria2.getGlobalStat')
                
                # Get active/waiting/stopped counts
                active = manager.tell_active() or []
                waiting = manager.tell_waiting(0, 1) or []
                stopped = manager.tell_stopped(0, 1) or []
                stalled_active = 0
                for it in active:
                    try:
                        speed = int(it.get('downloadSpeed', 0) or 0)
                        peers = int(it.get('numPeers', 0) or 0)
                        seeds = int(it.get('numSeeders', 0) or 0)
                        if speed <= 1024 and peers <= 1 and seeds <= 1:
                            stalled_active += 1
                    except Exception:
                        pass
                
                return jsonify({
                    'success': True,
                    'status': 'running',
                    'version': version_info.get('version', 'unknown'),
                    'enabled_features': version_info.get('enabledFeatures', []),
                    'global_stats': global_stats,
                    'active_downloads': len(active),
                    'waiting_downloads': global_stats.get('numWaiting', 0) if global_stats else 0,
                    'stopped_downloads': global_stats.get('numStopped', 0) if global_stats else 0,
                    'stalled_active_downloads': stalled_active,
                    'download_speed': global_stats.get('downloadSpeed', 0) if global_stats else 0,
                    'upload_speed': global_stats.get('uploadSpeed', 0) if global_stats else 0
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'aria2 RPC not responding',
                    'status': 'not_responding'
                }), 503
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'status': 'error'
            }), 503
            
    except Exception as e:
        logger.error(f"Error getting aria2 status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/engine/reset', methods=['POST'])
def reset_download_engine():
    """Reset/recover aria2 download engine"""
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

@app.route('/api/movie/<movie_id>', methods=['GET'])
def get_movie(movie_id):
    """Get a specific movie by ID"""
    try:
        movie = db.get_movie(movie_id)
        
        if not movie:
            return jsonify({
                'success': False,
                'error': 'Movie not found'
            }), 404
        
        return jsonify({
            'success': True,
            'movie': movie.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting movie {movie_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/movie/<movie_id>/fetch-torrents', methods=['POST'])
def fetch_movie_torrents(movie_id):
    if not scraper:
        return _scraper_unavailable_response()
    """
    Fetch fresh torrent data from YTS website for a specific movie
    This scrapes the movie detail page in real-time to get the latest torrents
    """
    try:
        # Get movie from database
        movie = db.get_movie(movie_id)
        
        if not movie:
            return jsonify({
                'success': False,
                'error': 'Movie not found'
            }), 404
        
        # Get YTS URL
        yts_url = movie.yts_url
        if not yts_url:
            return jsonify({
                'success': False,
                'error': 'No YTS URL available for this movie'
            }), 400
        
        logger.info(f"Fetching fresh torrents for: {movie.title} from {yts_url}")
        
        # Scrape the movie details page
        details = scraper.scrape_movie_details(yts_url)
        
        if not details:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch torrents from YTS'
            }), 500
        
        torrents = details.get('torrents', [])
        
        if not torrents:
            return jsonify({
                'success': True,
                'torrents': [],
                'message': 'No torrents available for this movie'
            })
        
        # Update movie in database with fresh torrents
        movie_dict = movie.to_dict()
        movie_dict['torrents'] = torrents
        if details.get('description'):
            movie_dict['description'] = details['description']
        if details.get('genres'):
            movie_dict['genres'] = details['genres']
        
        updated_movie = Movie.from_dict(movie_dict)
        db.add_movie(updated_movie)
        
        logger.info(f"Updated movie with {len(torrents)} torrents")
        
        return jsonify({
            'success': True,
            'torrents': torrents,
            'movie': updated_movie.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error fetching torrents for {movie_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scrape', methods=['POST'])
def scrape_movies():
    if not scraper:
        return _scraper_unavailable_response()
    """
    Scrape YTS for new movies
    
    JSON body:
        - page: Page number (default: 1)
        - genre: Genre filter (default: all)
        - quality: Quality filter (default: all)
        - year: Year filter (default: all)
        - fetch_details: Fetch full details (default: false)
    """
    try:
        data = request.get_json() or {}
        page = data.get('page', 1)
        genre = data.get('genre', 'all')
        quality = data.get('quality', 'all')
        year = data.get('year', 'all')
        fetch_details = data.get('fetch_details', False)
        
        logger.info(f"Scraping page {page} (genre={genre}, quality={quality}, year={year})")
        
        # Scrape browse page
        movies_data = scraper.scrape_browse_page(
            page=page,
            genre=genre,
            quality=quality,
            year=year
        )
        
        saved_count = 0
        for movie_dict in movies_data:
            try:
                # Fetch full details if requested
                if fetch_details:
                    details = scraper.scrape_movie_details(movie_dict['yts_url'])
                    if details:
                        movie_dict.update(details)
                
                # Download poster
                if movie_dict.get('poster_url'):
                    cached_path = poster_cache.get_cached_path(movie_dict['poster_url'])
                    if not cached_path:
                        # Not in cache, download it
                        cache_filename = poster_cache.get_cache_filename(movie_dict['poster_url'])
                        save_path = f"{Config.POSTER_CACHE_DIR}/{cache_filename}"
                        
                        if scraper.download_poster(movie_dict['poster_url'], save_path):
                            movie_dict['poster_local'] = save_path
                    else:
                        movie_dict['poster_local'] = cached_path
                
                # Create Movie object and save
                movie = Movie.from_dict(movie_dict)
                db.add_movie(movie)
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving movie {movie_dict.get('title')}: {e}")
                continue
        
        # Record scrape
        db.add_scrape_record(movies_found=len(movies_data), success=True)
        
        logger.info(f"Scraping complete: {saved_count}/{len(movies_data)} movies saved")
        
        return jsonify({
            'success': True,
            'found': len(movies_data),
            'saved': saved_count
        })
        
    except Exception as e:
        logger.error(f"Error scraping: {e}", exc_info=True)
        db.add_scrape_record(movies_found=0, success=False)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search/scrape', methods=['GET'])
def search_scrape():
    if not scraper:
        return _scraper_unavailable_response()
    """Scrape YTS for a free-text search and return results without saving to DB"""
    try:
        query = request.args.get('q')
        page = int(request.args.get('page', 1))
        if not query:
            return jsonify({'success': False, 'error': 'Missing query parameter'}), 400

        movies = scraper.scrape_search(query, page=page)
        return jsonify({'success': True, 'count': len(movies), 'movies': movies})
    except Exception as e:
        logger.error(f"Error in search_scrape: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/browse/scrape', methods=['GET'])
def browse_scrape():
    if not scraper:
        return _scraper_unavailable_response()
    """
    Scrape YTS browse page with filters (genre, year, quality) and return results without saving to DB.
    
    Query params match YTS website pattern:
        - keyword: search keyword (optional)
        - quality: '720p', '1080p', '2160p', 'all' (default: 'all')
        - genre: 'action', 'comedy', 'drama', etc. or 'all' (default: 'all')
        - rating: minimum rating 0-9 (default: 0)
        - year: year filter or '0'/'all' for all years (default: '0')
        - order_by: 'latest', 'rating', 'year', 'title' (default: 'latest')
        - page: starting page number (default: 1)
        - max_pages: maximum number of pages to scrape (default: 10 for all results)
    """
    try:
        keyword = request.args.get('keyword', '')
        quality = request.args.get('quality', 'all')
        genre = request.args.get('genre', 'all')
        rating = int(request.args.get('rating', 0))
        year = request.args.get('year', '0')
        order_by = request.args.get('order_by', 'latest')
        page = int(request.args.get('page', 1))
        max_pages = int(request.args.get('max_pages', 3))  # Default scrape up to 3 pages
        
        movies = scraper.scrape_browse_filtered(
            keyword=keyword,
            quality=quality,
            genre=genre,
            rating=rating,
            year=year,
            order_by=order_by,
            page=page,
            max_pages=max_pages
        )
        
        return jsonify({'success': True, 'count': len(movies), 'movies': movies})
    except Exception as e:
        logger.error(f"Error in browse_scrape: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/downloads', methods=['GET'])
def get_downloads():
    """
    Get all downloads – merges DB records with live aria2 data so that
    downloads present in aria2 but missing from the DB still show up.

    Query params:
        - state: Filter by state (optional)
    """
    try:
        state = request.args.get('state')
        db_downloads = db.get_all_downloads(state=None)  # fetch all; filter later

        def _safe_int(val, default=0):
            try:
                return int(val) if val is not None else default
            except (ValueError, TypeError):
                return default

        def _stall_info(it: dict) -> dict:
            status = str(it.get('status', '') or '').lower()
            speed = _safe_int(it.get('downloadSpeed', 0))
            peers = _safe_int(it.get('numPeers', 0))
            seeds = _safe_int(it.get('numSeeders', 0))
            err = str(it.get('errorMessage', '') or '').strip()
            completed = _safe_int(it.get('completedLength', 0))
            total = _safe_int(it.get('totalLength', 0))
            reason = ''
            is_stalled = False

            if err:
                is_stalled = True
                reason = err
            elif status in ('waiting', 'queued'):
                is_stalled = True
                reason = 'Queued (waiting for a free slot)'
            elif status == 'active':
                if speed <= 1024:
                    if peers <= 0 and seeds <= 0:
                        is_stalled = True
                        reason = 'No peers or seeds'
                    elif peers > 0 and completed == 0 and total > 0:
                        is_stalled = True
                        reason = 'Connected but not receiving pieces'
                    elif peers <= 1 and seeds <= 1:
                        is_stalled = True
                        reason = 'Very low peer availability'

            return {
                'is_stalled': bool(is_stalled),
                'stall_reason': reason,
                'aria2_status': status,
            }

        # Build a lookup of GIDs already tracked in DB
        db_gids = {d.id for d in db_downloads}

        # Map from aria2 status string -> our state string
        ARIA2_STATUS_MAP = {
            'active':   DOWNLOAD_STATE_DOWNLOADING,
            'waiting':  DOWNLOAD_STATE_QUEUED,
            'paused':   DOWNLOAD_STATE_PAUSED,
            'complete': DOWNLOAD_STATE_COMPLETED,
            'error':    DOWNLOAD_STATE_ERROR,
            'removed':  DOWNLOAD_STATE_ERROR,
        }

        # Fetch live aria2 downloads and create synthetic entries for unknowns
        synthetic = []
        aria2_diag_by_gid = {}
        try:
            manager = get_manager()
            if manager:
                aria2_items = []
                for it in (manager.tell_active() or []):
                    it['_src'] = 'active'
                    aria2_items.append(it)
                for it in (manager.tell_waiting(0, 1000) or []):
                    it['_src'] = 'waiting'
                    aria2_items.append(it)
                for it in (manager.tell_stopped(0, 1000) or []):
                    it['_src'] = 'stopped'
                    aria2_items.append(it)

                for it in aria2_items:
                    gid = it.get('gid')
                    if not gid or gid in db_gids:
                        if gid:
                            aria2_diag_by_gid[str(gid)] = _stall_info(it)
                        continue  # already tracked in DB – skip
                    # If this aria2 item is a follow-up to a DB-tracked metadata GID, skip it
                    following = it.get('following')
                    if following and str(following) in db_gids:
                        aria2_diag_by_gid[str(gid)] = _stall_info(it)
                        continue
                    followed_by = it.get('followedBy') or []
                    if followed_by and any(str(x) in db_gids for x in followed_by):
                        aria2_diag_by_gid[str(gid)] = _stall_info(it)
                        continue
                    aria2_diag_by_gid[str(gid)] = _stall_info(it)
                    # Determine state
                    aria2_status = it.get('status', '')
                    if it['_src'] == 'stopped' and aria2_status == 'complete':
                        mapped_state = DOWNLOAD_STATE_COMPLETED
                    else:
                        mapped_state = ARIA2_STATUS_MAP.get(aria2_status, DOWNLOAD_STATE_ERROR)

                    # Compute progress
                    try:
                        completed_len = int(it.get('completedLength', 0))
                        total_len = int(it.get('totalLength', 0))
                        progress = round(completed_len / total_len * 100.0, 2) if total_len > 0 else 0.0
                    except Exception:
                        progress = 0.0

                    # Try to extract a human-readable name from bittorrent metadata
                    bt_info = it.get('bittorrent', {})
                    bt_name = (bt_info.get('info') or {}).get('name', '') if bt_info else ''
                    display_name = bt_name or it.get('files', [{}])[0].get('path', '') or f'aria2:{gid}'

                    # Save path
                    files = it.get('files', [])
                    save_path = files[0].get('path', '') if files else ''
                    diag = aria2_diag_by_gid.get(str(gid), {})

                    synthetic.append({
                        'id': gid,
                        'movie_id': '',
                        'movie_title': display_name,
                        'quality': '',
                        'magnet_link': '',
                        'state': mapped_state,
                        'progress': progress,
                        'download_rate': _safe_int(it.get('downloadSpeed', 0)),
                        'upload_rate': _safe_int(it.get('uploadSpeed', 0)),
                        'eta': _safe_int(it.get('eta', 0)),
                        'size_total': _safe_int(it.get('totalLength', 0)),
                        'size_downloaded': _safe_int(it.get('completedLength', 0)),
                        'num_peers': _safe_int(it.get('numPeers', 0)),
                        'num_seeds': _safe_int(it.get('numSeeders', 0)),
                        'save_path': save_path,
                        'name': display_name,
                        'started_at': None,
                        'completed_at': None,
                        'error_message': it.get('errorMessage', '') or '',
                        'is_stalled': bool(diag.get('is_stalled', False)),
                        'stall_reason': diag.get('stall_reason', ''),
                        'aria2_status': diag.get('aria2_status', ''),
                    })
        except Exception as merge_err:
            logger.warning(f"Could not merge aria2 live data: {merge_err}")

        # Combine DB downloads + synthetic aria2-only ones
        all_dicts = []
        for d in db_downloads:
            row = d.to_dict()
            diag = aria2_diag_by_gid.get(str(row.get('id')), {})
            row['is_stalled'] = bool(diag.get('is_stalled', False))
            row['stall_reason'] = diag.get('stall_reason', '')
            row['aria2_status'] = diag.get('aria2_status', '')
            all_dicts.append(row)
        all_dicts.extend(synthetic)

        # Apply state filter if requested
        if state:
            all_dicts = [d for d in all_dicts if d.get('state') == state]

        return jsonify({
            'success': True,
            'count': len(all_dicts),
            'downloads': all_dicts
        })

    except Exception as e:
        logger.error(f"Error getting downloads: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>', methods=['GET'])
def get_download(download_id):
    """Get a specific download by ID"""
    try:
        download = db.get_download(download_id)
        if not download:
            return jsonify({'success': False, 'error': 'Download not found'}), 404
        return jsonify({'success': True, 'download': download.to_dict()})
    except Exception as e:
        logger.error(f"Error getting download {download_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/downloads/history', methods=['GET'])
def get_download_history():
    """Get persistent download history log"""
    try:
        limit = int(request.args.get('limit', 100))
        history = db.get_download_history(limit=limit)
        return jsonify({
            'success': True,
            'count': len(history),
            'history': history
        })
    except Exception as e:
        logger.error(f"Error getting download history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get aggregate statistics for the dashboard"""
    try:
        # Get up to 10,000 recent downloads for accurate stats
        history = db.get_download_history(limit=10000)
        total_downloads = len(history)
        completed = 0
        failed = 0
        total_size = 0
        
        for h in history:
            state = h.get('state', '').lower()
            if state in ('complete', 'completed', 'seeding'):
                completed += 1
                total_size += int(h.get('size_total') or 0)
            elif state == 'error':
                failed += 1
                
        trend = db.get_bandwidth_trend(days=7)
                
        return jsonify({
            'success': True,
            'stats': {
                'total_downloads': total_downloads,
                'completed': completed,
                'failed': failed,
                'total_bytes': total_size,
                'trend': trend
            }
        })
    except Exception as e:
        logger.error(f"Error getting analytics: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/start', methods=['POST'])
@limiter.limit("20 per minute") # Rate limit to prevent spam attacks
def start_download():
    """
    Start a new download.
    Expected JSON body:
        - movie_id: Movie ID
        - movie_title: Movie title
        - quality: Quality to download
        - magnet_link: Magnet link
    """
    try:
        data = request.get_json() or {}
        logger.info(f"Backend: /api/download/start called with data keys: {list(data.keys()) if data else 'None'}")
        
        # Validate required fields
        required = ['movie_id', 'movie_title', 'quality', 'magnet_link']
        for field in required:
            if field not in data:
                logger.warning(f"Backend: Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        logger.info(f"Backend: Starting download - movie_id={data['movie_id']}, title={data['movie_title']}, quality={data['quality']}")
        
        magnet_or_path = data['magnet_link'].strip().strip('"').strip("'")
        logger.debug(f"Backend: magnet_or_path={magnet_or_path[:80]}...")
        
        # Resolve runtime download settings from DB and sanitize them
        raw_path = db.get_setting('download_path', Config.DOWNLOAD_PATH) or Config.DOWNLOAD_PATH
        default_download_path = sanitize_download_path(raw_path)
        organize_setting = db.get_setting('organize_by_genre', 'true').lower() == 'true'
        organize_by_genre = data.get('organize_by_genre')
        if organize_by_genre is None:
            organize_by_genre = organize_setting
            
        audit_logger.info(f"DOWNLOAD_START: ip={request.remote_addr} movie_id={data['movie_id']} title='{data['movie_title']}' quality={data['quality']}")

        # Duplicate detection (smart)
        def _norm_source(val: str) -> str:
            if not val:
                return ''
            src = val.strip().lower()
            if src.startswith('magnet:'):
                m = re.search(r'xt=urn:btih:([^&]+)', src)
                if m:
                    return f'btih:{m.group(1)}'
            return src

        duplicate = None
        try:
            normalized = _norm_source(magnet_or_path)
            for existing in db.get_all_downloads():
                if not existing:
                    continue
                # Ignore errored downloads so the user can retry
                if (existing.state or '').lower() == DOWNLOAD_STATE_ERROR:
                    continue
                # Match by magnet/infohash or by movie_id + quality
                if normalized and _norm_source(existing.magnet_link or '') == normalized:
                    duplicate = existing
                    break
                if data.get('movie_id') and existing.movie_id == data.get('movie_id') and (existing.quality or '') == (data.get('quality') or ''):
                    duplicate = existing
                    break
        except Exception as dup_err:
            logger.debug(f"Duplicate detection skipped: {dup_err}")

        if duplicate:
            logger.info(f"Backend: Duplicate download blocked (existing id={duplicate.id})")
            return jsonify({
                'success': False,
                'error': 'Download already queued',
                'duplicate_id': duplicate.id,
                'duplicate_state': duplicate.state,
            }), 409

        # Use aria2 manager to add the download
        manager = get_manager()
        if not manager:
            logger.error("Backend: Download manager not available")
            return jsonify({'success': False, 'error': 'Download manager not available'}), 500
        if not manager.rpc_available():
            logger.error("Backend: aria2 RPC is not reachable")
            return jsonify({'success': False, 'error': 'aria2 RPC is not reachable. Please restart the Download Manager.'}), 503

        # TORRENT HEALTH CHECK: Pre-queue seed count validation
        try:
            available_seeds = int(data.get('seeds', 0))
            if available_seeds <= 0 and not data.get('force', False):
                logger.warning(f"Backend: Blocking download with 0 seeds (Health Check): {data.get('movie_title')}")
                return jsonify({
                    'success': False, 
                    'error': 'Torrent health check failed: 0 seeds reported. This download is likely stalled/dead. Choose another quality or use force start if you believe this is an error.'
                }), 400
        except (ValueError, TypeError):
            pass

        # Detect if it's a local file path or something to download (magnet/URL)
        from pathlib import Path
        is_file_path = False
        if not magnet_or_path.startswith('magnet:') and not magnet_or_path.startswith('http'):
            # If it doesn't look like a URI, check if it's a valid local file
            try:
                p = Path(magnet_or_path)
                if p.is_file() or p.exists():
                    is_file_path = True
            except Exception:
                pass

        
        # Compute genre-based folder and per-download save path if possible.
        # Strategy:
        #   1. Collect all genres for this movie.
        #   2. Use the FIRST genre as the real download directory (primary).
        #   3. Create a Windows directory junction inside every OTHER genre folder
        #      pointing at the primary folder so the movie appears in all
        #      its genres without duplicating data.
        save_dir = default_download_path
        if organize_by_genre:
            try:
                import json as _json
                import subprocess as _subprocess

                movie_obj = db.get_movie(data['movie_id']) if data.get('movie_id') else None

                def _sanitize_name(s: str) -> str:
                    """Strip characters forbidden in Windows path components."""
                    if not s:
                        return ''
                    invalid = '<>:"/\\|?*'
                    out = ''.join((c if c not in invalid else '_') for c in s)
                    return out.strip()[:200]

                def _safe_child(root: Path, *parts) -> Path:
                    """Build a path and verify it stays inside root (Windows-safe)."""
                    candidate = root.joinpath(*parts).resolve()
                    try:
                        if not candidate.is_relative_to(root):
                            raise ValueError(f"Path escapes root: {candidate}")
                    except AttributeError:  # Python < 3.9
                        if str(root) not in str(candidate):
                            raise ValueError(f"Path escapes root: {candidate}")
                    return candidate

                def _make_junction(link_path: Path, target_path: Path):
                    """Create a Windows directory junction (no admin required)."""
                    try:
                        if link_path.exists() or link_path.is_symlink():
                            return  # already set up
                        link_path.parent.mkdir(parents=True, exist_ok=True)
                        _subprocess.run(
                            ['cmd', '/c', 'mklink', '/J',
                             str(link_path), str(target_path)],
                            check=True,
                            capture_output=True
                        )
                        logger.info(f"Created junction: {link_path} -> {target_path}")
                    except Exception as je:
                        logger.debug(f"Junction creation failed ({link_path}): {je}")

                genres = []
                # Prefer genres from DB movie object when available
                if movie_obj and getattr(movie_obj, 'genres', None):
                    raw = movie_obj.genres
                    if isinstance(raw, str):
                        try:
                            raw = _json.loads(raw)
                        except Exception:
                            raw = [raw]
                    genres = [g.strip() for g in raw if g and g.strip()]

                # Fallback: accept genres provided in the API request (useful for live-scraped items)
                if not genres and data.get('genres'):
                    try:
                        raw2 = data.get('genres')
                        if isinstance(raw2, str):
                            try:
                                raw2 = _json.loads(raw2)
                            except Exception:
                                raw2 = [raw2]
                        genres = [g.strip() for g in (raw2 or []) if g and str(g).strip()]
                    except Exception:
                        genres = []

                root = Path(default_download_path).resolve()
                title = _sanitize_name(
                    data.get('movie_title') or
                    (getattr(movie_obj, 'title', '') if movie_obj else 'movie')
                )

                if genres:
                    # Only consider configured managed genres (order determines primary)
                    managed_cfg = getattr(Config, 'MANAGED_GENRES', []) or []
                    managed_lower = [g.lower() for g in managed_cfg]

                    # Normalize genres via canonical mapping (so Adventure/Crime/etc map to Action)
                    genre_map = getattr(Config, 'GENRE_CANONICAL_MAP', {}) or {}
                    mapped_genres = []
                    for g in genres:
                        if not g:
                            continue
                        key = g.strip().lower()
                        mapped = genre_map.get(key, g)
                        if mapped not in mapped_genres:
                            mapped_genres.append(mapped)

                    # Find which of the configured genres this movie belongs to (preserve configured order)
                    matches = []
                    for cfgg in managed_cfg:
                        for mg in mapped_genres:
                            if mg and mg.strip().lower() == cfgg.lower():
                                matches.append(cfgg)
                                break

                    if matches:
                        primary_genre = _sanitize_name(matches[0])
                        try:
                            primary_dir = _safe_child(root, primary_genre, title)
                            primary_dir.mkdir(parents=True, exist_ok=True)
                            save_dir = str(primary_dir)

                            # Create junctions for other matched managed genres (not for all movie genres)
                            for extra_cfg in matches[1:]:
                                eg = _sanitize_name(extra_cfg)
                                if not eg or eg == primary_genre:
                                    continue
                                try:
                                    junction = _safe_child(root, eg, title)
                                    _make_junction(junction, primary_dir)
                                except Exception as jex:
                                    logger.debug(f"Skipping junction for genre {eg}: {jex}")
                        except Exception:
                            save_dir = default_download_path

            except Exception as e:
                logger.debug(f"Failed to compute genre-based save_dir: {e}")

        if is_file_path:
            logger.info(f"Backend: Detected torrent file path, using add_torrent(): {magnet_or_path}; save_dir={save_dir}")
            gid = manager.add_torrent(magnet_or_path, save_path=save_dir)
        else:
            logger.info(f"Backend: Detected magnet link, using add_magnet(); save_dir={save_dir}")
            gid = manager.add_magnet(magnet_or_path, save_path=save_dir)
        
        if not gid:
            logger.error("Backend: Failed to add download to aria2")
            return jsonify({'success': False, 'error': 'Failed to add download to aria2'}), 500

        logger.info(f"Backend: aria2 returned gid={gid}")

        # Create Download object and save to DB using aria2 gid as id
        from datetime import datetime

        display_title = data.get('movie_title', 'Unknown')
        if display_title and ('/' in display_title or '\\' in display_title):
            import os
            display_title = os.path.basename(display_title)
        
        # Ensure we don't have empty strings for title
        if not display_title:
            display_title = 'Manual Download'

        download = Download(
            id=str(gid),
            movie_id=data['movie_id'],
            movie_title=display_title,
            quality=data['quality'],
            magnet_link=magnet_or_path,  # Can be either magnet link or torrent file path
            state=DOWNLOAD_STATE_DOWNLOADING,
            progress=0.0,
            download_rate=0.0,
            upload_rate=0.0,
            eta=0,
            size_total=0,
            size_downloaded=0,
            num_peers=0,
            num_seeds=0,
            save_path=save_dir,
            name=display_title, # Initialize with title, poller will improve it later
            started_at=datetime.now().isoformat(),
            completed_at=None,
            error_message=None
        )

        logger.info(f"Backend: Saving download to database with id={download.id}")
        db.add_download(download)
        logger.info(f"Backend: Download saved successfully")

        return jsonify({
            'success': True,
            'message': 'Download queued',
            'download_id': str(gid)
        })
        
    except Exception as e:
        logger.error(f"Error starting download: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/logs/export', methods=['GET'])
def export_logs():
    """Export the aria2 backend log for support."""
    try:
        from backend.downloader import _aria2_log_path
        log_path = _aria2_log_path()
        if log_path.exists():
            from flask import send_file
            return send_file(str(log_path), as_attachment=True, download_name='streamore_backend.log')
        return jsonify({'success': False, 'error': 'Log file not found'}), 404
    except Exception as e:
        logger.error(f"Failed to export logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>/pause', methods=['POST'])
def pause_download(download_id):
    """Pause a download"""
    try:
        manager = get_manager()
        if not manager:
            return jsonify({'success': False, 'error': 'Download manager not available'}), 500
        if not manager.rpc_available():
            logger.error("Backend: aria2 RPC is not reachable")
            return jsonify({'success': False, 'error': 'aria2 RPC is not reachable. Please restart the Download Manager.'}), 503

        # Call aria2 pause
        res = manager.pause(download_id)

        # Update DB state
        download = db.get_download(download_id)
        if download:
            download.state = DOWNLOAD_STATE_PAUSED
            db.add_download(download)

        return jsonify({'success': True, 'result': res})
    except Exception as e:
        logger.error(f"Error pausing download {download_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>/resume', methods=['POST'])
def resume_download(download_id):
    """Resume a download"""
    try:
        manager = get_manager()
        if not manager:
            return jsonify({'success': False, 'error': 'Download manager not available'}), 500
        if not manager.rpc_available():
            logger.error("Backend: aria2 RPC is not reachable")
            return jsonify({'success': False, 'error': 'aria2 RPC is not reachable. Please restart the Download Manager.'}), 503

        res = manager.resume(download_id)

        download = db.get_download(download_id)
        if download:
            download.state = DOWNLOAD_STATE_DOWNLOADING
            db.add_download(download)

        return jsonify({'success': True, 'result': res})
    except Exception as e:
        logger.error(f"Error resuming download {download_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>/force-start', methods=['POST'])
def force_start_download(download_id):
    """Force-start a queued download by pausing others if needed and moving it to top."""
    try:
        manager = get_manager()
        if not manager:
            return jsonify({'success': False, 'error': 'Download manager not available'}), 500
        if not manager.rpc_available():
            logger.error("Backend: aria2 RPC is not reachable")
            return jsonify({'success': False, 'error': 'aria2 RPC is not reachable. Please restart the Download Manager.'}), 503

        # Determine max concurrent from settings (fallback to Config)
        max_concurrent = db.get_setting('torrent_max_concurrent', None)
        try:
            max_concurrent = int(max_concurrent) if max_concurrent is not None else int(getattr(Config, 'MAX_CONCURRENT_DOWNLOADS', 5))
        except Exception:
            max_concurrent = int(getattr(Config, 'MAX_CONCURRENT_DOWNLOADS', 5))
        max_concurrent = max(1, int(max_concurrent))

        active = manager.tell_active() or []
        paused = []
        if len(active) >= max_concurrent:
            # Pause slowest active downloads (excluding the target)
            def _score(it):
                try:
                    return (int(it.get('downloadSpeed', 0)), int(it.get('completedLength', 0)))
                except Exception:
                    return (0, 0)

            candidates = [a for a in active if str(a.get('gid')) != str(download_id)]
            need = max(0, len(active) - max_concurrent + 1)
            for it in sorted(candidates, key=_score)[:need]:
                gid = it.get('gid')
                if not gid:
                    continue
                manager.pause(gid)
                paused.append(gid)
                try:
                    d = db.get_download(str(gid))
                    if d:
                        d.state = DOWNLOAD_STATE_PAUSED
                        db.add_download(d)
                except Exception:
                    pass

        # Move target to top and resume
        manager.change_position(download_id, 0, 'POS_SET')
        manager.resume(download_id)

        try:
            d = db.get_download(download_id)
            if d:
                d.state = DOWNLOAD_STATE_DOWNLOADING
                db.add_download(d)
        except Exception:
            pass

        return jsonify({'success': True, 'paused': paused})
    except Exception as e:
        logger.error(f"Error force-starting download {download_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>/move', methods=['POST'])
def move_download(download_id):
    """Move a download up/down in the aria2 queue."""
    try:
        manager = get_manager()
        if not manager:
            return jsonify({'success': False, 'error': 'Download manager not available'}), 500
        if not manager.rpc_available():
            logger.error("Backend: aria2 RPC is not reachable")
            return jsonify({'success': False, 'error': 'aria2 RPC is not reachable. Please restart the Download Manager.'}), 503

        data = request.get_json(silent=True) or {}
        direction = (data.get('direction') or '').lower()
        if direction in ('up', 'prev', 'previous'):
            offset = -1
        elif direction in ('down', 'next'):
            offset = 1
        else:
            return jsonify({'success': False, 'error': 'Invalid direction'}), 400

        res = manager.change_position(download_id, offset, 'POS_CUR')
        return jsonify({'success': True, 'result': res})
    except Exception as e:
        logger.error(f"Error moving download {download_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>/priority', methods=['POST'])
def set_download_priority(download_id):
    """Set priority (top/normal/bottom) for a download in the aria2 queue."""
    try:
        manager = get_manager()
        if not manager:
            return jsonify({'success': False, 'error': 'Download manager not available'}), 500
        if not manager.rpc_available():
            logger.error("Backend: aria2 RPC is not reachable")
            return jsonify({'success': False, 'error': 'aria2 RPC is not reachable. Please restart the Download Manager.'}), 503

        data = request.get_json(silent=True) or {}
        level = (data.get('level') or '').lower()

        if level in ('top', 'high', 'highest'):
            res = manager.change_position(download_id, 0, 'POS_SET')
        elif level in ('bottom', 'low', 'lowest'):
            res = manager.change_position(download_id, 0, 'POS_END')
        elif level in ('normal', 'middle', ''):
            res = {'status': 'unchanged'}
        else:
            return jsonify({'success': False, 'error': 'Invalid priority level'}), 400

        return jsonify({'success': True, 'result': res})
    except Exception as e:
        logger.error(f"Error setting priority for {download_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>/cancel', methods=['POST'])
def cancel_download(download_id):
    """Cancel a download"""
    try:
        manager = get_manager()
        if not manager:
            return jsonify({'success': False, 'error': 'Download manager not available'}), 500
        if not manager.rpc_available():
            logger.error("Backend: aria2 RPC is not reachable")
            return jsonify({'success': False, 'error': 'aria2 RPC is not reachable. Please restart the Download Manager.'}), 503

        # Get request JSON
        data = request.get_json(silent=True) or {}
        delete_files_flag = data.get('delete_files', False)

        # Get download info from DB
        download = db.get_download(download_id)
        
        # If deleting files, fetch file info from aria2 BEFORE purging
        files_to_delete = []
        if delete_files_flag:
            try:
                # We added get_files to manager earlier
                info = manager.get_files(download_id)
                if info and 'files' in info:
                    files_to_delete = info['files']
            except Exception as e:
                logger.error(f"Failed to get files from aria2 for deletion: {e}")

        # Purge from aria2 (removes result from memory)
        res = manager.purge_download(download_id)

        if download:
            # Delete physical files if requested
            if delete_files_flag and files_to_delete:
                try:
                    import shutil
                    from pathlib import Path
                    
                    # Base download directory
                    root_dl_path = Path(Config.DOWNLOAD_PATH).resolve()
                    parents_to_check = set()
                    
                    # 1. Delete individual files reported by aria2
                    for f in files_to_delete:
                        p_str = f.get('path')
                        if not p_str:
                            continue
                            
                        p = Path(p_str).resolve()
                        
                        # Security check: Ensure file is somewhat related to our download path
                        # (Allow if it's in the download directory or just a safe deletion)
                        try:
                            # Verify 'p' is inside 'root_dl_path' or 'p' equals 'root_dl_path' (unlikely for a file)
                            # is_relative_to is available in Python 3.9+
                            if not p.is_relative_to(root_dl_path):
                                logger.warning(f"Skipping deletion of file outside download path: {p}")
                                continue
                        except AttributeError:
                            # Fallback for Python < 3.9
                            if str(root_dl_path) not in str(p):
                                continue

                        if p.exists() and p.is_file():
                            try:
                                parent_dir = p.parent
                                parents_to_check.add(parent_dir)
                                os.remove(p)
                                logger.info(f"Deleted file: {p}")
                            except Exception as e:
                                logger.error(f"Failed to delete {p}: {e}")

                    # 2. Clean up empty parent directories
                    for parent in parents_to_check:
                        try:
                            # Only delete if it is a subdirectory of root_dl_path
                            # AND it is not the root_dl_path itself
                            if parent != root_dl_path:
                                # Check emptiness
                                if not any(parent.iterdir()):
                                    parent.rmdir()
                                    logger.info(f"Deleted empty directory: {parent}")
                        except Exception as e:
                             # Expected if directory not empty
                             pass

                except Exception as e:
                    logger.error(f"Failed to delete files logic for {download_id}: {e}")

            # Completely remove from DB
            db.delete_download(download_id)

        return jsonify({'success': True, 'result': res})
    except Exception as e:
        logger.error(f"Error cancelling download {download_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>/open-folder', methods=['POST'])
def open_download_folder(download_id):
    """Open the folder where the movie is downloaded"""
    try:
        download = db.get_download(download_id)
        if not download or not download.save_path:
            return jsonify({'success': False, 'error': 'Download or path not found'}), 404
        
        import os
        import subprocess
        path = os.path.abspath(download.save_path)
        
        if not os.path.exists(path):
            return jsonify({'success': False, 'error': f'Directory does not exist: {path}'}), 404
            
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error opening folder for {download_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<download_id>/play', methods=['POST'])
def play_downloaded_file(download_id):
    """Open the downloaded movie file with the default system player"""
    try:
        download = db.get_download(download_id)
        if not download or not download.save_path:
            return jsonify({'success': False, 'error': 'Download or path not found'}), 404
            
        import os
        from pathlib import Path
        
        save_dir = Path(download.save_path)
        if not save_dir.exists():
             return jsonify({'success': False, 'error': 'Path does not exist'}), 404
             
        # Find the largest video file in the directory
        video_extensions = ['.mp4', '.mkv', '.avi', '.ts', '.m4v', '.mov']
        video_files = []
        
        if save_dir.is_file():
            if save_dir.suffix.lower() in video_extensions:
                video_files = [save_dir]
        else:
            for ext in video_extensions:
                video_files.extend(save_dir.glob(f"**/*{ext}"))
        
        if not video_files:
            return jsonify({'success': False, 'error': 'No video files found'}), 404
            
        # Get the largest one (likely the actual movie)
        target_file = max(video_files, key=lambda f: f.stat().st_size)
        
        import subprocess
        path = str(target_file.absolute())
        
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error playing file for {download_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get all settings from database"""
    try:
        settings = {
            'organize_by_genre': db.get_setting('organize_by_genre', 'true').lower() == 'true',
            'download_path': db.get_setting('download_path', Config.DOWNLOAD_PATH),
            'log_level': db.get_setting('log_level', 'INFO'),
            'telemetry_enabled': db.get_setting('telemetry_enabled', 'true').lower() == 'true'
        }
        
        # Add torrent settings
        for key in _TORRENT_SETTING_KEYS:
            default = _TORRENT_DEFAULTS.get(key, '0')
            val = db.get_setting(key, default)
            
            # Convert to appropriate type for UI
            if key in ['enable_dht', 'enable_pex']:
                settings[key] = val.lower() == 'true'
            elif key == 'seed_ratio':
                settings[key] = float(val)
            else:
                try:
                    settings[key] = int(val)
                except:
                    settings[key] = 0
                    
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings in database"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        for key, value in data.items():
            # Convert bool to string for storage
            raw_value = value
            if isinstance(value, bool):
                value = str(value).lower()
            
            db.set_setting(key, value)
            
            # Sync to runtime Config if applicable
            config_key = key.upper()
            if hasattr(Config, config_key):
                setattr(Config, config_key, raw_value)
                logger.info(f"Updated runtime Config.{config_key} = {raw_value}")
            
            # Special handling for log_level
            if key == 'log_level':
                apply_log_level(str(value))
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Torrent / aria2 download option keys we expose to the settings UI
_TORRENT_SETTING_KEYS = [
    'max_download_speed',   # KiB/s, 0=unlimited  → aria2: max-overall-download-limit
    'max_upload_speed',     # KiB/s, 0=unlimited  → aria2: max-overall-upload-limit
    'max_concurrent',       # int                 → aria2: max-concurrent-downloads
    'max_connections',      # int                 → aria2: max-connection-per-server
    'seed_ratio',           # float               → aria2: seed-ratio  (0=off)
    'seed_time',            # seconds, 0=off      → aria2: seed-time
    'enable_dht',           # bool                → aria2: enable-dht
    'enable_pex',           # bool                → aria2: enable-peer-exchange
    'bt_max_peers',         # int, 0=unlimited    → aria2: bt-max-peers
]

_TORRENT_DEFAULTS = {
    'max_download_speed': '0',
    'max_upload_speed':   '0',
    'max_concurrent':     '5',
    'max_connections':    '16',
    'seed_ratio':         '0.0',
    'seed_time':          '0',
    'enable_dht':         'true',
    'enable_pex':         'true',
    'bt_max_peers':       '0',
}


@app.route('/api/torrent-settings', methods=['GET'])
def get_torrent_settings():
    """Return persisted torrent/aria2 settings."""
    try:
        result = {}
        for k in _TORRENT_SETTING_KEYS:
            result[k] = db.get_setting(f'torrent_{k}', _TORRENT_DEFAULTS.get(k, '0'))
        return jsonify({'success': True, 'settings': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/torrent-settings', methods=['POST'])
def update_torrent_settings():
    """Persist torrent/aria2 settings and apply them to a running aria2 daemon."""
    try:
        data = request.json or {}

        # Persist each key
        for k in _TORRENT_SETTING_KEYS:
            if k in data:
                val = str(data[k])
                if k == 'download_path':
                    val = sanitize_download_path(val)
                db.set_setting(f'torrent_{k}', val)

        # Build aria2 option dict and push via changeGlobalOption
        aria2_map = {
            'max_download_speed': lambda v: {'max-overall-download-limit': f'{v}K' if int(v) > 0 else '0'},
            'max_upload_speed':   lambda v: {'max-overall-upload-limit':   f'{v}K' if int(v) > 0 else '0'},
            'max_concurrent':     lambda v: {'max-concurrent-downloads': str(int(v))},
            'max_connections':    lambda v: {'max-connection-per-server': str(int(v))},
            'seed_ratio':         lambda v: {'seed-ratio': str(float(v))},
            'seed_time':          lambda v: {'seed-time':  str(int(v))},
            'enable_dht':         lambda v: {'enable-dht': 'true' if str(v).lower() in ('true','1','yes') else 'false'},
            'enable_pex':         lambda v: {'enable-peer-exchange': 'true' if str(v).lower() in ('true','1','yes') else 'false'},
            'bt_max_peers':       lambda v: {'bt-max-peers': str(int(v))},
        }

        aria2_options = {}
        for k, fn in aria2_map.items():
            if k in data:
                try:
                    aria2_options.update(fn(data[k]))
                except Exception as opt_err:
                    logger.warning(f"Could not build aria2 option for {k}: {opt_err}")

        if aria2_options:
            try:
                manager = get_manager()
                if manager:
                    manager.change_global_option(aria2_options)
                    logger.info(f"Applied aria2 global options: {aria2_options}")
            except Exception as apply_err:
                logger.warning(f"Could not apply aria2 options live: {apply_err}")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    err_str = str(error)
    logger.error(f"Internal server error: {err_str}", exc_info=True)
    log_internal_error(f"Internal Server Error: {err_str[:200]}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


@app.route('/api/refresh-genres', methods=['POST'])
def refresh_genres():
    """Background-scrape genres for all movies that have an empty genres list."""
    import threading, time

    def _worker():
        conn = db._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, title, yts_url FROM movies WHERE genres = '[]' OR genres IS NULL OR genres = ''")
        rows = cur.fetchall()
        logger.info(f"Genre refresh: {len(rows)} movies to refresh")
        updated = 0
        for row in rows:
            movie_id, title, yts_url = row['id'], row['title'], row['yts_url']
            if not yts_url:
                continue
            try:
                details = scraper.scrape_movie_details(yts_url)
                if details and details.get('genres'):
                    import json as _json
                    cur.execute(
                        "UPDATE movies SET genres = ? WHERE id = ?",
                        (_json.dumps(details['genres']), movie_id)
                    )
                    conn.commit()
                    updated += 1
                    logger.info(f"Updated genres for '{title}': {details['genres']}")
                time.sleep(1.5)   # polite rate-limit
            except Exception as e:
                logger.warning(f"Genre refresh failed for '{title}': {e}")
        logger.info(f"Genre refresh complete: {updated}/{len(rows)} updated")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return jsonify({'success': True, 'message': 'Genre refresh started in background'})


def _startup_scrape_if_empty():
    if not scraper:
        logger.warning('Startup scrape skipped: scraper unavailable')
        return
    """If the DB has no movies, scrape the first 3 browse pages in the background."""
    import time
    import threading
    time.sleep(3)  # Wait for Flask to fully start
    try:
        movies = db.get_all_movies()
        if len(movies) < 5:
            logger.info("DB is empty on startup — running initial scrape (3 pages)...")
            for page in range(1, 4):
                try:
                    scraped = scraper.scrape_browse_page(page=page)
                    for m in scraped:
                        try:
                            if m.get('poster_url'):
                                cached = poster_cache.get_cached_path(m['poster_url'])
                                if cached:
                                    m['poster_local'] = cached
                                else:
                                    cache_fn = poster_cache.get_cache_filename(m['poster_url'])
                                    save_path = f"{Config.POSTER_CACHE_DIR}/{cache_fn}"
                                    if scraper.download_poster(m['poster_url'], save_path):
                                        m['poster_local'] = save_path
                            db.add_movie(Movie.from_dict(m))
                        except Exception as e:
                            logger.error(f"Startup scrape save error: {e}")
                    logger.info(f"Startup scrape page {page}: {len(scraped)} movies")
                except Exception as e:
                    logger.error(f"Startup scrape page {page} failed: {e}")
            logger.info("Startup scrape complete")
    except Exception as e:
        logger.error(f"Startup scrape failed: {e}")


# ----- WebSocket: Real-time download progress -----
def _broadcast_downloads():
    """Background thread: push download status to all connected browsers every 2s."""
    while True:
        try:
            manager = get_manager()
            if manager:
                # Fetch active/waiting downloads from aria2
                active = manager.tell_active() or []
                waiting = manager.tell_waiting(0, 1000) or []
                stopped = manager.tell_stopped(0, 1000) or []
                items = [{'_src': 'active', **i} for i in active] + \
                        [{'_src': 'waiting', **i} for i in waiting] + \
                        [{'_src': 'stopped', **i} for i in stopped]

                # Build a GID→DB record lookup for enriching display names
                try:
                    _db_all = db.get_all_downloads()
                    _db_by_gid = {d.id: d for d in _db_all}
                except Exception:
                    _db_by_gid = {}

                _ARIA2_STATE_MAP = {
                    'active':   DOWNLOAD_STATE_DOWNLOADING,
                    'waiting':  DOWNLOAD_STATE_QUEUED,
                    'paused':   DOWNLOAD_STATE_PAUSED,
                    'complete': DOWNLOAD_STATE_COMPLETED,
                    'error':    DOWNLOAD_STATE_ERROR,
                    'removed':  DOWNLOAD_STATE_ERROR,
                }

                downloads_data = []
                for it in items:
                    gid = it.get('gid', '')
                    aria2_status = it.get('status', '')
                    try:
                        completed = int(it.get('completedLength', 0))
                        total = int(it.get('totalLength', 0))
                        progress = round(completed / total * 100.0, 2) if total > 0 else 0.0
                    except Exception:
                        progress = 0.0

                    # Prefer DB record metadata for title/quality
                    db_rec = _db_by_gid.get(gid)
                    if db_rec:
                        movie_title = db_rec.movie_title
                        quality = db_rec.quality
                        error_msg = db_rec.error_message or it.get('errorMessage', '') or ''
                    else:
                        bt_info = it.get('bittorrent', {})
                        bt_name = (bt_info.get('info') or {}).get('name', '') if bt_info else ''
                        files = it.get('files', [])
                        movie_title = bt_name or (files[0].get('path', '').split('\\')[-1].split('/')[-1] if files else f'aria2:{gid}')
                        quality = ''
                        error_msg = it.get('errorMessage', '') or ''

                    if it['_src'] == 'stopped' and aria2_status == 'complete':
                        state = DOWNLOAD_STATE_COMPLETED
                    else:
                        state = _ARIA2_STATE_MAP.get(aria2_status, aria2_status)

                    files = it.get('files', [])
                    save_path = files[0].get('path', '') if files else ''

                    try:
                        speed = int(it.get('downloadSpeed', 0) or 0)
                        peers = int(it.get('numPeers', 0) or 0)
                        seeds = int(it.get('numSeeders', 0) or 0)
                    except Exception:
                        speed, peers, seeds = 0, 0, 0
                    stall_reason = ''
                    is_stalled = False
                    if error_msg:
                        is_stalled = True
                        stall_reason = error_msg
                    elif state in (DOWNLOAD_STATE_QUEUED, 'waiting', 'queued'):
                        is_stalled = True
                        stall_reason = 'Queued (waiting for a free slot)'
                    elif state in (DOWNLOAD_STATE_DOWNLOADING, 'active', 'downloading'):
                        if speed <= 1024 and peers <= 1 and seeds <= 1:
                            is_stalled = True
                            stall_reason = 'Low peer availability'

                    def _si(val, default=0):
                        try:
                            return int(val) if val is not None else default
                        except (ValueError, TypeError):
                            return default

                    downloads_data.append({
                        'id': gid,
                        'movie_id': db_rec.movie_id if db_rec else '',
                        'movie_title': movie_title,
                        'quality': quality,
                        'state': state,
                        'progress': progress,
                        'download_rate': _si(it.get('downloadSpeed', 0)),
                        'upload_rate': _si(it.get('uploadSpeed', 0)),
                        'eta': _si(it.get('eta', 0)),
                        'size_total': _si(it.get('totalLength', 0)),
                        'size_downloaded': _si(it.get('completedLength', 0)),
                        'num_peers': _si(it.get('numPeers', 0)),
                        'num_seeds': _si(it.get('numSeeders', 0)),
                        'save_path': save_path,
                        'error_message': error_msg,
                        'is_stalled': is_stalled,
                        'stall_reason': stall_reason,
                        'aria2_status': str(aria2_status or '').lower(),
                    })
                socketio.emit('downloads_update', {'downloads': downloads_data})
        except Exception as e:
            logger.debug(f"WebSocket broadcast error: {e}")
        time.sleep(2)


@socketio.on('connect')
def on_connect():
    logger.info(f"Browser connected via WebSocket")
    emit('connected', {'status': 'ok'})


@socketio.on('disconnect')
def on_disconnect():
    logger.info("Browser disconnected from WebSocket")


def run_server():
    """Run the Flask+SocketIO server"""
    # Auto-populate DB on first run
    threading.Thread(target=_startup_scrape_if_empty, daemon=True).start()
    # Start background WebSocket broadcaster
    threading.Thread(target=_broadcast_downloads, daemon=True).start()
    logger.info(f"Starting server on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    socketio.run(
        app,
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )


if __name__ == '__main__':
    run_server()









