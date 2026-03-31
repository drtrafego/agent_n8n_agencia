import { NextResponse } from 'next/server';
import { waDb } from '@/lib/db/whatsapp';
import { waMessages } from '@/lib/db/whatsapp-schema';
import { sql, eq, isNull, inArray } from 'drizzle-orm';
import { downloadMedia } from '@/lib/meta/client';
import { put } from '@vercel/blob';

export async function POST() {
  try {
    // Buscar mensagens de mídia sem URL
    const missing = await waDb
      .select({
        id: waMessages.id,
        waMessageId: waMessages.waMessageId,
        type: waMessages.type,
        mediaMimeType: waMessages.mediaMimeType,
      })
      .from(waMessages)
      .where(
        sql`${waMessages.type} IN ('audio', 'image', 'document')
            AND ${waMessages.mediaUrl} IS NULL
            AND ${waMessages.waMessageId} IS NOT NULL`
      )
      .limit(50);

    let fixed = 0;
    let failed = 0;
    const errors: string[] = [];

    for (const msg of missing) {
      if (!msg.waMessageId) continue;

      // O waMessageId no banco é o ID da mensagem, não o media ID.
      // Precisamos buscar o media ID no payload original do webhook log.
      // Alternativa: tentar baixar usando o waMessageId (não vai funcionar).
      // A Meta só permite baixar mídia se tiver o media ID, que é diferente do message ID.
      // Os media IDs expiram após 14 dias, então mídias antigas não podem ser re-baixadas.

      // Para novas mídias: o fix no webhook vai funcionar daqui pra frente.
      // Para mídias existentes: verificar se o media ID está no webhook log.

      const logs = await waDb.execute(sql`
        SELECT payload FROM wa_webhook_logs
        WHERE payload::text LIKE ${'%' + msg.waMessageId + '%'}
        ORDER BY created_at DESC LIMIT 1
      `);

      const logRows = logs as unknown as { payload: Record<string, unknown> }[];
      if (logRows.length === 0) { failed++; continue; }

      // Extrair media ID do payload
      const payload = logRows[0].payload;
      let mediaId: string | null = null;

      try {
        const entries = (payload as Record<string, unknown[]>).entry as Array<Record<string, unknown>>;
        for (const entry of entries) {
          const changes = entry.changes as Array<Record<string, Record<string, unknown>>>;
          for (const change of changes) {
            const messages = change.value?.messages as Array<Record<string, Record<string, string>>> | undefined;
            if (!messages) continue;
            for (const m of messages) {
              if (m.audio?.id) mediaId = m.audio.id;
              else if (m.image?.id) mediaId = m.image.id;
              else if (m.document?.id) mediaId = m.document.id;
              else if (m.video?.id) mediaId = m.video.id;
              else if (m.voice?.id) mediaId = m.voice.id;
            }
          }
        }
      } catch {
        failed++;
        errors.push(`${msg.id}: falha ao parsear payload`);
        continue;
      }

      if (!mediaId) { failed++; errors.push(`${msg.id}: media ID não encontrado no log`); continue; }

      const buffer = await downloadMedia(mediaId);
      if (!buffer) { failed++; errors.push(`${msg.id}: download falhou (media ID: ${mediaId})`); continue; }

      const mime = msg.mediaMimeType || 'application/octet-stream';
      const ext = (mime.split('/')[1] || 'bin').split(';')[0].trim();
      const filename = `${mediaId}.${ext}`;

      const blob = await put(`whatsapp/${mediaId}/${filename}`, buffer, {
        access: 'public',
        contentType: mime,
      });

      await waDb
        .update(waMessages)
        .set({ mediaUrl: blob.url })
        .where(eq(waMessages.id, msg.id));

      fixed++;
    }

    return NextResponse.json({ total: missing.length, fixed, failed, errors });
  } catch (err) {
    console.error('media-retry error:', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
