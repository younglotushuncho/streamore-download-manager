'use client';

interface AffiliateBannerProps {
  variant?: 'compact' | 'card';
}

const affiliateUrl = process.env.NEXT_PUBLIC_AFFILIATE_URL || '';
const affiliateTitle = process.env.NEXT_PUBLIC_AFFILIATE_TITLE || 'Secure Your Downloads';
const affiliateText =
  process.env.NEXT_PUBLIC_AFFILIATE_TEXT ||
  'Use a VPN for safer, faster downloads and access from anywhere.';
const affiliateCta = process.env.NEXT_PUBLIC_AFFILIATE_CTA || 'Get Offer';

export default function AffiliateBanner({ variant = 'card' }: AffiliateBannerProps) {
  if (!affiliateUrl) return null;

  const baseStyle: React.CSSProperties = {
    border: '1px solid var(--border)',
    borderRadius: 14,
    background: 'rgba(108,99,255,0.12)',
    padding: variant === 'compact' ? '10px 14px' : '16px 18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  };

  return (
    <div style={baseStyle}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontWeight: 800, fontSize: variant === 'compact' ? 13 : 15, color: '#fff' }}>
          {affiliateTitle}
        </div>
        <div style={{ fontSize: variant === 'compact' ? 12 : 13, color: 'var(--text-secondary)' }}>
          {affiliateText}
        </div>
      </div>
      <a
        href={affiliateUrl}
        target="_blank"
        rel="noreferrer"
        style={{
          background: 'var(--accent)',
          color: '#fff',
          borderRadius: 10,
          padding: variant === 'compact' ? '8px 12px' : '10px 14px',
          fontWeight: 700,
          fontSize: variant === 'compact' ? 12 : 13,
          textDecoration: 'none',
          whiteSpace: 'nowrap',
        }}
      >
        {affiliateCta}
      </a>
    </div>
  );
}
