import { NextRequest, NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { waConversations, waMessages, waContacts } from '@/lib/db/whatsapp-schema';
import { emitSSE } from '@/lib/sse/emitter';
import {
  sendTextMessage,
  sendImageMessage,
  sendDocumentMessage,
} from '@/lib/meta/client';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      conversationId,
      type,
      body: msgBody,
      mediaUrl,
      filename,
      sentBy = 'human',
    } = body as {
      conversationId: string;
      type: 'text' | 'image' | 'document';
      body?: string;
      mediaUrl?: string;
      filename?: string;
      sentBy?: 'human' | 'bot';
    };

    // Buscar conversa + contato
    const [conv] = await waDb
      .select()
      .from(waConversations)
      .where(eq(waConversations.id, conversationId))
      .limit(1);

    if (!conv) {
      return NextResponse.json(
        { error: 'Conversa não encontrada' },
        { status: 404 }
      );
    }

    const [contact] = await waDb
      .select()
      .from(waContacts)
      .where(eq(waContacts.id, conv.contactId))
      .limit(1);

    if (!contact) {
      return NextResponse.json(
        { error: 'Contato não encontrado' },
        { status: 404 }
      );
    }

    // Enviar via Meta API
    let metaResult;
    if (type === 'text' && msgBody) {
      metaResult = await sendTextMessage(contact.waId, msgBody);
    } else if (type === 'image' && mediaUrl) {
      metaResult = await sendImageMessage(contact.waId, mediaUrl, msgBody);
    } else if (type === 'document' && mediaUrl && filename) {
      metaResult = await sendDocumentMessage(contact.waId, mediaUrl, filename);
    } else {
      return NextResponse.json(
        { error: 'Parâmetros inválidos' },
        { status: 400 }
      );
    }

    if (!metaResult.success) {
      return NextResponse.json(
        { error: metaResult.error || 'Erro ao enviar mensagem' },
        { status: 500 }
      );
    }

    // Salvar no banco
    const [saved] = await waDb
      .insert(waMessages)
      .values({
        conversationId: conv.id,
        contactId: null,
        direction: 'outbound',
        type,
        body: msgBody || null,
        mediaUrl: mediaUrl || null,
        mediaFilename: filename || null,
        status: 'sent',
        sentBy,
      })
      .returning();

    // Atualizar conversa
    await waDb
      .update(waConversations)
      .set({
        lastMessage: msgBody || '[mídia]',
        lastMessageAt: new Date(),
        updatedAt: new Date(),
      })
      .where(eq(waConversations.id, conv.id));

    // Emitir SSE — notificar tanto o chat aberto quanto a lista de conversas
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
      unreadCount: 0,
    });

    return NextResponse.json({ ok: true, message: saved });
  } catch (err) {
    console.error('Erro no /api/whatsapp/send:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
