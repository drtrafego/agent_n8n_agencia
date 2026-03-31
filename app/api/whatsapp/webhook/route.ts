import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';
import { after } from 'next/server';
import { eq, sql } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import {
  waContacts,
  waConversations,
  waMessages,
  waWebhookLogs,
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
    token === (process.env.META_WEBHOOK_VERIFY_TOKEN || '').trim()
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

    const secret = (process.env.META_APP_SECRET || '').trim();
    if (secret) {
      const computedExpected =
        'sha256=' +
        crypto.createHmac('sha256', secret).update(body).digest('hex');

      if (sig !== computedExpected) {
        return new Response('Unauthorized', { status: 401 });
      }
    }

    payload = JSON.parse(body);
  } catch {
    return NextResponse.json({ ok: true }); // SEMPRE 200 para a Meta
  }

  // Salvar log do webhook (fire and forget)
  waDb
    .insert(waWebhookLogs)
    .values({ payload: payload as Record<string, unknown>, status: 'processed' })
    .catch(console.error);

  const parsed = parseWebhookPayload(payload);
  if (!parsed) return NextResponse.json({ ok: true });

  // Processar updates de status (delivered/read)
  for (const statusUpdate of parsed.statuses) {
    await waDb
      .update(waMessages)
      .set({ status: statusUpdate.status })
      .where(eq(waMessages.waMessageId, statusUpdate.id))
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
        .from(waContacts)
        .where(eq(waContacts.waId, waId))
        .limit(1);

      // Detect referral — tudo que chega aqui é WhatsApp
      // Click-to-WhatsApp ad → 'whatsapp_campanha', direto → 'whatsapp'
      const referral = msg.referral;
      const source = referral?.source_type === 'ad' ? 'whatsapp_campanha' : 'whatsapp';

      if (!contact) {
        const [created] = await waDb
          .insert(waContacts)
          .values({
            waId,
            name: profile?.profile?.name ?? waId,
            phone: waId,
          })
          .returning();
        contact = created;
      } else if (profile?.profile?.name && !contact.name) {
        await waDb
          .update(waContacts)
          .set({ name: profile.profile.name, updatedAt: new Date() })
          .where(eq(waContacts.id, contact.id));
      }

      // Save source in contacts table (n8n bot table)
      // whatsapp_campanha sobrescreve whatsapp, mas nenhum sobrescreve google/meta
      await waDb.execute(
        sql`INSERT INTO contacts (telefone, nome, source, last_lead_msg_at)
            VALUES (${waId}, ${profile?.profile?.name ?? waId}, ${source}, NOW())
            ON CONFLICT (telefone) DO UPDATE SET
              source = CASE
                WHEN contacts.source IS NULL THEN ${source}
                WHEN contacts.source = 'whatsapp' AND ${source} = 'whatsapp_campanha' THEN ${source}
                WHEN contacts.source = 'direto' THEN ${source}
                ELSE contacts.source
              END,
              nome = COALESCE(NULLIF(${profile?.profile?.name ?? ''}, ''), contacts.nome),
              last_lead_msg_at = NOW()`
      );

      // Upsert conversa
      let [conv] = await waDb
        .select()
        .from(waConversations)
        .where(eq(waConversations.contactId, contact.id))
        .limit(1);

      if (!conv) {
        const [created] = await waDb
          .insert(waConversations)
          .values({ contactId: contact.id })
          .returning();
        conv = created;
      }

      // Verificar duplicata
      const existing = await waDb
        .select({ id: waMessages.id })
        .from(waMessages)
        .where(eq(waMessages.waMessageId, msg.id))
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
            const ext = (mime.split('/')[1] || 'bin').split(';')[0].trim();
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
        .insert(waMessages)
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
        .update(waConversations)
        .set({
          lastMessage: msgBody || '[mídia]',
          lastMessageAt: new Date(),
          unreadCount: conv.unreadCount + 1,
          updatedAt: new Date(),
        })
        .where(eq(waConversations.id, conv.id));

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

      // Se bot ativo → encaminhar para n8n no formato que o workflow espera
      // Roteamento por phone_number_id: cada número pode ter seu próprio webhook n8n
      if (conv.botActive) {
        const incomingPhoneNumberId = parsed.value.metadata?.phone_number_id;
        let targetWebhookUrl: string | undefined;

        if (
          process.env.META_PHONE_NUMBER_ID_AD &&
          incomingPhoneNumberId === process.env.META_PHONE_NUMBER_ID_AD &&
          process.env.N8N_WEBHOOK_URL_AD
        ) {
          // Número do advogado → agent_adv_trial
          targetWebhookUrl = process.env.N8N_WEBHOOK_URL_AD;
        } else if (process.env.N8N_WEBHOOK_URL) {
          // Número padrão → workflow existente (sem mudança)
          targetWebhookUrl = process.env.N8N_WEBHOOK_URL;
        }

        if (targetWebhookUrl) {
          const n8nPayload = JSON.stringify({
            object: 'whatsapp_business_account',
            entry: [{
              changes: [{
                value: {
                  messaging_product: 'whatsapp',
                  messages: [msg],
                  contacts: parsed.contacts,
                  metadata: parsed.value.metadata,
                },
              }],
            }],
          });

          const webhookUrl = targetWebhookUrl;
          after(async () => {
            try {
              await fetch(webhookUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: n8nPayload,
              });
            } catch (err) {
              console.error('Erro ao notificar n8n:', err);
            }
          });
        }
      }
    } catch (err) {
      console.error('Erro ao processar mensagem:', err);
    }
  }

  return NextResponse.json({ ok: true });
}
