import { notFound } from 'next/navigation';
import { eq, asc, desc } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import {
  conversations,
  contacts,
  messages,
} from '@/lib/db/whatsapp-schema';
import { ConversationList } from '@/components/inbox/ConversationList';
import { ChatWindow } from '@/components/inbox/ChatWindow';

async function getConversations() {
  try {
    return await waDb
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
  } catch {
    return [];
  }
}

export default async function ChatPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  // Buscar conversa + contato
  const [conv] = await waDb
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
    .where(eq(conversations.id, id))
    .limit(1);

  if (!conv) notFound();

  // Buscar últimas 100 mensagens
  const msgs = await waDb
    .select()
    .from(messages)
    .where(eq(messages.conversationId, id))
    .orderBy(asc(messages.createdAt))
    .limit(100);

  // Zerar unread count
  await waDb
    .update(conversations)
    .set({ unreadCount: 0 })
    .where(eq(conversations.id, id));

  const allConvs = await getConversations();

  return (
    <div className="flex h-[calc(100vh-57px)]">
      <ConversationList initialConversations={allConvs} />
      <div className="flex-1 overflow-hidden">
        <ChatWindow conversation={conv} initialMessages={msgs} />
      </div>
    </div>
  );
}
