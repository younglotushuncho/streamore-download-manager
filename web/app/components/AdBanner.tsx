'use client';
import { useEffect } from 'react';
import Script from 'next/script';

export default function AdBanner({ zoneId }: { zoneId: string }) {
    useEffect(() => {
        // Run the ExoClick trigger push command required for SPA rendering
        if (typeof window !== 'undefined') {
            const w = window as any;
            w.AdProvider = w.AdProvider || [];
            w.AdProvider.push({ "serve": {} });
        }
    }, [zoneId]);

    return (
        <div style={{ width: '100%', display: 'flex', justifyContent: 'center', margin: '20px 0' }}>
            <Script src="https://a.magsrv.com/ad-provider.js" strategy="lazyOnload" />
            <ins className="eas6a97888e2" data-zoneid={zoneId}></ins>
        </div>
    );
}
