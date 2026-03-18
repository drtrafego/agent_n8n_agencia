import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';
import { after } from 'next/server';
import { eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import {
  contacts,
  conversations,
  messages,
  webhookLogs,
} from '@/lib/db/whatsapp-schema';
import { emitSSE } from '@/lib/sse/emitter';
import {
  parseWebhookPayload,
  getMessageText,
  getMediaId,
  getMimeType,
  getFilename,
  type MetaWebhookPayload,
} from '@/lib/meta/webhook';
import { downloadMedia } from '@/lib/meta/client';
import { put } from '@vercel/blob';

// GET — verificação do webhook pela Meta
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const mode = searchParams.get('hub.mode');
  const token = searchParams.get('hub.verify_token');
  const challenge = searchParams.get('hub.challenge');

  if (
    mode === 'subscribe' &&
    token === process.env.META_WEBHOOK_VERIFY_TOKEN
  ) {
    return new Response(challenge, { status: 200 });
  }
  return new Response('Forbidden', { status: 403 });
}

// POST — receber mensagens
export async function POST(req: NextRequest) {
  let body = '';
  let payload: MetaWebhookPayload;

  try {
    body = await req.text();

    // Validar assinatura HMAC
    const sig = req.headers.get('x-hub-signature-256') ?? '';
    const expected =
      'sha256=' +
      crypto
        .createHmac('sha256', process.env.META_APP_SECRET!)
        .update(body)
        .digest('hex');

    if (process.env.META_APP_SECRET && sig !== expected) {
      return new Response('Unauthorized', { status: 401 });
    }

    payload = JSON.parse(body);
  } catch {
    return NextResponse.json({ ok: true }); // SEMPRE 200 para a Meta
  }

  // Salvar log do webhook (fire and forget)
  waDb
    .insert(webhookLogs)
    .values({ payload: payload as Record<string, unknown>, status: 'processed' })
    .catch(console.error);

  const parsed = parseWebhookPayload(payload);
  if (!parsed) return NextResponse.json({ ok: true });

  // Processar updates de status (delivered/read)
  for (const statusUpdate of parsed.statuses) {
    await waDb
      .update(messages)
      .set({ status: statusUpdate.status })
      .where(eq(messages.waMessageId, statusUpdate.id))
      .catch(console.error);
  }

  // Processar mensagens recebidas
  for (const msg of parsed.messages) {
    try {
      const waId = msg.from;
      const profile = parsed.contacts.find((c) => c.wa_id === waId);

      // Upsert contato
      let [contact] = await waDb
        .select()
        .from(contacts)
        .where(eq(contacts.waId, waId))
        .limit(1);

      if (!contact) {
        const [created] = await waDb
          .insert(contacts)
          .values({
            waId,
            name: profile?.profile?.name ?? waId,
            phone: waId,
          })
          .returning();
        contact = created;
      } else if (profile?.profile?.name && !contact.name) {
        await waDb
          .update(contacts)
          .set({ name: profile.profile.name, updatedAt: new Date() })
          .where(eq(contacts.id, contact.id));
      }

      // Upsert conversa
      let [conv] = await waDb
        .select()
        .from(conversations)
        .where(eq(conversations.contactId, contact.id))
        .limit(1);

      if (!conv) {
        const [created] = await waDb
          .insert(conversations)
          .values({ contactId: contact.id })
          .returning();
        conv = created;
      }

      // Verificar duplicata
      const existing = await waDb
        .select({ id: messages.id })
        .from(messages)
        .where(eq(messages.waMessageId, msg.id))
        .limit(1);

      if (existing.length > 0) continue;

      // Processar mídia
      let mediaUrl: string | null = null;
      const mediaId = getMediaId(msg);

      if (mediaId) {
        try {
          const buffer = await downloadMedia(mediaId);
          if (buffer) {
            const mime = getMimeType(msg) || 'application/octet-stream';
            const ext = mime.split('/')[1] || 'bin';
            const filename = getFilename(msg) || `${mediaId}.${ext}`;
            const blob = await put(`whatsapp/${mediaId}/${filename}`, buffer, {
              access: 'public',
              contentType: mime,
            });
            mediaUrl = blob.url;
          }
        } catch (err) {
          console.error('Erro ao baixar mídia:', err);
        }
      }

      const msgBody = getMessageText(msg);

      // Inserir mensagem
      const [saved] = await waDb
        .insert(messages)
        .values({
          conversationId: conv.id,
          contactId: contact.id,
          waMessageId: msg.id,
          direction: 'inbound',
          type: msg.type,
          body: msgBody,
          mediaUrl,
          mediaMimeType: getMimeType(msg),
          mediaFilename: getFilename(msg),
          status: 'received',
          sentBy: 'contact',
        })
        .returning();

      // Atualizar conversa
      await waDb
        .update(conversations)
        .set({
          lastMessage: msgBody || '[mídia]',
          lastMessageAt: new Date(),
          unreadCount: conv.unreadCount + 1,
          updatedAt: new Date(),
        })
        .where(eq(conversations.id, conv.id));

      // Emitir SSE
      emitSSE({
        type: 'message',
        conversationId: conv.id,
        message: saved as Record<string, unknown>,
      });
      emitSSE({
        type: 'conversation-update',
        conversationId: conv.id,
        lastMessage: msgBody || '[mídia]',
        lastMessageAt: new Date().toISOString(),
        unreadCount: conv.unreadCount + 1,
      });

      // Se bot ativo → encaminhar para n8n
      if (conv.botActive && process.env.N8N_WEBHOOK_URL) {
        const n8nPayload = JSON.stringify({
          contact,
          conversation: conv,
          message: saved,
          raw: msg,
        });

        after(async () => {
          try {
            await fetch(process.env.N8N_WEBHOOK_URL!, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: n8nPayload,
            });
          } catch (err) {
            console.error('Erro ao notificar n8n:', err);
          }
        });
      }
    } catch (err) {
      console.error('Erro ao processar mensagem:', err);
    }
  }

  return NextResponse.json({ ok: true });
}
