'use client';
import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

interface Download {
    id: string;
    movie_title: string;
    quality: string;
    state: string;
    progress: number;
    download_rate: number;
    upload_rate: number;
    size_total: number;
    size_downloaded: number;
    num_peers: number;
    num_seeds: number;
    eta: number;
    save_path: string;
    name?: string;
    error_message?: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'https://movie-project-backend.fly.dev';

function formatBytes(bytes: number): string {
    if (!bytes || bytes === 0) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function formatSpeed(bytesPerSec: number): string {
    if (!bytesPerSec) return '0 B/s';
    return formatBytes(bytesPerSec) + '/s';
}

const stateColor: Record<string, string> = {
    active: '#6c63ff',
    downloading: '#6c63ff',
    waiting: '#f59e0b',
    queued: '#f59e0b',
    complete: '#22c55e',
    completed: '#22c55e',
    error: '#ef4444',
    paused: '#64748b',
    pausing: '#64748b',
    removed: '#64748b',
};

const stateLabel: Record<string, string> = {
    active: '⬇️ Downloading',
    downloading: '⬇️ Downloading',
    waiting: '⏳ Queued',
    queued: '⏳ Queued',
    complete: '✅ Complete',
    completed: '✅ Complete',
    error: '❌ Error',
    paused: '⏸ Paused',
    pausing: '⏸ Pausing',
    removed: '🗑 Removed',
};

export default function DownloadManager() {
    const [downloads, setDownloads] = useState<Download[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [connected, setConnected] = useState(false);
    const [activeTab, setActiveTab] = useState<'all' | 'downloading' | 'paused' | 'completed' | 'error' | 'history'>('all');

    useEffect(() => {
        const socket: Socket = io(API, { transports: ['websocket', 'polling'] });
        socket.on('connect', () => {
             console.log("Socket connected");
             setConnected(true);
        });
        socket.on('disconnect', () => setConnected(false));
        socket.on('downloads_update', (data: { downloads: Download[] }) => {
            setDownloads(data.downloads || []);
        });

        const poll = async () => {
            try {
                const res = await fetch(`${API}/api/downloads`);
                const data = await res.json();
                if (data.downloads) setDownloads(data.downloads);
            } catch { }
        };
        poll();
        const interval = setInterval(poll, 5000);
        return () => { socket.disconnect(); clearInterval(interval); };
    }, []);

    const fetchHistory = async () => {
        try {
            const res = await fetch(`${API}/api/downloads/history`);
            const data = await res.json();
            if (data.success) setHistory(data.history || []);
        } catch { }
    };

    useEffect(() => {
        if (activeTab === 'history') fetchHistory();
    }, [activeTab]);

    const handleAction = async (id: string, action: string) => {
        try {
            const res = await fetch(`${API}/api/download/${id}/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: action === 'cancel' ? JSON.stringify({ delete_files: true }) : undefined,
            });
            const data = await res.json();
            if (!data.success) {
                alert(`Error: ${data.error}`);
            }
        } catch (err) {
            alert(`Failed to perform action: ${err}`);
        }
    };

    const tabs = [
        { id: 'all', label: 'All', icon: '📁' },
        { id: 'downloading', label: 'Downloading', icon: '⬇️' },
        { id: 'paused', label: 'Paused', icon: '⏸' },
        { id: 'completed', label: 'Completed', icon: '✅' },
        { id: 'error', label: 'Errors', icon: '❌' },
        { id: 'history', label: 'History', icon: '📜' },
    ];

    const filteredDownloads = downloads.filter(dl => {
        if (activeTab === 'all') return true;
        if (activeTab === 'downloading') return ['active', 'downloading', 'waiting', 'queued'].includes(dl.state);
        if (activeTab === 'paused') return ['paused', 'pausing'].includes(dl.state);
        if (activeTab === 'completed') return ['complete', 'completed'].includes(dl.state);
        if (activeTab === 'error') return dl.state === 'error';
        return true;
    });

    return (
        <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <h1 style={{ fontSize: 28, fontWeight: 800 }}>⬇️ Download Manager</h1>
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    fontSize: 13, color: connected ? 'var(--success)' : 'var(--text-secondary)',
                }}>
                    <div style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: connected ? 'var(--success)' : 'var(--error)',
                        animation: connected ? 'pulse-glow 2s infinite' : 'none',
                    }} />
                    {connected ? 'Live updates' : 'Polling...'}
                </div>
            </div>

            {/* Tabs */}
            <div style={{
                display: 'flex',
                gap: 8,
                marginBottom: 24,
                padding: '4px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '14px',
                border: '1px solid var(--border)',
                overflowX: 'auto'
            }}>
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        style={{
                            flex: 1,
                            minWidth: 'fit-content',
                            padding: '10px 16px',
                            borderRadius: '10px',
                            border: 'none',
                            background: activeTab === tab.id ? 'var(--accent)' : 'transparent',
                            color: activeTab === tab.id ? '#fff' : 'var(--text-secondary)',
                            fontWeight: 600,
                            fontSize: '14px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            transition: 'all 0.2s',
                        }}
                    >
                        <span>{tab.icon}</span>
                        {tab.label}
                        <span style={{
                            fontSize: '11px',
                            padding: '2px 6px',
                            borderRadius: '6px',
                            background: activeTab === tab.id ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.05)',
                            marginLeft: '4px'
                        }}>
                            {tab.id === 'history' ? history.length : downloads.filter(dl => {
                                if (tab.id === 'all') return true;
                                if (tab.id === 'downloading') return ['active', 'downloading', 'waiting', 'queued'].includes(dl.state);
                                if (tab.id === 'paused') return ['paused', 'pausing'].includes(dl.state);
                                if (tab.id === 'completed') return ['complete', 'completed'].includes(dl.state);
                                if (tab.id === 'error') return dl.state === 'error';
                                return true;
                            }).length}
                        </span>
                    </button>
                ))}
            </div>

            {activeTab === 'history' ? (
                history.length === 0 ? (
                    <div style={{
                        textAlign: 'center', padding: '80px 20px', color: 'var(--text-secondary)',
                        background: 'var(--bg-card)', borderRadius: 20, border: '1px solid var(--border)',
                    }}>
                        <div style={{ fontSize: 64, marginBottom: 16 }}>📜</div>
                        <p style={{ fontSize: 18, fontWeight: 600 }}>No history records</p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {history.map((h, i) => (
                            <div key={i} style={{
                                background: 'var(--bg-card)', borderRadius: 16,
                                border: '1px solid var(--border)', padding: 16,
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                            }}>
                                <div>
                                    <p style={{ fontWeight: 700, fontSize: 15 }}>{h.movie_title} {h.quality && `· ${h.quality}`}</p>
                                    <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                                        {h.id} · {h.completed_at ? new Date(h.completed_at).toLocaleString() : 'Date unknown'}
                                    </p>
                                </div>
                                <span style={{
                                    fontSize: 11, fontWeight: 700, padding: '4px 8px', borderRadius: 10,
                                    background: h.result === 'completed' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                                    color: h.result === 'completed' ? '#22c55e' : '#ef4444',
                                    textTransform: 'uppercase'
                                }}>
                                    {h.result}
                                </span>
                            </div>
                        ))}
                    </div>
                )
            ) : filteredDownloads.length === 0 ? (
                <div style={{
                    textAlign: 'center', padding: '80px 20px', color: 'var(--text-secondary)',
                    background: 'var(--bg-card)', borderRadius: 20, border: '1px solid var(--border)',
                }}>
                    <div style={{ fontSize: 64, marginBottom: 16 }}>
                        {activeTab === 'all' ? '📭' : activeTab === 'completed' ? '🎬' : '🔍'}
                    </div>
                    <p style={{ fontSize: 18, fontWeight: 600 }}>
                        {activeTab === 'all' ? 'No downloads yet' : `No ${activeTab} downloads`}
                    </p>
                    <p style={{ fontSize: 14, marginTop: 8 }}>
                        {activeTab === 'all' ? 'Browse movies and click Download to start' : `Check other tabs for more info`}
                    </p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {filteredDownloads.map(dl => (
                        <div key={dl.id} style={{
                            background: 'var(--bg-card)', borderRadius: 16,
                            border: '1px solid var(--border)', padding: 20,
                            transition: 'all 0.2s',
                        }}>
                             <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <p style={{
                                        fontWeight: 700, fontSize: 16,
                                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                        marginBottom: 2,
                                        color: 'var(--text-primary)',
                                    }}>
                                        {dl.movie_title}
                                        {dl.quality ? ` · ${dl.quality}` : ''}
                                    </p>
                                    <span style={{
                                        fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
                                        background: `${stateColor[dl.state] || '#64748b'}20`,
                                        color: stateColor[dl.state] || '#64748b',
                                        textTransform: 'uppercase',
                                    }}>
                                        {stateLabel[dl.state] || dl.state}
                                    </span>
                                </div>
                                <span style={{ fontSize: 22, fontWeight: 800, color: stateColor[dl.state] || '#fff', marginLeft: 16 }}>
                                    {dl.progress.toFixed(1)}%
                                </span>
                            </div>

                            <div style={{ height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, marginBottom: 12, overflow: 'hidden' }}>
                                <div style={{
                                    height: '100%', borderRadius: 3,
                                    width: `${dl.progress}%`,
                                    background: dl.state === 'complete' || dl.state === 'completed'
                                        ? 'var(--success)'
                                        : 'linear-gradient(90deg, var(--accent), #a78bfa)',
                                    transition: 'width 0.5s ease',
                                }} />
                            </div>

                            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>
                                <span>📦 {formatBytes(dl.size_downloaded)} / {formatBytes(dl.size_total)}</span>
                                {dl.download_rate > 0 && <span>⬇ {formatSpeed(dl.download_rate)}</span>}
                                {dl.eta > 0 && (dl.state === 'downloading' || dl.state === 'active') && <span>⏱ ETA {dl.eta}s</span>}
                            </div>

                            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                                {(dl.state === 'complete' || dl.state === 'completed') ? (
                                    <button onClick={() => handleAction(dl.id, 'play')} style={actionButtonStyle('#22c55e')}>
                                        ▶️ Play
                                    </button>
                                ) : (
                                    <button onClick={() => handleAction(dl.id, dl.state === 'paused' ? 'resume' : 'pause')} style={actionButtonStyle(dl.state === 'paused' ? '#6c63ff' : '#f59e0b')}>
                                        {dl.state === 'paused' ? '▶️ Resume' : '⏸ Pause'}
                                    </button>
                                )}
                                <button onClick={() => handleAction(dl.id, 'open-folder')} style={actionButtonStyle('var(--accent)')}>
                                    📂 Open Folder
                                </button>
                                <button onClick={() => { if (confirm('Remove this download?')) handleAction(dl.id, 'cancel'); }} style={actionButtonStyle('#ef4444')}>
                                    🛑 Stop
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

const actionButtonStyle = (color: string) => ({
    padding: '8px 16px',
    borderRadius: '10px',
    background: `${color}15`,
    color: color,
    border: `1px solid ${color}33`,
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    outline: 'none',
    ':hover': {
        background: `${color}25`,
        transform: 'translateY(-1px)',
    }
} as any);
