import { NextRequest, NextResponse } from 'next/server';

/**
 * Cron job: sincroniza tokens do n8n diariamente as 8h BRT.
 * Configurado em vercel.json com schedule "0 11 * * *" (11 UTC = 8 BRT).
 * Protegido por CRON_SECRET para evitar chamadas externas.
 */
export async function GET(req: NextRequest) {
  // Verificar CRON_SECRET (Vercel injeta automaticamente)
  const authHeader = req.headers.get('authorization');
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://agente.casaldotrafego.com';
    const res = await fetch(`${baseUrl}/api/tokens/sync`, {
      method: 'POST',
      cache: 'no-store',
    });
    const data = await res.json();

    console.log('[CRON] sync-tokens:', JSON.stringify(data));

    return NextResponse.json({
      ok: true,
      timestamp: new Date().toISOString(),
      ...data,
    });
  } catch (err) {
    console.error('[CRON] sync-tokens error:', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
