import { NextRequest, NextResponse } from 'next/server';
import { eq, asc } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { waMessages } from '@/lib/db/whatsapp-schema';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ conversationId: string }> }
) {
  try {
    const { conversationId } = await params;

    const rows = await waDb
      .select()
      .from(waMessages)
      .where(eq(waMessages.conversationId, conversationId))
      .orderBy(asc(waMessages.createdAt))
      .limit(100);

    return NextResponse.json(rows);
  } catch (err) {
    console.error('Erro em /api/whatsapp/messages:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
