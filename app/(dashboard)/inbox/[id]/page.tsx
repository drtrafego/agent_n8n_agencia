import { notFound } from 'next/navigation';
import { eq, asc, desc } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import {
  waConversations,
  waContacts,
  waMessages,
} from '@/lib/db/whatsapp-schema';
import { ConversationList } from '@/components/inbox/ConversationList';
import { ChatWindow } from '@/components/inbox/ChatWindow';

async function getConversations() {
  try {
    return await waDb
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

  const [conv] = await waDb
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
    .where(eq(waConversations.id, id))
    .limit(1);

  if (!conv) notFound();

  const msgs = await waDb
    .select()
    .from(waMessages)
    .where(eq(waMessages.conversationId, id))
    .orderBy(asc(waMessages.createdAt))
    .limit(100);

  await waDb
    .update(waConversations)
    .set({ unreadCount: 0 })
    .where(eq(waConversations.id, id));

  const allConvs = await getConversations();

  return (
    <div className="flex h-[calc(100dvh-57px)] md:h-[calc(100vh-57px)]">
      {/* Lista — escondida no mobile quando estiver em uma conversa */}
      <div className="hidden md:flex md:w-80 md:shrink-0">
        <ConversationList initialConversations={allConvs} />
      </div>

      {/* Chat — tela toda no mobile */}
      <div className="flex flex-1 overflow-hidden">
        <ChatWindow conversation={conv} initialMessages={msgs} />
      </div>
    </div>
  );
}
