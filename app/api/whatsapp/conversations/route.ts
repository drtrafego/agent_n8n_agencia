import { NextRequest, NextResponse } from 'next/server';
import { desc, eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { waConversations, waContacts } from '@/lib/db/whatsapp-schema';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const status = searchParams.get('status') || 'open';

    const rows = await waDb
      .select({
        id: waConversations.id,
        contactId: waConversations.contactId,
        status: waConversations.status,
        botActive: waConversations.botActive,
        unreadCount: waConversations.unreadCount,
        lastMessage: waConversations.lastMessage,
        lastMessageAt: waConversations.lastMessageAt,
        createdAt: waConversations.createdAt,
        updatedAt: waConversations.updatedAt,
        contact: {
          id: waContacts.id,
          waId: waContacts.waId,
          name: waContacts.name,
          phone: waContacts.phone,
          avatarUrl: waContacts.avatarUrl,
          createdAt: waContacts.createdAt,
          updatedAt: waContacts.updatedAt,
        },
      })
      .from(waConversations)
      .innerJoin(waContacts, eq(waConversations.contactId, waContacts.id))
      .where(eq(waConversations.status, status))
      .orderBy(desc(waConversations.lastMessageAt));

    return NextResponse.json(rows);
  } catch (err) {
    console.error('Erro em /api/whatsapp/conversations:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
