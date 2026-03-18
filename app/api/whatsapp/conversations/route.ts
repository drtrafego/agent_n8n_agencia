import { NextRequest, NextResponse } from 'next/server';
import { desc, eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { conversations, contacts } from '@/lib/db/whatsapp-schema';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const status = searchParams.get('status') || 'open';

    const rows = await waDb
      .select({
        id: conversations.id,
        status: conversations.status,
        botActive: conversations.botActive,
        unreadCount: conversations.unreadCount,
        lastMessage: conversations.lastMessage,
        lastMessageAt: conversations.lastMessageAt,
        updatedAt: conversations.updatedAt,
        contact: {
          id: contacts.id,
          waId: contacts.waId,
          name: contacts.name,
          phone: contacts.phone,
          avatarUrl: contacts.avatarUrl,
        },
      })
      .from(conversations)
      .innerJoin(contacts, eq(conversations.contactId, contacts.id))
      .where(eq(conversations.status, status))
      .orderBy(desc(conversations.lastMessageAt));

    return NextResponse.json(rows);
  } catch (err) {
    console.error('Erro em /api/whatsapp/conversations:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
