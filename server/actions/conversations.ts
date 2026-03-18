'use server';

import { eq, desc } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { conversations, contacts } from '@/lib/db/whatsapp-schema';

export async function getOpenConversations() {
  return waDb
    .select({
      id: conversations.id,
      contactId: conversations.contactId,
      status: conversations.status,
      botActive: conversations.botActive,
      unreadCount: conversations.unreadCount,
      lastMessage: conversations.lastMessage,
      lastMessageAt: conversations.lastMessageAt,
      createdAt: conversations.createdAt,
      updatedAt: conversations.updatedAt,
      contact: {
        id: contacts.id,
        waId: contacts.waId,
        name: contacts.name,
        phone: contacts.phone,
        avatarUrl: contacts.avatarUrl,
        createdAt: contacts.createdAt,
        updatedAt: contacts.updatedAt,
      },
    })
    .from(conversations)
    .innerJoin(contacts, eq(conversations.contactId, contacts.id))
    .where(eq(conversations.status, 'open'))
    .orderBy(desc(conversations.lastMessageAt));
}

export async function resolveConversation(conversationId: string) {
  return waDb
    .update(conversations)
    .set({ status: 'resolved', updatedAt: new Date() })
    .where(eq(conversations.id, conversationId));
}
