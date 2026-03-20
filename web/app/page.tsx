import Navbar from './components/Navbar';
import MovieGrid from './components/MovieGrid';
import AdsterraBanner from './components/AdsterraBanner';
import AffiliateBanner from './components/AffiliateBanner';

export default function HomePage() {
  return (
    <main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <div style={{ flex: 1 }}>
        <MovieGrid />
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', width: '100%', padding: '0 20px 24px' }}>
        <AffiliateBanner />
      </div>

      {/* Footer Banner */}
      <div style={{
        display: 'flex', justifyContent: 'center', alignItems: 'center',
        padding: '40px 20px', background: 'rgba(0,0,0,0.5)',
        borderTop: '1px solid var(--border)', marginTop: 'auto'
      }}>
        {/* === ADSTERRA BANNER PLACEHOLDER === */}
        {/* Paste your Adsterra Banner Script (e.g. 728x90) inside this div */}
        {/* === ADSTERRA DYNAMIC BANNER === */}
        <div id="adsterra-banner-footer" style={{ width: '100%', maxWidth: 728, height: 90 }}>
          {/* Replace 'YOUR_FOOTER_BANNER_KEY' with your actual Adsterra banner key */}
          <AdsterraBanner id="YOUR_FOOTER_BANNER_KEY" width={728} height={90} />
        </div>
      </div>
    </main>
  );
}
