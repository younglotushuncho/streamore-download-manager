'use client';
import { useEffect, useRef } from 'react';

interface AdsterraBannerProps {
    id: string;
    width: number;
    height: number;
}

export default function AdsterraBanner({ id, width, height }: AdsterraBannerProps) {
    const bannerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (bannerRef.current && !bannerRef.current.firstChild) {
            const atOptions = {
                'key': id,
                'format': 'iframe',
                'height': height,
                'width': width,
                'params': {}
            };

            const confScript = document.createElement('script');
            confScript.type = 'text/javascript';
            confScript.innerHTML = `atOptions = ${JSON.stringify(atOptions)}`;

            const adScript = document.createElement('script');
            adScript.type = 'text/javascript';
            adScript.src = `http${window.location.protocol === 'https:' ? 's' : ''}://www.highperformancedisplayformat.com/${id}/invoke.js`;

            bannerRef.current.appendChild(confScript);
            bannerRef.current.appendChild(adScript);
        }
    }, [id, width, height]);

    return (
        <div
            ref={bannerRef}
            style={{
                width: '100%',
                maxWidth: width,
                height: height,
                margin: '0 auto',
                overflow: 'hidden',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: 8
            }}
        />
    );
}
