import { NextRequest, NextResponse } from 'next/server';
import { eq, sql } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { waConversations, waMessages, waContacts } from '@/lib/db/whatsapp-schema';
import { emitSSE } from '@/lib/sse/emitter';
import { sendTextMessage } from '@/lib/meta/client';

// Endpoint chamado pelo n8n para enviar mensagem do bot
// Envia via Meta API E salva no banco para exibir no frontend
export async function POST(req: NextRequest) {
  try {
    const { phone, body: msgBody } = await req.json() as {
      phone: string;
      body: string;
    };

    if (!phone || !msgBody) {
      return NextResponse.json({ error: 'phone e body são obrigatórios' }, { status: 400 });
    }

    // Normalizar phone (remover + se houver)
    const waId = phone.replace(/^\+/, '');

    // Buscar contato
    const [contact] = await waDb
      .select()
      .from(waContacts)
      .where(eq(waContacts.waId, waId))
      .limit(1);

    if (!contact) {
      return NextResponse.json({ error: 'Contato não encontrado' }, { status: 404 });
    }

    // Buscar conversa
    const [conv] = await waDb
      .select()
      .from(waConversations)
      .where(eq(waConversations.contactId, contact.id))
      .limit(1);

    if (!conv) {
      return NextResponse.json({ error: 'Conversa não encontrada' }, { status: 404 });
    }

    // Enviar via Meta API
    const metaResult = await sendTextMessage(waId, msgBody);
    if (!metaResult.success) {
      return NextResponse.json({ error: metaResult.error || 'Erro ao enviar' }, { status: 500 });
    }

    // Salvar no banco como mensagem do bot
    const [saved] = await waDb
      .insert(waMessages)
      .values({
        conversationId: conv.id,
        contactId: null,
        direction: 'outbound',
        type: 'text',
        body: msgBody,
        status: 'sent',
        sentBy: 'bot',
      })
      .returning();

    // Atualizar conversa
    await waDb
      .update(waConversations)
      .set({
        lastMessage: msgBody,
        lastMessageAt: new Date(),
        updatedAt: new Date(),
      })
      .where(eq(waConversations.id, conv.id));

    // Atualizar last_bot_msg_at na tabela CRM (usada pelo reengagement)
    try {
      await waDb.execute(
        sql`UPDATE contacts SET last_bot_msg_at = NOW() WHERE telefone = ${waId}`
      );
    } catch {
      // não bloqueia o fluxo se a tabela contacts não existir
    }

    // Emitir SSE para atualizar frontend em tempo real
    emitSSE({
      type: 'message',
      conversationId: conv.id,
      message: saved as Record<string, unknown>,
    });
    emitSSE({
      type: 'conversation-update',
      conversationId: conv.id,
      lastMessage: msgBody,
      lastMessageAt: new Date().toISOString(),
      unreadCount: 0,
    });

    return NextResponse.json({ ok: true, messageId: saved.id });
  } catch (err) {
    console.error('Erro no /api/whatsapp/bot-send:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
