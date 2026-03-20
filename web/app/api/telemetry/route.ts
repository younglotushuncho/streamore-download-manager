import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const data = await req.json();
    
    // In a real-world scenario, you would send this to PostHog, Mixpanel, Google Analytics, etc.
    // For now, we log it to standard output where Vercel/Fly logs will pick it up.
    console.log('[TELEMETRY_EVENT]', JSON.stringify({
      timestamp: new Date().toISOString(),
      ...data
    }));

    return NextResponse.json({ success: true, message: 'Telemetry received' });
  } catch (err) {
    console.error('[TELEMETRY_ERROR]', err);
    return NextResponse.json({ success: false, error: 'Invalid payload' }, { status: 400 });
  }
}
