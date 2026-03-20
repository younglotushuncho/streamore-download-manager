'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import MovieModal from './MovieModal';
import AdBanner from './AdBanner';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Torrent {
    quality: string;
    type?: string;
    size?: string;
    url?: string;
    hash?: string;
    seeds?: number;
    peers?: number;
    magnet_link?: string;
    torrent_url?: string;
}

interface Movie {
    id: string;
    title: string;
    year?: number;
    rating?: number;
    poster_url?: string;
    genres?: string[];
    yts_url?: string;
    torrents?: Torrent[];
    description?: string;
    yts_id?: number;
    yt_trailer_code?: string;
}

// ── API helpers ───────────────────────────────────────────────────────────────
const YTS_API = 'https://movies-api.accel.li/api/v2';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

/** Map a raw YTS movie object → our Movie shape */
function mapYtsMovie(m: any): Movie {
    const torrents: Torrent[] = (m.torrents || []).map((t: any) => {
        const hash = t.hash || '';
        const magnet = hash
            ? `magnet:?xt=urn:btih:${hash}&dn=${encodeURIComponent(m.title_long || m.title)}&tr=udp://open.demonii.com:1337/announce&tr=udp://tracker.openbittorrent.com:80&tr=udp://tracker.coppersurfer.tk:6969&tr=udp://glotorrents.pw:6969/announce&tr=udp://tracker.opentrackr.org:1337/announce&tr=udp://torrent.gresille.org:80/announce&tr=udp://p4p.arenabg.com:1337&tr=udp://tracker.leechers-paradise.org:6969`
            : '';
        return {
            quality: t.quality || '',
            type: t.type || 'BluRay',
            size: t.size || '',
            hash,
            seeds: t.seeds ?? 0,
            peers: t.peers ?? 0,
            torrent_url: t.url || '',
            magnet_link: magnet,
        };
    });

    return {
        id: String(m.id),
        yts_id: m.id,
        title: m.title_long || m.title || 'Unknown',
        year: m.year,
        rating: m.rating,
        poster_url: m.large_cover_image || m.medium_cover_image || m.small_cover_image || '',
        genres: m.genres || [],
        yts_url: m.url || '',
        description: m.summary || m.synopsis || m.description_full || '',
        yt_trailer_code: m.yt_trailer_code || '',
        torrents,
    };
}

/** Fetch movie list from YTS public API */
async function fetchYtsMovies(opts: {
    search?: string;
    genre?: string;
    quality?: string;
    year?: string;
    page?: number;
    limit?: number;
    sort?: string;
}): Promise<{ movies: Movie[], totalCount: number }> {
    const params: Record<string, string> = {
        limit: String(opts.limit ?? 50),
        page: String(opts.page ?? 1),
        sort_by: opts.sort ?? 'download_count',
        order_by: 'desc',
        with_rt_ratings: 'false',
    };
    if (opts.search && opts.search.trim()) params.query_term = opts.search.trim();
    if (opts.genre && opts.genre !== 'All') params.genre = opts.genre.toLowerCase();
    if (opts.quality && opts.quality !== 'All') params.quality = opts.quality;
    if (opts.year && opts.year !== 'All') params.query_term = (params.query_term ? params.query_term + ' ' : '') + opts.year;

    const qs = new URLSearchParams(params).toString();
    const res = await fetch(`${YTS_API}/list_movies.json?${qs}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`Streamore API HTTP ${res.status}`);
    const data = await res.json();
    if (data.status !== 'ok') throw new Error(`Streamore API status: ${data.status}`);
    return {
        movies: (data.data?.movies || []).map(mapYtsMovie),
        totalCount: data.data?.movie_count || 0,
    };
}

/** Fetch full movie details (includes torrents & summary) */
async function fetchYtsDetails(ytsId: number): Promise<Partial<Movie>> {
    const res = await fetch(`${YTS_API}/movie_details.json?movie_id=${ytsId}&with_images=true&with_cast=false`, {
        cache: 'force-cache',
    });
    if (!res.ok) return {};
    const data = await res.json();
    if (data.status !== 'ok') return {};
    return mapYtsMovie(data.data?.movie || {});
}

// ── MovieCard ─────────────────────────────────────────────────────────────────
function MovieCard({ movie, onClick, isDownloaded }: { movie: Movie; onClick: () => void; isDownloaded: boolean }) {
    const [imgError, setImgError] = useState(false);

    return (
        <div
            className="card-glow"
            onClick={onClick}
            style={{
                background: 'var(--bg-card)', borderRadius: 14,
                border: isDownloaded ? '1px solid var(--success)' : '1px solid var(--border)', overflow: 'hidden',
                cursor: 'pointer', transition: 'all 0.25s',
                animation: 'fadeIn 0.4s ease forwards',
            }}
        >
            {/* Poster */}
            <div style={{ position: 'relative', aspectRatio: '2/3', background: '#1a1a28' }}>
                {!imgError && movie.poster_url ? (
                    <img
                        src={movie.poster_url}
                        alt={movie.title}
                        onError={() => setImgError(true)}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                ) : (
                    <div style={{
                        width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 40, background: 'linear-gradient(135deg, #1e1e2f, #12121a)',
                    }}>🎬</div>
                )}

                {/* Overlays */}
                <div style={{
                    position: 'absolute', top: 8, right: 8, display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end',
                }}>
                    {movie.rating && (
                        <div style={{
                            background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(4px)',
                            borderRadius: 8, padding: '4px 8px', fontSize: 12, fontWeight: 700, color: '#f59e0b',
                        }}>⭐ {movie.rating}</div>
                    )}
                    {isDownloaded && (
                        <div style={{
                            background: 'rgba(34,197,94,0.9)', backdropFilter: 'blur(4px)',
                            borderRadius: 8, padding: '4px 8px', fontSize: 10, fontWeight: 800, color: '#fff',
                        }}>✅ DOWNLOADED</div>
                    )}
                </div>

                {/* Quality badges */}
                {movie.torrents && movie.torrents.length > 0 && (
                    <div style={{
                        position: 'absolute', bottom: 8, left: 8,
                        display: 'flex', gap: 4, flexWrap: 'wrap',
                    }}>
                        {[...new Set(movie.torrents.map(t => t.quality))].map(q => (
                            <span key={q} style={{
                                background: q === '2160p' ? 'rgba(245,158,11,0.85)' :
                                    q === '1080p' ? 'rgba(108,99,255,0.85)' :
                                        'rgba(34,197,94,0.75)',
                                backdropFilter: 'blur(4px)',
                                color: '#fff', fontSize: 10, fontWeight: 700,
                                padding: '2px 6px', borderRadius: 4,
                            }}>{q}</span>
                        ))}
                    </div>
                )}
            </div>
            {/* Info */}
            <div style={{ padding: '12px 14px' }}>
                <h3 style={{
                    fontSize: 14, fontWeight: 700, color: 'var(--text-primary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 4,
                }}>{movie.title}</h3>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {movie.year}
                    {movie.genres && movie.genres[0] && <span> · {movie.genres[0]}</span>}
                </div>
            </div>
        </div>
    );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function SkeletonGrid() {
    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16 }}>
            {Array.from({ length: 30 }).map((_, i) => (
                <div key={i}>
                    <div className="skeleton" style={{ aspectRatio: '2/3', borderRadius: 14 }} />
                    <div className="skeleton" style={{ height: 14, marginTop: 10, width: '80%' }} />
                    <div className="skeleton" style={{ height: 12, marginTop: 6, width: '50%' }} />
                </div>
            ))}
        </div>
    );
}

// ── Main MovieGrid ─────────────────────────────────────────────────────────────
export default function MovieGrid() {
    const [movies, setMovies] = useState<Movie[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [error, setError] = useState('');
    const [search, setSearch] = useState('');
    const [liveSearch, setLiveSearch] = useState('');
    const [genre, setGenre] = useState('All');
    const [year, setYear] = useState('All');
    const [quality, setQuality] = useState('All');
    const [sort, setSort] = useState('download_count');
    const [page, setPage] = useState(1);
    const [totalMovies, setTotalMovies] = useState(0);
    const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);

    const GENRES = ['All', 'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'Film-Noir', 'Horror', 'Music', 'Mystery', 'Romance', 'Sci-Fi', 'Sport', 'Thriller', 'Western'];
    const QUALITIES = ['All', '720p', '1080p', '2160p'];
    const SORTS = [
        { value: 'download_count', label: '🔥 Popular' },
        { value: 'like_count', label: '❤️ Most Liked' },
        { value: 'date_added', label: '🆕 Newest' },
        { value: 'year', label: '📅 Year' },
        { value: 'rating', label: '⭐ Rating' },
        { value: 'title', label: '🔤 Title' },
    ];
    const currentYear = new Date().getFullYear();
    const YEARS = ['All', ...Array.from({ length: 30 }, (_, i) => String(currentYear - i))];

    const [suggestions, setSuggestions] = useState<Movie[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);

    // Debounce search
    useEffect(() => {
        const t = setTimeout(() => setSearch(liveSearch), 600);
        return () => clearTimeout(t);
    }, [liveSearch]);

    // Fetch suggestions as user types
    useEffect(() => {
        if (liveSearch.length < 2) {
            setSuggestions([]);
            setShowSuggestions(false);
            return;
        }

        const t = setTimeout(async () => {
            try {
                const { movies } = await fetchYtsMovies({ search: liveSearch, limit: 5 });
                setSuggestions(movies);
                setShowSuggestions(true);
            } catch (err) {}
        }, 300);
        return () => clearTimeout(t);
    }, [liveSearch]);

    const [downloadedIds, setDownloadedIds] = useState<string[]>([]);

    const fetchDownloadedIds = async () => {
        try {
            const [dRes, hRes] = await Promise.all([
                 fetch(`${API}/api/downloads`),
                 fetch(`${API}/api/downloads/history`)
            ]);
            const dData = await dRes.json();
            const hData = await hRes.json();
            const ids = new Set<string>();
            if (dData.success && dData.downloads) {
                 dData.downloads.forEach((dl: any) => { if (dl.movie_id) ids.add(String(dl.movie_id)); });
            }
            if (hData.success && hData.history) {
                 hData.history.forEach((h: any) => { if (h.movie_id) ids.add(String(h.movie_id)); });
            }
            setDownloadedIds(Array.from(ids));
        } catch(e) {}
    };

    const [trendingMovies, setTrendingMovies] = useState<Movie[]>([]);

    useEffect(() => {
        // Fetch top trending movies
        (async () => {
            try {
                const { movies } = await fetchYtsMovies({ limit: 15, sort: 'download_count' });
                setTrendingMovies(movies);
            } catch (e) {}
        })();
    }, []);

    // Fetch page whenever filters change
    const doFetch = useCallback(async (pg = 1) => {
        setLoading(true);
        setError('');
        fetchDownloadedIds();
        try {
            const { movies: results, totalCount } = await fetchYtsMovies({ search, genre, quality, year, sort, page: pg, limit: 48 });
            setMovies(results);
            setTotalMovies(totalCount);
            setPage(pg);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (e: any) {
            setError(e.message || 'Failed to fetch movies');
        } finally {
            setLoading(false);
        }
    }, [search, genre, quality, year, sort]);
    useEffect(() => { doFetch(1); }, [doFetch]);
    // Open movie — always try to fetch full details (torrents + summary) from YTS
    const openMovie = async (movie: Movie) => {
        setSelectedMovie(movie); // show immediately, then enrich
        if (movie.yts_id) {
            const details = await fetchYtsDetails(movie.yts_id);
            setSelectedMovie(prev => prev ? { ...prev, ...details } : prev);
        }
    };

    const filterStyle: React.CSSProperties = {
        background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)',
        color: 'var(--text-primary)', borderRadius: 10, padding: '8px 12px', fontSize: 14,
        outline: 'none', cursor: 'pointer',
    };

    return (
        <div>
            {/* Search + filters bar */}
            <div style={{
                position: 'sticky', top: 64, zIndex: 50,
                background: 'rgba(10,10,15,0.95)', backdropFilter: 'blur(12px)',
                borderBottom: '1px solid var(--border)', padding: '12px 24px',
            }}>
                <div style={{ maxWidth: 1400, margin: '0 auto', display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                    <div style={{ position: 'relative', flex: '1 1 240px', minWidth: 200 }}>
                        <input
                            type="text" placeholder="🔍 Search movies..."
                            value={liveSearch} 
                            onChange={e => setLiveSearch(e.target.value)}
                            onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
                            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                            style={{ ...filterStyle, width: '100%', padding: '10px 16px', fontSize: 15 }}
                        />
                        {showSuggestions && suggestions.length > 0 && (
                            <div style={{
                                position: 'absolute', top: '100%', left: 0, right: 0, 
                                background: 'var(--bg-card)', border: '1px solid var(--border)',
                                borderTop: 'none', borderRadius: '0 0 12px 12px',
                                boxShadow: '0 20px 40px rgba(0,0,0,0.5)', zIndex: 1000,
                                maxHeight: 300, overflowY: 'auto'
                            }}>
                                {suggestions.map(s => (
                                    <div 
                                        key={s.id} 
                                        onClick={() => { openMovie(s); setLiveSearch(s.title); setShowSuggestions(false); }}
                                        style={{
                                            padding: '10px 16px', display: 'flex', gap: 12, alignItems: 'center',
                                            cursor: 'pointer', borderBottom: '1px solid var(--border)', transition: 'all 0.2s',
                                        }}
                                        className="card-glow-hover"
                                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                    >
                                        <div style={{ 
                                            width: 40, height: 56, background: '#1a1a28', borderRadius: 4, overflow: 'hidden' 
                                        }}>
                                            <img src={s.poster_url} alt={s.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                        </div>
                                        <div>
                                            <p style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>{s.title}</p>
                                            <p style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{s.year} · ⭐ {s.rating}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    <select value={genre} onChange={e => { setGenre(e.target.value); }} style={filterStyle}>
                        {GENRES.map(g => <option key={g} value={g} style={{ background: 'var(--bg-card)' }}>{g}</option>)}
                    </select>
                    <select value={year} onChange={e => { setYear(e.target.value); }} style={filterStyle}>
                        {YEARS.map(y => <option key={y} value={y} style={{ background: 'var(--bg-card)' }}>{y}</option>)}
                    </select>
                    <select value={quality} onChange={e => { setQuality(e.target.value); }} style={filterStyle}>
                        {QUALITIES.map(q => <option key={q} value={q} style={{ background: 'var(--bg-card)' }}>{q}</option>)}
                    </select>
                    <select value={sort} onChange={e => { setSort(e.target.value); }} style={filterStyle}>
                        {SORTS.map(s => <option key={s.value} value={s.value} style={{ background: 'var(--bg-card)' }}>{s.label}</option>)}
                    </select>
                    <button onClick={() => doFetch(1)} disabled={loading} style={{
                        ...filterStyle, background: 'var(--accent)', border: 'none',
                        fontWeight: 700, padding: '10px 18px', color: '#fff',
                        opacity: loading ? 0.6 : 1,
                    }}>
                        {loading ? '⏳' : '↺'}
                    </button>
                </div>
            </div>

            {/* Content */}
            <div style={{ maxWidth: 1400, margin: '0 auto', padding: '24px 24px 40px' }}>
                {!search && !genre && !year && trendingMovies.length > 0 && (
                    <div style={{ marginBottom: 48 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                            <span style={{ fontSize: 24 }}>🔥</span>
                            <h2 style={{ fontSize: 22, fontWeight: 800 }}>Trending Now</h2>
                        </div>
                        <div style={{ 
                            display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 16,
                            maskImage: 'linear-gradient(to right, black 85%, transparent)'
                        }} className="hide-scrollbar">
                           {trendingMovies.map(m => (
                               <div key={m.id} onClick={() => openMovie(m)} style={{
                                   flex: '0 0 140px', cursor: 'pointer', transition: 'transform 0.2s'
                               }} onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'} onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}>
                                   <div style={{ position: 'relative', aspectRatio: '2/3', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--border)' }}>
                                       <img src={m.poster_url} alt={m.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                       <div style={{ position: 'absolute', top: 6, right: 6, background: 'rgba(0,0,0,0.7)', borderRadius: 6, padding: '2px 6px', fontSize: 10, fontWeight: 700, color: '#f59e0b' }}>
                                           ⭐ {m.rating}
                                       </div>
                                   </div>
                                   <p style={{ marginTop: 8, fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.title}</p>
                               </div>
                           ))}
                        </div>
                    </div>
                )}

                {error && (
                    <div style={{
                        background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                        borderRadius: 12, padding: '16px 20px', color: '#ef4444',
                        marginBottom: 16, fontSize: 14,
                    }}>
                        ⚠️ {error} — Streamore may be temporarily unavailable. Please try again.
                    </div>
                )}

                {loading ? (
                    <SkeletonGrid />
                ) : movies.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--text-secondary)' }}>
                        <div style={{ fontSize: 56, marginBottom: 16 }}>🎬</div>
                        <p style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>No movies found</p>
                        <p style={{ fontSize: 14, marginTop: 8 }}>Try adjusting your filters or search term</p>

                        {search && (
                            <div style={{ 
                                maxWidth: 400, margin: '40px auto 0', padding: '24px', 
                                borderRadius: 20, background: 'rgba(108,99,255,0.05)', border: '1px dashed var(--border)',
                                animation: 'fadeIn 0.5s ease-out'
                            }}>
                                <p style={{ fontSize: 14, marginBottom: 16, color: 'var(--text-primary)', fontWeight: 600 }}>
                                    🔔 Want to be notified when "{search}" is available?
                                </p>
                                <form onSubmit={(e) => {
                                    e.preventDefault();
                                    alert(`Thanks! We've saved your interest for "${search}". We'll notify you if a high-quality release drops.`);
                                    (e.target as any).reset();
                                }} style={{ display: 'flex', gap: 8 }}>
                                    <input 
                                        type="email" 
                                        required
                                        placeholder="Enter your email" 
                                        style={{ 
                                            flex: 1, padding: '12px 16px', borderRadius: 12, 
                                            background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', 
                                            color: '#fff', outline: 'none', fontSize: 14
                                        }} 
                                    />
                                    <button type="submit" style={{ 
                                        padding: '12px 20px', borderRadius: 12, background: 'var(--accent)', 
                                        border: 'none', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer',
                                        transition: 'transform 0.2s'
                                    }} onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'} onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}>
                                        Alert Me
                                    </button>
                                </form>
                                <p style={{ fontSize: 11, marginTop: 12, opacity: 0.5 }}>
                                    Your email is safe with us. We only send movie release alerts.
                                </p>
                            </div>
                        )}
                    </div>
                ) : (
                    <>
                        <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 16 }}>
                            Showing {movies.length} of {totalMovies.toLocaleString()} movies from <strong style={{ color: 'var(--accent)' }}>Streamore</strong>
                            {genre !== 'All' && ` · ${genre}`}
                            {quality !== 'All' && ` · ${quality}`}
                            {year !== 'All' && ` · ${year}`}
                        </p>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16 }}>
                            {movies.map((m, i) => (
                                <React.Fragment key={m.id}>
                                    {i > 0 && i % 12 === 0 && (
                                        <div style={{ 
                                            gridColumn: '1 / -1', margin: '8px 0', 
                                            borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', 
                                            padding: '16px 0', background: 'rgba(255,255,255,0.02)', borderRadius: 12,
                                            display: 'flex', flexDirection: 'column', alignItems: 'center'
                                        }}>
                                            <p style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Advertisement</p>
                                            <AdBanner zoneId="5876820" />
                                        </div>
                                    )}
                                    <MovieCard 
                                        movie={m} 
                                        onClick={() => openMovie(m)} 
                                        isDownloaded={downloadedIds.includes(String(m.id))}
                                    />
                                </React.Fragment>
                            ))}
                        </div>

                        {/* Pagination */}
                        {totalMovies > 48 && (
                            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16, marginTop: 40, marginBottom: 20 }}>
                                <button
                                    onClick={() => doFetch(page - 1)}
                                    disabled={page <= 1 || loading}
                                    style={{
                                        background: page <= 1 ? 'rgba(255,255,255,0.05)' : 'rgba(108,99,255,0.15)',
                                        border: '1px solid var(--border)', color: page <= 1 ? 'var(--text-secondary)' : 'var(--accent)',
                                        borderRadius: 8, padding: '8px 16px', fontSize: 14, fontWeight: 600,
                                        cursor: page <= 1 ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
                                    }}
                                >
                                    ← Previous
                                </button>

                                <span style={{ color: 'var(--text-secondary)', fontSize: 14, fontWeight: 500 }}>
                                    Page <strong style={{ color: 'var(--text-primary)' }}>{page}</strong> of {Math.ceil(totalMovies / 48)}
                                </span>

                                <button
                                    onClick={() => doFetch(page + 1)}
                                    disabled={page >= Math.ceil(totalMovies / 48) || loading}
                                    style={{
                                        background: page >= Math.ceil(totalMovies / 48) ? 'rgba(255,255,255,0.05)' : 'rgba(108,99,255,0.15)',
                                        border: '1px solid var(--border)', color: page >= Math.ceil(totalMovies / 48) ? 'var(--text-secondary)' : 'var(--accent)',
                                        borderRadius: 8, padding: '8px 16px', fontSize: 14, fontWeight: 600,
                                        cursor: page >= Math.ceil(totalMovies / 48) ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
                                    }}
                                >
                                    Next →
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>

            {selectedMovie && (
                <MovieModal movie={selectedMovie} onClose={() => setSelectedMovie(null)} />
            )}
        </div>
    );
}
