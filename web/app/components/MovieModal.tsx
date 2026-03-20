'use client';
import { useState, useEffect, useRef } from 'react';
import AffiliateBanner from './AffiliateBanner';

interface Torrent {
    quality: string;
    type?: string;
    size?: string;
    url?: string;
    torrent_url?: string;
    magnet_link?: string;
    seeds?: number;
}

interface Movie {
    id: string;
    title: string;
    year?: number;
    rating?: number;
    description?: string;
    poster_url?: string;
    genres?: string[];
    yts_url?: string;
    yt_trailer_code?: string;
    torrents?: Torrent[];
}

interface Props {
    movie: Movie;
    onClose: () => void;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'https://movie-project-backend.fly.dev';
const OUO_API_KEY = 'k1e6VX2P';
const DESKTOP_INSTALLER_URL =
    process.env.NEXT_PUBLIC_DESKTOP_INSTALLER_URL || 'https://pub-de03d3c6527b425fa2ee53203c4ea5fc.r2.dev/StreamoreSetup.exe';

/** Port the desktop app's detection server listens on */
const DESKTOP_PORT = 57432;
const DESKTOP_PING_URL = `http://127.0.0.1:${DESKTOP_PORT}/ping`;
const DESKTOP_DL_URL = `http://127.0.0.1:${DESKTOP_PORT}/download`;

/** How long to wait for the ping response before giving up (ms) */
const PING_TIMEOUT_MS = 1500;

function formatBytes(bytes: number) {
    if (!bytes) return '?';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(0) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

/**
 * Probe the desktop app's local detection server.
 * Returns the ping payload if the app is running, or null if not detected.
 */
async function pingDesktopApp(): Promise<{ ok: boolean; version?: string; app?: string } | null> {
    try {
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), PING_TIMEOUT_MS);
        const res = await fetch(DESKTOP_PING_URL, {
            method: 'GET',
            signal: controller.signal,
            mode: 'cors',
            cache: 'no-store',
        });
        clearTimeout(tid);
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

/**
 * Send a download request directly to the desktop app's local HTTP server.
 * The desktop app handles consent, backend forwarding, and the toast.
 */
async function sendToDesktopApp(payload: {
    magnet: string;
    title: string;
    quality: string;
    movie_id: string;
    genres?: string[];
}): Promise<{ ok: boolean; error?: string }> {
    try {
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 8000);
        const res = await fetch(DESKTOP_DL_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal,
            mode: 'cors',
        });
        clearTimeout(tid);
        const data = await res.json();
        return { ok: !!data.ok, error: data.error };
    } catch (e: any) {
        return { ok: false, error: e.message };
    }
}

export default function MovieModal({ movie, onClose }: Props) {
    const [selectedTorrent, setSelectedTorrent] = useState<Torrent | null>(null);
    const [status, setStatus] = useState('');
    const [statusColor, setStatusColor] = useState('var(--text-secondary)');
    const [loading, setLoading] = useState(false);
    const [torrents] = useState<Torrent[]>(movie.torrents || []);
    const [adPhase, setAdPhase] = useState(false);

    // Desktop app detection state
    // 'checking' = probing, 'yes' = confirmed running, 'no' = not found
    const [appState, setAppState] = useState<'checking' | 'yes' | 'no'>('checking');
    const [showInstallBanner, setShowInstallBanner] = useState(false);
    const [installerLoading, setInstallerLoading] = useState(false);
    const pingDoneRef = useRef(false);

    const setMsg = (msg: string, color = 'var(--text-secondary)') => {
        setStatus(msg);
        setStatusColor(color);
    };

    // Watchlist state
    const [isOnWatchlist, setIsOnWatchlist] = useState(false);
    const [watchlistLoading, setWatchlistLoading] = useState(false);

    // Auto-probe the desktop app when the modal opens
    useEffect(() => {
        if (pingDoneRef.current) return;
        pingDoneRef.current = true;

        (async () => {
            const result = await pingDesktopApp();
            if (result?.ok) {
                setAppState('yes');
            } else {
                setAppState('no');
            }
        })();

        // Check watchlist status
        (async () => {
             try {
                 const res = await fetch(`${API}/api/movies`);
                 if (res.ok) {
                      const data = await res.json();
                      if (data.success) {
                           // This is slow, but works for now.
                           // Better: /api/watchlist/status?movie_id=X
                           setIsOnWatchlist(data.movies?.some((m: any) => m.id === movie.id));
                      }
                 }
             } catch(e) {}
        })();
    }, [movie.id]);

    const toggleWatchlist = async () => {
        setWatchlistLoading(true);
        try {
            const res = await fetch(`${API}/api/watchlist/toggle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ movie_id: movie.id })
            });
            const data = await res.json();
            if (data.success) {
                setIsOnWatchlist(data.is_on_watchlist);
                setMsg(data.is_on_watchlist ? 'Added to watchlist' : 'Removed from watchlist', 'var(--accent)');
            }
        } catch (err: any) {
            setMsg('Failed to update watchlist', 'var(--error)');
        } finally {
            setWatchlistLoading(false);
        }
    };

    // Desktop app helpers

    const handleDesktopDownload = async () => {
        if (!selectedTorrent) { setMsg('Select a quality first', 'var(--error)'); return; }
        // Prefer magnet_link over torrent_url for better desktop app compatibility
        const target = selectedTorrent.magnet_link || selectedTorrent.torrent_url || selectedTorrent.url || '';
        if (!target) { setMsg('No download link available', 'var(--error)'); return; }

        setLoading(true);
        setMsg('Sending to Streamore Desktop...', 'var(--accent)');

        const result = await sendToDesktopApp({
            magnet: target,
            title: movie.title || '',
            quality: selectedTorrent.quality || '',
            movie_id: movie.id || '',
            genres: movie.genres || [],
        });

        setLoading(false);

        if (result.ok) {
            setMsg('Download queued in the desktop app! Check your system tray.', 'var(--success)');
        } else if (result.error === 'User declined') {
            setMsg('Download cancelled.', 'var(--text-secondary)');
        } else {
            // Desktop app may have gone away - fall back
            setAppState('no');
            setMsg('Desktop app not reachable. Using web download...', 'var(--warning)');
            setTimeout(() => handleWebDownload(), 500);
        }
    };

    /** Called when the user presses Download and the desktop app is NOT detected. */
    const handleDownloadClick = async () => {
        if (!selectedTorrent) { setMsg('Select a quality first', 'var(--error)'); return; }
        const target = selectedTorrent.magnet_link || selectedTorrent.torrent_url || selectedTorrent.url || '';
        if (!target) { setMsg('No download link available', 'var(--error)'); return; }

        setLoading(true);
        setMsg('Connecting to Streamore Desktop...', 'var(--accent)');

        const payload = {
            magnet: target,
            title: movie.title || '',
            quality: selectedTorrent.quality || '',
            movie_id: movie.id || '',
            genres: movie.genres || [],
        };

        // 1) Fast path: send directly to desktop bridge.
        let result = await sendToDesktopApp(payload);

        // 2) Recovery path: re-ping then retry once.
        if (!result.ok) {
            const probe = await pingDesktopApp();
            if (probe?.ok) {
                setAppState('yes');
                result = await sendToDesktopApp(payload);
            } else {
                setAppState('no');
            }
        }

        setLoading(false);

        if (result.ok) {
            setAppState('yes');
            setMsg('Download queued in the desktop app. Check your system tray.', 'var(--success)');
            return;
        }

        if (result.error === 'User declined') {
            setMsg('Download cancelled.', 'var(--text-secondary)');
            return;
        }

        // Desktop auto-send failed: download installer instead.
        setMsg('Desktop app not detected. Downloading installer...','var(--warning)');
        setShowInstallBanner(true);
        handleInstallerDownload();
        return;
    };

    // Web download (Adsterra Direct Link flow)

    // Paste your Adsterra Direct Link URL here
    const ADSTERRA_DIRECT_LINK = 'https://www.highcpmgate.com/example-direct-link';

    const handleWebDownload = async () => {
        if (!selectedTorrent) { setMsg('Select a quality first', 'var(--error)'); return; }
        // Prefer magnet_link over torrent_url for web fallback too
        const targetUrl = selectedTorrent.magnet_link || selectedTorrent.torrent_url || selectedTorrent.url || '';
        if (!targetUrl) { setMsg('No download link available', 'var(--error)'); return; }

        // 1. Open Adsterra Direct Link in a new background tab or popup
        window.open(ADSTERRA_DIRECT_LINK, '_blank');

        // 2. Immediately trigger the magnet link download in the current window
        setMsg('Starting download...', 'var(--success)');
        const a = document.createElement('a');
        a.href = targetUrl;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    };

    // Install banner actions

    /** User says they have the app - re-probe then send. */
    const handleIHaveIt = async () => {
        setShowInstallBanner(false);
        setMsg('Re-checking for desktop app...', 'var(--accent)');
        const result = await pingDesktopApp();
        if (result?.ok) {
            setAppState('yes');
            handleDesktopDownload();
        } else {
            setMsg('Desktop app not detected. Make sure it is running, then try again.', 'var(--error)');
        }
    };

    /** User prefers web - remember for the session and proceed. */
    const handleSkipToWeb = () => {
        localStorage.setItem('streamore_skip_app_banner', 'true');
        setShowInstallBanner(false);
        handleWebDownload();
    };

    /** Download desktop installer without redirecting the user away from the page. */
    const handleInstallerDownload = async () => {
        setInstallerLoading(true);
        setMsg('Downloading desktop installer...', 'var(--accent)');
        try {
            const res = await fetch(DESKTOP_INSTALLER_URL, { mode: 'cors' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'StreamoreSetup.exe';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            setMsg('Installer download started.', 'var(--success)');
        } catch {
            // Fallback for browsers/environments where fetch->blob download is blocked.
            const a = document.createElement('a');
            a.href = DESKTOP_INSTALLER_URL;
            a.download = 'StreamoreSetup.exe';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setMsg('Installer download triggered.', 'var(--success)');
        } finally {
            setInstallerLoading(false);
        }
    };

    const handleShare = async () => {
        const shareData = {
            title: `Check out "${movie.title}" on Streamore!`,
            text: `Download the latest movies in high quality with Streamore.`,
            url: window.location.href,
        };

        if (navigator.share) {
            try {
                await navigator.share(shareData);
            } catch (err) {
                console.log('Error sharing:', err);
            }
        } else {
            // Fallback: Copy to clipboard
            try {
                await navigator.clipboard.writeText(`${shareData.title}\n${shareData.url}`);
                setMsg('Link copied to clipboard! 🔗', 'var(--success)');
                setTimeout(() => setMsg('', ''), 3000);
            } catch (err) {
                setMsg('Share failed. Copy URL manually.', 'var(--error)');
            }
        }
    };

    const qualityColors: Record<string, string> = {
        '2160p': '#f59e0b', '1080p': '#6c63ff', '720p': '#22c55e', '480p': '#64748b',
    };

    // Render

    const downloadButtonLabel = () => {
        if (loading) return 'Please wait...';
        if (appState === 'checking') return 'Download';
        if (appState === 'yes') return 'Send to Desktop App';
        return 'Download Installer';
    };

    return (
        <div
            onClick={onClose}
            style={{
                position: 'fixed', inset: 0, zIndex: 200,
                background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: 16,
            }}
        >
            <div
                onClick={e => e.stopPropagation()}
                className="animate-fade-in"
                style={{
                    background: 'var(--bg-card)', borderRadius: 20,
                    border: '1px solid var(--border)',
                    width: '100%', maxWidth: 780, maxHeight: '90vh',
                    overflow: 'auto', padding: 32,
                    boxShadow: '0 40px 80px rgba(0,0,0,0.8)',
                }}
            >
                {/* Header */}
                <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
                    {movie.poster_url && (
                        <img src={movie.poster_url} alt={movie.title}
                            style={{ width: 120, height: 180, objectFit: 'cover', borderRadius: 12, flexShrink: 0 }} />
                    )}
                    <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8, lineHeight: 1.2 }}>{movie.title}</h2>
                            <button onClick={onClose} style={{
                                background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff',
                                width: 36, height: 36, borderRadius: 18, cursor: 'pointer',
                                fontSize: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>X</button>
                        </div>
                        <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
                            {movie.year && <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>{movie.year}</span>}
                            {movie.rating && (
                                <span style={{ color: '#f59e0b', fontSize: 14, fontWeight: 600 }}>Rating: {movie.rating}</span>
                            )}
                            {movie.genres?.map(g => (
                                <span key={g} style={{
                                    background: 'rgba(108,99,255,0.15)', color: 'var(--accent)',
                                    padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500,
                                }}>{g}</span>
                            ))}
                        </div>
                        {/* Trailer */}
                        {movie.yt_trailer_code && (
                            <div style={{ marginBottom: 24 }}>
                                <div style={{ 
                                    position: 'relative', width: '100%', aspectRatio: '16/9', 
                                    borderRadius: 12, overflow: 'hidden', background: '#000',
                                    border: '1px solid var(--border)'
                                }}>
                                    <iframe 
                                        width="100%" height="100%" 
                                        src={`https://www.youtube.com/embed/${movie.yt_trailer_code}`} 
                                        title="YouTube video player" frameBorder="0" 
                                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                                        allowFullScreen
                                        style={{ border: 'none' }}
                                    ></iframe>
                                </div>
                            </div>
                        )}

                        {movie.description && (
                            <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6, maxHeight: 100, overflow: 'auto' }}>
                                {movie.description}
                            </p>
                        )}
                        {!movie.description && (
                            <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6, maxHeight: 100, overflow: 'auto' }}>
                                No description available.
                            </p>
                        )}
                    </div>
                </div>

                {/* Desktop app detected badge */}
                {appState === 'yes' && (
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.25)',
                        borderRadius: 12, padding: '10px 16px', marginBottom: 16,
                        fontSize: 13, color: '#22c55e',
                    }}>
                        <span style={{ fontSize: 16 }}>Desktop</span>
                        <span><strong>Streamore Desktop</strong> detected - downloads will go straight to your PC, no ads!</span>
                    </div>
                )}
                {appState === 'no' && (
                    <div style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                        background: 'rgba(108,99,255,0.12)', border: '1px solid rgba(108,99,255,0.25)',
                        borderRadius: 12, padding: '10px 14px', marginBottom: 16,
                        fontSize: 13,
                    }}>
                        <span style={{ color: 'var(--text-secondary)' }}>
                            Desktop app not detected. Install it for automatic direct downloads.
                        </span>
                        <button
                            onClick={handleInstallerDownload}
                            disabled={installerLoading}
                            style={{
                                background: 'var(--accent)', color: '#fff', textDecoration: 'none',
                                borderRadius: 8, padding: '8px 12px', fontWeight: 700, whiteSpace: 'nowrap',
                                border: 'none', cursor: installerLoading ? 'not-allowed' : 'pointer',
                            }}
                        >
                            {installerLoading ? 'Preparing...' : 'Download Manager'}
                        </button>
                    </div>
                )}

                {/* Qualities */}
                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                    Select Quality
                </h3>
                {torrents.length === 0 ? (
                    <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 16 }}>No torrents available. Try refreshing.</p>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10, marginBottom: 20 }}>
                        {torrents.map((t, i) => (
                            <button key={i} onClick={() => setSelectedTorrent(t)} style={{
                                background: selectedTorrent === t ? 'var(--accent)' : 'rgba(255,255,255,0.04)',
                                border: `2px solid ${selectedTorrent === t ? 'var(--accent)' : 'var(--border)'}`,
                                borderRadius: 12, padding: '12px 16px', cursor: 'pointer', textAlign: 'left',
                                color: '#fff', transition: 'all 0.2s',
                            }}>
                                <div style={{ fontSize: 18, fontWeight: 800, color: selectedTorrent === t ? '#fff' : (qualityColors[t.quality] || '#fff') }}>
                                    {t.quality}
                                </div>
                                <div style={{ fontSize: 12, color: selectedTorrent === t ? 'rgba(255,255,255,0.7)' : 'var(--text-secondary)', marginTop: 2 }}>
                                    {t.type || 'BluRay'} - {t.size || '?'}
                                </div>
                                {t.seeds !== undefined && (
                                    <div style={{ fontSize: 11, color: selectedTorrent === t ? 'rgba(255,255,255,0.6)' : '#22c55e', marginTop: 4 }}>
                                        Seeds: {t.seeds}
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                )}

                {/* Status */}
                {status && (
                    <div style={{
                        background: 'rgba(255,255,255,0.04)', borderRadius: 10, padding: '10px 16px',
                        marginBottom: 16, color: statusColor, fontSize: 14,
                    }}>{status}</div>
                )}

                <div style={{ marginBottom: 16 }}>
                    <AffiliateBanner variant="compact" />
                </div>

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 10 }}>
                    <button
                        onClick={handleDownloadClick}
                        disabled={loading || !selectedTorrent}
                        style={{
                            flex: 1,
                            background: loading || !selectedTorrent
                                ? 'rgba(108,99,255,0.3)'
                                : appState === 'yes'
                                    ? 'linear-gradient(135deg, #22c55e, #16a34a)'
                                    : 'var(--accent)',
                            border: 'none', color: '#fff', borderRadius: 12, padding: '14px 24px',
                            fontSize: 15, fontWeight: 700,
                            cursor: loading || !selectedTorrent ? 'not-allowed' : 'pointer',
                            transition: 'all 0.2s',
                        }}
                    >
                        {downloadButtonLabel()}
                    </button>
                    <button
                        onClick={toggleWatchlist}
                        disabled={watchlistLoading}
                        style={{
                            background: 'rgba(255,255,255,0.06)', border: `1px solid ${isOnWatchlist ? 'var(--accent)' : 'var(--border)'}`,
                            color: isOnWatchlist ? 'var(--accent)' : 'var(--text-secondary)', borderRadius: 12, padding: '14px 18px',
                            fontSize: 14, display: 'flex', alignItems: 'center', gap: 6,
                            cursor: 'pointer', transition: 'all 0.2s',
                        }}
                    >
                        {isOnWatchlist ? '❤️ In Watchlist' : '🤍 Bookmark'}
                    </button>
                    <button
                        onClick={handleShare}
                        style={{
                            background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)',
                            color: 'var(--text-secondary)', borderRadius: 12, padding: '14px 18px',
                            fontSize: 14, display: 'flex', alignItems: 'center', gap: 6,
                            cursor: 'pointer', transition: 'all 0.2s',
                        }}
                    >
                        📤 Share
                    </button>
                </div>

                {adPhase && (
                    <div style={{
                        marginTop: 16, padding: 16, borderRadius: 12,
                        background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)',
                        color: '#f59e0b', fontSize: 14, textAlign: 'center',
                    }}>
                        Complete the step in the popup window, then close it. The download will start automatically!
                    </div>
                )}
            </div>

            {/* Install / detect banner */}
            {showInstallBanner && (
                <div
                    onClick={() => setShowInstallBanner(false)}
                    style={{
                        position: 'fixed', inset: 0, zIndex: 300,
                        background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(6px)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        padding: 16,
                    }}
                >
                    <div
                        onClick={e => e.stopPropagation()}
                        style={{
                            background: 'var(--bg-card)', borderRadius: 20,
                            border: '1px solid var(--border)', padding: 32,
                            maxWidth: 480, width: '100%',
                            boxShadow: '0 40px 80px rgba(0,0,0,0.8)',
                            textAlign: 'center',
                        }}
                    >
                        <div style={{ fontSize: 56, marginBottom: 12 }}>Desktop App</div>
                        <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>
                            Streamore Desktop App
                        </h2>
                        <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.7, marginBottom: 24 }}>
                            Download movies <strong>directly to your PC</strong> - no ads, no popups.
                            Install the free Streamore Desktop app and every download goes straight to your drive.
                        </p>

                        {/* Step 1 - already installed */}
                        <button
                            onClick={handleIHaveIt}
                            style={{
                                width: '100%', padding: '14px 20px', borderRadius: 12,
                                background: 'linear-gradient(135deg, #22c55e, #16a34a)',
                                border: 'none', color: '#fff',
                                fontSize: 15, fontWeight: 700, cursor: 'pointer', marginBottom: 10,
                            }}
                        >
                            I have it installed - connect now
                        </button>

                        {/* Step 2 - download installer */}
                        <button
                            onClick={handleInstallerDownload}
                            disabled={installerLoading}
                            style={{
                                display: 'block', width: '100%', padding: '13px 20px',
                                borderRadius: 12, border: '1px solid var(--border)',
                                background: 'rgba(108,99,255,0.12)', color: 'var(--accent)',
                                fontSize: 14, fontWeight: 600, textDecoration: 'none',
                                marginBottom: 10, boxSizing: 'border-box',
                                cursor: installerLoading ? 'not-allowed' : 'pointer',
                            }}
                        >
                            {installerLoading ? 'Preparing installer...' : 'Download Installer (.exe)'}
                        </button>

                        {/* Step 3 - skip */}
                        <button
                            onClick={handleSkipToWeb}
                            style={{
                                width: '100%', padding: '12px 20px', borderRadius: 12,
                                border: '1px solid var(--border)',
                                background: 'transparent', color: 'var(--text-secondary)',
                                fontSize: 13, fontWeight: 500, cursor: 'pointer',
                            }}
                        >
                            Skip - Use Web Download (shows an ad)
                        </button>

                        <p style={{ marginTop: 16, fontSize: 11, color: 'var(--text-secondary)', opacity: 0.6 }}>
                            The desktop app runs a tiny local server (port 57432) that this web page uses to detect it automatically.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}


