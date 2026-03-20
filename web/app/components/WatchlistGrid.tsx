'use client';
import { useState, useEffect, useCallback } from 'react';
import MovieModal from './MovieModal';

interface Torrent {
    quality: string;
    type?: string;
    size?: string;
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
    torrents?: Torrent[];
    description?: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

function MovieCard({ movie, onClick }: { movie: Movie; onClick: () => void }) {
    const [imgError, setImgError] = useState(false);
    return (
        <div
            className="card-glow"
            onClick={onClick}
            style={{
                background: 'var(--bg-card)', borderRadius: 14,
                border: '1px solid var(--border)', overflow: 'hidden',
                cursor: 'pointer', transition: 'all 0.25s',
            }}
        >
            <div style={{ position: 'relative', aspectRatio: '2/3', background: '#1a1a28' }}>
                {!imgError && movie.poster_url ? (
                    <img src={movie.poster_url} alt={movie.title} onError={() => setImgError(true)}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40 }}>🎬</div>
                )}
                {movie.rating && (
                    <div style={{
                        position: 'absolute', top: 8, right: 8, background: 'rgba(0,0,0,0.8)',
                        borderRadius: 8, padding: '4px 8px', fontSize: 12, fontWeight: 700, color: '#f59e0b',
                    }}>⭐ {movie.rating}</div>
                )}
            </div>
            <div style={{ padding: '12px' }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{movie.title}</h3>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{movie.year}</div>
            </div>
        </div>
    );
}

export default function WatchlistGrid() {
    const [movies, setMovies] = useState<Movie[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);

    const fetchWatchlist = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API}/api/watchlist`);
            const data = await res.json();
            if (data.success) {
                setMovies(data.movies || []);
            }
        } catch (e) {} finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchWatchlist(); }, [fetchWatchlist]);

    if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>Loading watchlist...</div>;

    return (
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: 24 }}>
            <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 24 }}>❤️ Your Watchlist</h1>
            {movies.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-secondary)' }}>
                    <div style={{ fontSize: 60, marginBottom: 16 }}>🤍</div>
                    <p>Your watchlist is empty.</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16 }}>
                    {movies.map(m => <MovieCard key={m.id} movie={m} onClick={() => setSelectedMovie(m)} />)}
                </div>
            )}
            {selectedMovie && <MovieModal movie={selectedMovie} onClose={() => { setSelectedMovie(null); fetchWatchlist(); }} />}
        </div>
    );
}
