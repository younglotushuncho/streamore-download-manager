'use client';
import { useReportWebVitals } from 'next/web-vitals';
import { useEffect, useState } from 'react';

export function Analytics() {
  const [consent, setConsent] = useState<boolean | null>(null);

  useEffect(() => {
    // Check local storage for existing consent preference
    const saved = localStorage.getItem('gdpr_consent');
    if (saved === 'true') setConsent(true);
    else if (saved === 'false') setConsent(false);
  }, []);

  const handleConsent = (choice: boolean) => {
    setConsent(choice);
    localStorage.setItem('gdpr_consent', choice.toString());
  };

  // 1. Next.js Web Vitals tracking (Skip if no consent)
  useReportWebVitals((metric: any) => {
    if (consent !== true) return;
    
    // Only send the core vitals we care about for performance budget
    if (['LCP', 'FID', 'CLS', 'FCP', 'TTFB'].includes(metric.name)) {
      fetch('/api/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_version: 'web',
          event: 'web_vital',
          properties: {
            metric: metric.name,
            value: metric.value,
            rating: metric.rating,
          }
        }),
      }).catch(() => {});
    }
  });

  // 2. Track page views and ad script load guardrails (Skip if no consent)
  useEffect(() => {
    if (consent !== true) return;

    // Send a pageview event
    fetch('/api/telemetry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        app_version: 'web',
        event: 'pageview',
        properties: { path: window.location.pathname }
      }),
    }).catch(() => {});

    // Monitor for Ad Loading performance
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name.includes('effectivegatecpm')) {
          fetch('/api/telemetry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              app_version: 'web',
              event: 'ad_load',
              properties: {
                load_time_ms: entry.duration,
                start_time_ms: entry.startTime
              }
            }),
          }).catch(() => {});
        }
      }
    });

    try {
      observer.observe({ entryTypes: ['resource'] });
    } catch (e) {}

    return () => observer.disconnect();
  }, [consent]);

  // If consent as not been given (either true or false), show banner
  if (consent === null) {
      return (
          <div style={{
              position: 'fixed', bottom: 20, left: 20, right: 20,
              background: 'var(--bg-card, #1a1a1f)', border: '1px solid var(--border, #2e2e36)',
              borderRadius: 16, padding: '16px 24px', zIndex: 999999,
              boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              gap: 20, flexWrap: 'wrap'
          }}>
              <div style={{ flex: 1, minWidth: 300 }}>
                  <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4, color: '#fff' }}>🍪 Privacy & Cookies</div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary, #a1a1aa)' }}>
                      We use anonymous telemetry and basic cookies to improve your movie experience. 
                      No personal data is collected. By clicking Accept, you agree to our 
                      <span style={{ color: 'var(--accent, #6366f1)', marginLeft: 4, cursor: 'pointer' }}>Privacy Policy</span>.
                  </div>
              </div>
              <div style={{ display: 'flex', gap: 12 }}>
                  <button 
                      onClick={() => handleConsent(false)}
                      style={{ 
                          background: 'transparent', border: '1px solid var(--border, #2e2e36)', 
                          color: 'var(--text-secondary, #a1a1aa)', padding: '8px 16px', borderRadius: 8, cursor: 'pointer' 
                      }}
                  >Decline</button>
                  <button 
                      onClick={() => handleConsent(true)}
                      style={{ 
                          background: 'var(--accent, #6366f1)', border: 'none', 
                          color: '#fff', padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontWeight: 600
                      }}
                  >Accept All</button>
              </div>
          </div>
      );
  }

  return null;
}
