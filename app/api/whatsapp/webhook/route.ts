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
import { put, getDownloadUrl } from '@vercel/blob';

// Traduz o valor bruto de {{placement}} da Meta para label legível
function resolvePlacementFromUtm(raw: string): string | null {
  const MAP: Record<string, string> = {
    feed:                 'Instagram Feed',
    instagram_feed:       'Instagram Feed',
    story:                'Instagram Stories',
    instagram_stories:    'Instagram Stories',
    reels:                'Instagram Reels',
    instagram_reels:      'Instagram Reels',
    explore:              'Instagram Explore',
    instagram_explore:    'Instagram Explore',
    facebook_feed:        'Facebook Feed',
    facebook_stories:     'Facebook Stories',
    facebook_reels:       'Facebook Reels',
    marketplace:          'Facebook Marketplace',
    right_hand_column:    'Facebook Feed',
    audience_network:     'Audience Network',
    messenger_inbox:      'Messenger',
    messenger_stories:    'Messenger Stories',
  };
  return MAP[raw.toLowerCase().trim()] ?? raw;
}

function resolvePlacement(targeting: Record<string, unknown>): string | null {
  const platforms = (targeting.publisher_platforms as string[]) || [];

  // Mapeamento de position -> label legível
  const IG_LABELS: Record<string, string> = {
    stream: 'Instagram Feed',
    feed: 'Instagram Feed',
    story: 'Instagram Stories',
    reels: 'Instagram Reels',
    explore: 'Instagram Explore',
    explore_home: 'Instagram Explore',
    profile_feed: 'Instagram Feed',
  };
  const FB_LABELS: Record<string, string> = {
    feed: 'Facebook Feed',
    story: 'Facebook Stories',
    reels: 'Facebook Reels',
    video_feeds: 'Facebook Video',
    marketplace: 'Facebook Marketplace',
    right_hand_column: 'Facebook Feed',
    instant_article: 'Facebook Feed',
  };

  // Prioridade: instagram > facebook. Pega o placement mais específico (primeiro da lista).
  if (platforms.includes('instagram')) {
    const pos = (targeting.instagram_positions as string[]) || [];
    // Único placement → nome exato. Múltiplos → só a plataforma.
    if (pos.length === 1) return IG_LABELS[pos[0]] ?? 'Instagram';
    if (pos.length > 1) return 'Instagram';
    return 'Instagram Feed'; // advantage+ sem posição explícita
  }

  if (platforms.includes('facebook')) {
    const pos = (targeting.facebook_positions as string[]) || [];
    if (pos.length === 1) return FB_LABELS[pos[0]] ?? 'Facebook';
    if (pos.length > 1) return 'Facebook';
    return 'Facebook Feed';
  }

  if (platforms.length > 0) {
    const PLATFORM_LABELS: Record<string, string> = {
      audience_network: 'Audience Network',
      messenger: 'Messenger',
    };
    return PLATFORM_LABELS[platforms[0]] ?? platforms[0];
  }

  return null;
}

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

  // Forward para CRM externo (fire and forget)
  // O CRM roteia automaticamente pela tabela meta_integrations (phone_number_id, ig_account_id)
  const crmWebhookUrl = process.env.CRM_WEBHOOK_URL;
  const crmForwardToken = process.env.CRM_FORWARD_TOKEN;
  if (crmWebhookUrl && crmForwardToken) {
    after(async () => {
      try {
        const res = await fetch(crmWebhookUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-forward-token': crmForwardToken,
          },
          body,
        });
        console.log(`[CRM Forward] ${res.status}`);
      } catch (err) {
        console.error('[CRM Forward] Erro:', err);
      }
    });
  }

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

      // Detect referral e origem do lead
      // Click-to-WhatsApp ad → 'whatsapp_campanha'
      // Mensagem pre-preenchida do site → 'site'
      // Direto → 'whatsapp'
      const referral = msg.referral;
      const msgText = (msg.text?.body || '').toLowerCase();
      const isFromSite = msgText.includes('agente 24') || msgText.includes('cheguei do site') || msgText.includes('vi no site');
      const source = referral?.source_type === 'ad'
        ? 'whatsapp_campanha'
        : isFromSite
          ? 'site'
          : 'whatsapp';

      // Extrair dados de rastreamento do referral (Click-to-WhatsApp ads)
      const adId = referral?.source_id || null;
      const adHeadline = referral?.headline || null;
      const adBody = referral?.body || null;
      const adSourceUrl = referral?.source_url || null;

      // Parsear UTM params do source_url (Meta resolve {{placement}}, {{site_source_name}}, etc.)
      let utmPlacement: string | null = null;
      let utmSource: string | null = null;
      let utmMedium: string | null = null;
      let utmCampaign: string | null = null;
      let utmContent: string | null = null;
      if (adSourceUrl) {
        try {
          const urlParams = new URL(adSourceUrl).searchParams;
          utmPlacement = urlParams.get('utm_placement') || urlParams.get('placement') || null;
          utmSource   = urlParams.get('utm_source')   || null;
          utmMedium   = urlParams.get('utm_medium')   || null;
          utmCampaign = urlParams.get('utm_campaign') || null;
          utmContent  = urlParams.get('utm_content')  || null;
        } catch { /* URL inválida, ignora */ }
      }

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

      // Save source + tracking data in contacts table (n8n bot table)
      // Separado em operações simples para evitar falhas silenciosas
      try {
        const contactName = profile?.profile?.name || waId;

        // 1. Upsert básico: cria contato ou atualiza nome/last_lead_msg_at
        await waDb.execute(
          sql`INSERT INTO contacts (telefone, nome, source, last_lead_msg_at)
              VALUES (${waId}, ${contactName}, ${source}, NOW())
              ON CONFLICT (telefone) DO UPDATE SET
                nome = COALESCE(NULLIF(EXCLUDED.nome, contacts.telefone), contacts.nome),
                last_lead_msg_at = NOW()`
        );

        // 2. Atualizar source (whatsapp_campanha sobrescreve whatsapp/direto)
        await waDb.execute(
          sql`UPDATE contacts SET
                source = CASE
                  WHEN source IS NULL OR source = 'direto' THEN ${source}
                  WHEN source = 'whatsapp' AND ${source} != 'whatsapp' THEN ${source}
                  ELSE source
                END
              WHERE telefone = ${waId}`
        );

        // 3. Stage transition: sem_interesse → interesse quando lead volta a falar
        await waDb.execute(
          sql`UPDATE contacts SET
                stage = 'interesse',
                stage_updated_at = NOW()
              WHERE telefone = ${waId} AND stage = 'sem_interesse'`
        );

        // 4. Tracking de anúncio (somente se veio referral)
        if (adId) {
          await waDb.execute(
            sql`UPDATE contacts SET
                  ad_id        = ${adId},
                  utm_content  = ${utmContent  || adHeadline || ''},
                  utm_source   = ${utmSource   || adSourceUrl || ''},
                  utm_medium   = ${utmMedium   || adBody || ''},
                  utm_campaign = COALESCE(NULLIF(${utmCampaign || ''}, ''), utm_campaign),
                  placement    = COALESCE(NULLIF(${utmPlacement ? resolvePlacementFromUtm(utmPlacement) : ''}, ''), placement)
                WHERE telefone = ${waId}`
          );

          // Enriquecer dados via Meta Graph API (fire and forget)
          after(async () => {
            try {
              const metaToken = process.env.META_WHATSAPP_TOKEN;
              if (!metaToken) return;
              const adRes = await fetch(
                `https://graph.facebook.com/v21.0/${adId}?fields=name,adset_id,campaign_id,adset{name},campaign{name}&access_token=${metaToken}`
              );
              if (!adRes.ok) return;
              const adData = await adRes.json();
              const adName = adData.name || null;
              const campaignId = adData.campaign_id || adData.campaign?.id || null;
              const campaignName = adData.campaign?.name || null;
              const adsetId = adData.adset_id || adData.adset?.id || null;
              const adsetName = adData.adset?.name || null;
              if (adName || campaignId || adsetId) {
                await waDb.execute(
                  sql`UPDATE contacts SET
                    ad_name = COALESCE(${adName}, ad_name),
                    campaign_id = COALESCE(${campaignId}, campaign_id),
                    campaign_name = COALESCE(${campaignName}, campaign_name),
                    adset_id = COALESCE(${adsetId}, adset_id),
                    adset_name = COALESCE(${adsetName}, adset_name)
                  WHERE telefone = ${waId} AND ad_id = ${adId}`
                );
              }
              // Buscar placement do adset
              const fetchedAdsetId = adsetId || adData.adset?.id;
              if (fetchedAdsetId) {
                try {
                  const adsetRes = await fetch(
                    `https://graph.facebook.com/v21.0/${fetchedAdsetId}?fields=targeting&access_token=${metaToken}`
                  );
                  if (adsetRes.ok) {
                    const adsetData = await adsetRes.json();
                    const targeting = adsetData.targeting || {};
                    const placement = resolvePlacement(targeting);
                    if (placement) {
                      await waDb.execute(
                        sql`UPDATE contacts SET placement = ${placement} WHERE telefone = ${waId} AND placement IS NULL`
                      );
                    }
                  }
                } catch (err) {
                  console.error('[webhook] Erro ao buscar placement:', err);
                }
              }
            } catch (err) {
              console.error('[webhook] Erro enriquecer ad:', err);
            }
          });
        }
      } catch (contactsErr) {
        // NÃO bloqueia o fluxo: conversa e mensagem ainda serão salvas
        console.error('[webhook] Erro ao salvar contacts:', contactsErr);
      }

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
              access: 'private',
              contentType: mime,
            });
            mediaUrl = await getDownloadUrl(blob.url);
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
      console.error('[webhook] Erro ao processar mensagem:', msg?.from, msg?.id, err instanceof Error ? err.message : err, err instanceof Error ? err.stack : '');
    }
  }

  return NextResponse.json({ ok: true });
}
