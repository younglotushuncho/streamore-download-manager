import type { Metadata } from "next";
import "./globals.css";
import { Analytics } from "../components/Analytics";

export const metadata: Metadata = {
  title: "Streamore — Movie Downloader",
  description: "Browse and download the best movies in HD quality.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#6c63ff" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />

        {/* === EXOCLICK SITE VERIFICATION === */}
        <meta name="6a97888e-site-verification" content="19c052422f743878ae4a0cd0a68aa632" />

        {/* === ADSTERRA POPUNDER SCRIPT === */}
        <script type='text/javascript' src='https://pl28868196.effectivegatecpm.com/8b/41/f1/8b41f1021deaf587d0694f64293f4038.js'></script>
      </head>
      <body>
        <Analytics />
        {children}
      </body>
    </html>
  );
}
