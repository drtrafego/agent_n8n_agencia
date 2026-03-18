import { NextRequest, NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { conversations } from '@/lib/db/whatsapp-schema';
import { emitSSE } from '@/lib/sse/emitter';

export async function PATCH(req: NextRequest) {
  try {
    const { conversationId, botActive } = await req.json();

    if (!conversationId || typeof botActive !== 'boolean') {
      return NextResponse.json({ error: 'Parâmetros inválidos' }, { status: 400 });
    }

    await waDb
      .update(conversations)
      .set({ botActive, updatedAt: new Date() })
      .where(eq(conversations.id, conversationId));

    emitSSE({ type: 'bot-toggle', conversationId, botActive });

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('Erro no /api/whatsapp/bot-toggle:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
