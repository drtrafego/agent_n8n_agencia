import { NextRequest, NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { conversations, messages, contacts } from '@/lib/db/whatsapp-schema';
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
      .from(conversations)
      .where(eq(conversations.id, conversationId))
      .limit(1);

    if (!conv) {
      return NextResponse.json(
        { error: 'Conversa não encontrada' },
        { status: 404 }
      );
    }

    const [contact] = await waDb
      .select()
      .from(contacts)
      .where(eq(contacts.id, conv.contactId))
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
      .insert(messages)
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
      .update(conversations)
      .set({
        lastMessage: msgBody || '[mídia]',
        lastMessageAt: new Date(),
        updatedAt: new Date(),
      })
      .where(eq(conversations.id, conv.id));

    // Emitir SSE
    emitSSE({
      type: 'message',
      conversationId: conv.id,
      message: saved as Record<string, unknown>,
    });

    return NextResponse.json({ ok: true, message: saved });
  } catch (err) {
    console.error('Erro no /api/whatsapp/send:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
