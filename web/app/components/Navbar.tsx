'use client';
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import SettingsModal from './SettingsModal';
import AdsterraBanner from './AdsterraBanner';

export default function Navbar() {
    const pathname = usePathname();
    const [mobileOpen, setMobileOpen] = useState(false);
    const [showSettings, setShowSettings] = useState(false);

    const links = [
        { href: '/', label: '🎬 Browse' },
        { href: '/watchlist', label: '❤️ Watchlist' },
        { href: '/downloads', label: '⬇️ Downloads' },
    ];

    return (
        <nav style={{
            position: 'sticky', top: 0, zIndex: 1000,
            background: 'rgba(10,10,15,0.85)',
            backdropFilter: 'blur(16px)',
            borderBottom: '1px solid var(--border)',
            padding: '0 24px',
        }}>
            <div style={{
                maxWidth: 1400, margin: '0 auto',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                height: 64,
            }}>
                {/* Logo */}
                <Link href="/" style={{ textDecoration: 'none' }}>
                    <span style={{
                        fontSize: 22, fontWeight: 800, letterSpacing: '-0.5px',
                        background: 'linear-gradient(135deg, #6c63ff, #a78bfa)',
                        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                    }}>
                        ▶ Streamore
                    </span>
                </Link>

                {/* Mobile Toggle */}
                <button
                    onClick={() => setMobileOpen(!mobileOpen)}
                    style={{
                        display: 'none', // Shown via media query in production or keep hidden for now if desktop-first
                        border: 'none', background: 'transparent', color: '#fff', fontSize: 24, cursor: 'pointer'
                    }}
                    className="mobile-toggle"
                >
                    {mobileOpen ? '✕' : '☰'}
                </button>

                {/* Desktop nav */}
                <div style={{ display: 'flex', gap: 16, alignItems: 'center' }} className="nav-content">
                    {/* === ADSTERRA DYNAMIC BANNER === */}
                    <div id="adsterra-banner-nav" style={{ minWidth: 200, height: 40, overflow: 'hidden' }} className="nav-banner">
                        <AdsterraBanner id="YOUR_BANNER_KEY" width={468} height={60} />
                    </div>

                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        {links.map(l => (
                            <Link key={l.href} href={l.href} style={{
                                textDecoration: 'none',
                                padding: '8px 12px',
                                borderRadius: 10,
                                fontSize: 13, fontWeight: 500,
                                color: pathname === l.href ? '#fff' : 'var(--text-secondary)',
                                background: pathname === l.href ? 'var(--accent)' : 'transparent',
                                transition: 'all 0.2s',
                                whiteSpace: 'nowrap'
                            }}>
                                {l.label}
                            </Link>
                        ))}

                        <button
                            onClick={() => {
                                const shareData = {
                                    title: 'Streamore — Download HD Movies',
                                    text: 'Check out Streamore for the best movie download experience!',
                                    url: window.location.origin
                                };
                                if (navigator.share) {
                                    navigator.share(shareData).catch(() => {});
                                } else {
                                    navigator.clipboard.writeText(window.location.origin);
                                    alert('Link copied to clipboard!');
                                }
                            }}
                            style={{
                                border: 'none',
                                padding: '8px 12px',
                                borderRadius: 10,
                                fontSize: 13, fontWeight: 500,
                                color: 'var(--text-secondary)',
                                background: 'rgba(255,255,255,0.05)',
                                transition: 'all 0.2s',
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                            }}
                        >
                            📤 Share
                        </button>
                        
                        <button
                            onClick={() => setShowSettings(true)}
                            style={{
                                border: 'none',
                                padding: '8px 12px',
                                borderRadius: 10,
                                fontSize: 13, fontWeight: 500,
                                color: showSettings ? '#fff' : 'var(--text-secondary)',
                                background: showSettings ? 'var(--accent)' : 'rgba(255,255,255,0.05)',
                                transition: 'all 0.2s',
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                            }}
                        >
                            ⚙️ Settings
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile Nav Menu */}
            {mobileOpen && (
                <div style={{
                    paddingBottom: 16,
                    display: 'flex', flexDirection: 'column', gap: 8,
                    padding: '0 24px 16px',
                    background: 'var(--bg-card)',
                    borderBottom: '1px solid var(--border)',
                }}>
                    {links.map(l => (
                        <Link key={l.href} href={l.href} onClick={() => setMobileOpen(false)} style={{
                            textDecoration: 'none',
                            padding: '12px 16px', borderRadius: 10,
                            fontSize: 15, fontWeight: 500,
                            color: pathname === l.href ? '#fff' : 'var(--text-secondary)',
                            background: pathname === l.href ? 'linear-gradient(135deg, #6c63ff, #8b5cf6)' : 'rgba(255,255,255,0.03)',
                        }}>
                            {l.label}
                        </Link>
                    ))}
                    <button onClick={() => { setShowSettings(true); setMobileOpen(false); }} style={{
                        textAlign: 'left',
                        border: 'none', padding: '12px 16px', borderRadius: 10,
                        fontSize: 15, fontWeight: 500, color: 'var(--text-secondary)',
                        background: 'rgba(255,255,255,0.03)', width: '100%', cursor: 'pointer'
                    }}>
                        ⚙️ Settings
                    </button>
                    <button 
                        onClick={() => {
                            const shareData = {
                                title: 'Streamore — Download HD Movies',
                                text: 'Check out Streamore for the best movie download experience!',
                                url: window.location.origin
                            };
                            if (navigator.share) {
                                navigator.share(shareData).catch(() => {});
                            } else {
                                navigator.clipboard.writeText(window.location.origin);
                                alert('Link copied to clipboard!');
                            }
                            setMobileOpen(false);
                        }}
                        style={{
                            textAlign: 'left',
                            border: 'none', padding: '12px 16px', borderRadius: 10,
                            fontSize: 15, fontWeight: 500, color: 'var(--text-secondary)',
                            background: 'rgba(255,255,255,0.03)', width: '100%', cursor: 'pointer'
                        }}
                    >
                        📤 Share App
                    </button>
                </div>
            )}

            {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
        </nav>
    );
}
