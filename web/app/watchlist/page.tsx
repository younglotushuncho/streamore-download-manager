import Navbar from '../components/Navbar';
import WatchlistGrid from '../components/WatchlistGrid';
import AdsterraBanner from '../components/AdsterraBanner';

export default function WatchlistPage() {
  return (
    <main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <div style={{ flex: 1 }}>
        <WatchlistGrid />
      </div>

      {/* Footer Banner */}
      <div style={{
        display: 'flex', justifyContent: 'center', alignItems: 'center',
        padding: '40px 20px', background: 'rgba(0,0,0,0.5)',
        borderTop: '1px solid var(--border)', marginTop: 'auto'
      }}>
        <div id="adsterra-banner-footer" style={{ width: '100%', maxWidth: 728, height: 90 }}>
          <AdsterraBanner id="YOUR_FOOTER_BANNER_KEY" width={728} height={90} />
        </div>
      </div>
    </main>
  );
}
