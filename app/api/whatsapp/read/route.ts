import { NextRequest, NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { waConversations, waMessages } from '@/lib/db/whatsapp-schema';
import { markAsRead } from '@/lib/meta/client';

export async function PATCH(req: NextRequest) {
  try {
    const { conversationId } = await req.json();

    if (!conversationId) {
      return NextResponse.json({ error: 'conversationId obrigatório' }, { status: 400 });
    }

    // Zerar unread count
    await waDb
      .update(waConversations)
      .set({ unreadCount: 0, updatedAt: new Date() })
      .where(eq(waConversations.id, conversationId));

    // Marcar última mensagem inbound como lida na Meta
    const [lastInbound] = await waDb
      .select({ waMessageId: waMessages.waMessageId })
      .from(waMessages)
      .where(eq(waMessages.conversationId, conversationId))
      .orderBy(waMessages.createdAt)
      .limit(1);

    if (lastInbound?.waMessageId) {
      markAsRead(lastInbound.waMessageId).catch(console.error);
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('Erro no /api/whatsapp/read:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
