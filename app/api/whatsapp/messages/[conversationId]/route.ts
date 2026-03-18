import { NextRequest, NextResponse } from 'next/server';
import { eq, asc } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { messages } from '@/lib/db/whatsapp-schema';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ conversationId: string }> }
) {
  try {
    const { conversationId } = await params;

    const rows = await waDb
      .select()
      .from(messages)
      .where(eq(messages.conversationId, conversationId))
      .orderBy(asc(messages.createdAt))
      .limit(100);

    return NextResponse.json(rows);
  } catch (err) {
    console.error('Erro em /api/whatsapp/messages:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
