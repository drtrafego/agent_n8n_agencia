import { NextRequest, NextResponse } from 'next/server';
import { waDb } from '@/lib/db/whatsapp';
import { waWebhookLogs } from '@/lib/db/whatsapp-schema';
import { desc } from 'drizzle-orm';

const GRAPH_API_VERSION = 'v25.0';

async function checkMetaApi(): Promise<{ ok: boolean; detail: string }> {
  try {
    const phoneId = process.env.META_PHONE_NUMBER_ID;
    const token = process.env.META_WHATSAPP_TOKEN;
    if (!phoneId || !token) {
      return { ok: false, detail: 'META_PHONE_NUMBER_ID or META_WHATSAPP_TOKEN not set' };
    }
    const res = await fetch(
      `https://graph.facebook.com/${GRAPH_API_VERSION}/${phoneId}?fields=verified_name`,
      { headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(8000) }
    );
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      return { ok: false, detail: json?.error?.message || `HTTP ${res.status}` };
    }
    const json = await res.json();
    return { ok: true, detail: `verified_name: ${json.verified_name ?? 'OK'}` };
  } catch (err) {
    return { ok: false, detail: String(err) };
  }
}

async function checkSupabase(): Promise<{ ok: boolean; detail: string }> {
  try {
    const result = await waDb.execute<{ now: string }>(
      /* sql */ `SELECT now()::text AS now`
    );
    return { ok: true, detail: `DB time: ${(result as any)?.[0]?.now ?? 'connected'}` };
  } catch (err) {
    return { ok: false, detail: String(err) };
  }
}

async function checkN8n(): Promise<{ ok: boolean; detail: string }> {
  try {
    const url = process.env.N8N_WEBHOOK_URL;
    if (!url) {
      return { ok: false, detail: 'N8N_WEBHOOK_URL not set' };
    }
    // HEAD request to check reachability (n8n webhooks return 404 on GET but the host is reachable)
    const res = await fetch(url, {
      method: 'HEAD',
      signal: AbortSignal.timeout(8000),
    });
    // n8n may return various codes; as long as we got a response the host is reachable
    return { ok: true, detail: `Reachable (HTTP ${res.status})` };
  } catch (err) {
    return { ok: false, detail: String(err) };
  }
}

export async function GET(_req: NextRequest) {
  try {
    // Fetch recent webhook logs
    const logs = await waDb
      .select()
      .from(waWebhookLogs)
      .orderBy(desc(waWebhookLogs.createdAt))
      .limit(50);

    // Health checks in parallel
    const [meta, supabase, n8n] = await Promise.all([
      checkMetaApi(),
      checkSupabase(),
      checkN8n(),
    ]);

    return NextResponse.json({
      health: { meta, supabase, n8n },
      logs,
      fetchedAt: new Date().toISOString(),
    });
  } catch (err) {
    console.error('/api/logs error:', err);
    return NextResponse.json(
      { error: 'Failed to fetch logs', detail: String(err) },
      { status: 500 }
    );
  }
}
