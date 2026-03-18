'use server';

import { eq, desc } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { waConversations, waContacts } from '@/lib/db/whatsapp-schema';

export async function getOpenConversations() {
  return waDb
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
    .where(eq(waConversations.status, 'open'))
    .orderBy(desc(waConversations.lastMessageAt));
}

export async function resolveConversation(conversationId: string) {
  return waDb
    .update(waConversations)
    .set({ status: 'resolved', updatedAt: new Date() })
    .where(eq(waConversations.id, conversationId));
}
