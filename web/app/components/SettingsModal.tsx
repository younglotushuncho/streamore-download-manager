'use client';
import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';

interface Props {
    onClose: () => void;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'https://movie-project-backend.fly.dev';

export default function SettingsModal({ onClose }: Props) {
    const [settings, setSettings] = useState<any>({
        organize_by_genre: true,
        max_download_speed: 0,
        max_upload_speed: 0,
        max_concurrent: 3,
        max_connections: 16,
        bt_max_peers: 0,
        seed_ratio: 0,
        seed_time: 0,
        enable_dht: true,
        enable_pex: true,
        download_path: '',
        theme_is_light: false,
        remove_torrent_after_send: false,
        language: 'en',
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            const res = await fetch(`${API}/api/settings`);
            const data = await res.json();
            if (data.success) {
                setSettings(data.settings);
                if (data.settings.theme_is_light) {
                    document.documentElement.setAttribute('data-theme', 'light');
                } else {
                    document.documentElement.removeAttribute('data-theme');
                }
            }
        } catch (err) {
            console.error('Failed to fetch settings:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setMessage('');
        try {
            const res = await fetch(`${API}/api/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings),
            });
            const data = await res.json();
            if (data.success) {
                setMessage('✅ Settings saved successfully!');
                setTimeout(() => setMessage(''), 3000);
            } else {
                setMessage(`❌ Error: ${data.error}`);
            }
        } catch (err) {
            setMessage('❌ Failed to save settings');
        } finally {
            setSaving(false);
        }
    };

    const handleApplyTorrentSettings = async () => {
        setSaving(true);
        setMessage('');
        try {
            const payload: any = {
                max_download_speed: settings.max_download_speed || 0,
                max_upload_speed: settings.max_upload_speed || 0,
                max_concurrent: settings.max_concurrent || 3,
                max_connections: settings.max_connections || 16,
                bt_max_peers: settings.bt_max_peers || 0,
                seed_ratio: settings.seed_ratio || 0,
                seed_time: settings.seed_time || 0,
                enable_dht: settings.enable_dht === true,
                enable_pex: settings.enable_pex === true,
            };

            const res = await fetch(`${API}/api/torrent-settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (data.success) {
                setMessage('✅ Torrent settings applied');
                setTimeout(() => setMessage(''), 3000);
            } else {
                setMessage(`❌ Error: ${data.error}`);
            }
        } catch (err) {
            setMessage('❌ Failed to apply torrent settings');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return null;

    const modal = (
        <div
            onClick={onClose}
            style={{
                position: 'fixed', inset: 0, zIndex: 99999,
                background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)',
                display: 'flex', justifyContent: 'center', alignItems: 'flex-start',
                padding: '10vh 16px', overflowY: 'auto'
            }}
        >
            <div
                onClick={e => e.stopPropagation()}
                style={{
                    background: 'var(--bg-card)', borderRadius: 20,
                    border: '1px solid var(--border)',
                    width: '100%', maxWidth: 500, padding: 32,
                    boxShadow: '0 40px 80px rgba(0,0,0,0.8)',
                    height: 'fit-content', margin: 'auto 0'
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                    <h2 style={{ fontSize: 24, fontWeight: 800 }}>⚙️ App Settings</h2>
                    <button onClick={onClose} style={{
                        background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff',
                        width: 36, height: 36, borderRadius: 18, cursor: 'pointer',
                        fontSize: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>×</button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    {/* General */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div>
                                <div style={{ fontWeight: 600, fontSize: 15 }}>Remove .torrent after send</div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Delete .torrent files after sending to aria2</div>
                            </div>
                            <input
                                type="checkbox"
                                checked={settings.remove_torrent_after_send}
                                onChange={e => setSettings({ ...settings, remove_torrent_after_send: e.target.checked })}
                                style={{ width: 20, height: 20, cursor: 'pointer' }}
                            />
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div>
                                <div style={{ fontWeight: 600, fontSize: 15 }}>Dark Mode</div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Toggle theme preference</div>
                            </div>
                            <input
                                type="checkbox"
                                checked={!settings.theme_is_light}
                                onChange={e => {
                                    const isDark = e.target.checked;
                                    setSettings({ ...settings, theme_is_light: !isDark });
                                    if (!isDark) {
                                        document.documentElement.setAttribute('data-theme', 'light');
                                    } else {
                                        document.documentElement.removeAttribute('data-theme');
                                    }
                                }}
                                style={{ width: 20, height: 20, cursor: 'pointer', accentColor: 'var(--accent)' }}
                            />
                        </div>

                        <div>
                            <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Language</label>
                            <select
                                value={settings.language}
                                onChange={e => setSettings({ ...settings, language: e.target.value })}
                                style={inputStyle as any}
                            >
                                <option value="en">English</option>
                                <option value="es">Español</option>
                                <option value="fr">Français</option>
                                <option value="de">Deutsch</option>
                            </select>
                        </div>

                        <div>
                            <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Downloads folder</label>
                            <input
                                type="text"
                                value={settings.download_path || ''}
                                onChange={e => setSettings({ ...settings, download_path: e.target.value })}
                                placeholder="Path on backend host"
                                style={inputStyle}
                            />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Logging Verbosity</label>
                                <select
                                    value={settings.log_level || 'INFO'}
                                    onChange={e => setSettings({ ...settings, log_level: e.target.value })}
                                    style={inputStyle as any}
                                >
                                    <option value="DEBUG">Debug (Verbose)</option>
                                    <option value="INFO">Info (Normal)</option>
                                    <option value="WARNING">Warning</option>
                                    <option value="ERROR">Error Only</option>
                                </select>
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Support Tools</label>
                                <button
                                    onClick={() => window.open(`${API}/api/logs/export`, '_blank')}
                                    style={{
                                        ...inputStyle, 
                                        background: 'rgba(255,255,255,0.1)', border: '1px dashed var(--border)',
                                        cursor: 'pointer', textAlign: 'center', fontWeight: 600
                                    }}
                                >
                                    📥 Export Logs
                                </button>
                            </div>
                        </div>

                        {/* Premium Card */}
                        <div style={{
                            marginTop: 16, padding: 18, borderRadius: 18,
                            background: 'linear-gradient(135deg, rgba(108,99,255,0.15), rgba(168,85,247,0.15))',
                            border: '1px solid rgba(168,85,247,0.3)',
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            boxShadow: '0 10px 20px rgba(0,0,0,0.1)'
                        }}>
                            <div>
                                <div style={{ fontWeight: 800, fontSize: 16, color: '#fff', marginBottom: 2 }}>🌟 Streamore Premium</div>
                                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Ad-free browsing, priority updates & more.</div>
                            </div>
                            <button 
                               onClick={() => alert('Streamore Premium will be available soon with easy Stripe payments. Stay tuned!')}
                               style={{ 
                                background: 'linear-gradient(135deg, #a855f7, #6c63ff)', border: 'none', 
                                borderRadius: 12, padding: '10px 18px', color: '#fff', fontWeight: 800, fontSize: 14, cursor: 'pointer',
                                boxShadow: '0 4px 12px rgba(108,99,255,0.3)', transition: 'transform 0.2s'
                            }} onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'} onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}>Go Pro</button>
                        </div>
                    </div>

                    {/* Organize by Genre */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                            <div style={{ fontWeight: 600, fontSize: 15 }}>Organize by Genre</div>
                            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Create subfolders for Action, Comedy, etc.</div>
                        </div>
                        <input
                            type="checkbox"
                            checked={settings.organize_by_genre}
                            onChange={e => setSettings({ ...settings, organize_by_genre: e.target.checked })}
                            style={{ width: 20, height: 20, cursor: 'pointer', accentColor: 'var(--accent)' }}
                        />
                    </div>

                    <div style={{ height: '1px', background: 'var(--border)' }} />

                    {/* Download Limits */}
                    <div>
                        <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16 }}>
                            Download Controls
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Max Speed (KiB/s)</label>
                                <input
                                    type="number"
                                    value={settings.max_download_speed || 0}
                                    onChange={e => setSettings({ ...settings, max_download_speed: parseInt(e.target.value) })}
                                    placeholder="0 = unlimited"
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Connections / server</label>
                                <input
                                    type="number"
                                    value={settings.max_connections || 16}
                                    onChange={e => setSettings({ ...settings, max_connections: parseInt(e.target.value) })}
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Max BitTorrent peers</label>
                                <input
                                    type="number"
                                    value={settings.bt_max_peers || 0}
                                    onChange={e => setSettings({ ...settings, bt_max_peers: parseInt(e.target.value) })}
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Seed time (min)</label>
                                <input
                                    type="number"
                                    value={settings.seed_time || 0}
                                    onChange={e => setSettings({ ...settings, seed_time: parseInt(e.target.value) })}
                                    style={inputStyle}
                                />
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: 13 }}>Enable DHT</div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Distributed Hash Table</div>
                                </div>
                                <input
                                    type="checkbox"
                                    checked={settings.enable_dht}
                                    onChange={e => setSettings({ ...settings, enable_dht: e.target.checked })}
                                    style={{ width: 20, height: 20, cursor: 'pointer' }}
                                />
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: 13 }}>Enable PEX</div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Peer Exchange</div>
                                </div>
                                <input
                                    type="checkbox"
                                    checked={settings.enable_pex}
                                    onChange={e => setSettings({ ...settings, enable_pex: e.target.checked })}
                                    style={{ width: 20, height: 20, cursor: 'pointer' }}
                                />
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: 13 }}>Anonymous Telemetry</div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Help us improve performance</div>
                                </div>
                                <input
                                    type="checkbox"
                                    checked={settings.telemetry_enabled !== false}
                                    onChange={e => {
                                        const val = e.target.checked;
                                        setSettings({ ...settings, telemetry_enabled: val });
                                        // Synchronize with GDPR consent for Analytics.tsx
                                        localStorage.setItem('gdpr_consent', val.toString());
                                    }}
                                    style={{ width: 20, height: 20, cursor: 'pointer', accentColor: 'var(--accent)' }}
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Max Upload (KiB/s)</label>
                                <input
                                    type="number"
                                    value={settings.max_upload_speed || 0}
                                    onChange={e => setSettings({ ...settings, max_upload_speed: parseInt(e.target.value) })}
                                    placeholder="0 = unlimited"
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Max Concurrent</label>
                                <input
                                    type="number"
                                    value={settings.max_concurrent || 3}
                                    onChange={e => setSettings({ ...settings, max_concurrent: parseInt(e.target.value) })}
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: 13, marginBottom: 6, color: 'var(--text-secondary)' }}>Seed Ratio</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={settings.seed_ratio || 0}
                                    onChange={e => setSettings({ ...settings, seed_ratio: parseFloat(e.target.value) })}
                                    placeholder="0 = off"
                                    style={inputStyle}
                                />
                            </div>
                        </div>
                    </div>

                    {message && (
                        <div style={{
                            padding: '12px', borderRadius: '10px',
                            background: message.startsWith('✅') ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                            color: message.startsWith('✅') ? '#22c55e' : '#ef4444',
                            fontSize: '14px', textAlign: 'center'
                        }}>
                            {message}
                        </div>
                    )}

                    <button
                        onClick={handleSave}
                        disabled={saving}
                        style={{
                            background: 'var(--accent)', color: '#fff', border: 'none',
                            borderRadius: '12px', padding: '14px', fontSize: '15px', fontWeight: 700,
                            cursor: saving ? 'not-allowed' : 'pointer', transition: 'all 0.2s', marginTop: 10,
                            opacity: saving ? 0.7 : 1
                        }}
                    >
                        {saving ? 'Saving...' : 'Save Settings'}
                    </button>
                    <button
                        onClick={handleApplyTorrentSettings}
                        disabled={saving}
                        style={{
                            background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border)',
                            borderRadius: '12px', padding: '12px', fontSize: '14px', fontWeight: 600,
                            cursor: saving ? 'not-allowed' : 'pointer', transition: 'all 0.2s', marginTop: 8,
                        }}
                    >
                        {saving ? 'Applying…' : 'Apply Torrent Settings'}
                    </button>
                </div>
            </div>
        </div>
    );

    // Render the modal into document.body so it sits above all app content
    if (typeof document !== 'undefined') {
        return createPortal(modal, document.body);
    }

    return null;
}

const inputStyle = {
    width: '100%',
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid var(--border)',
    borderRadius: '10px',
    padding: '10px 12px',
    color: '#fff',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s',
};
