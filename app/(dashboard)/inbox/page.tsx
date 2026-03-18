import { desc, eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { conversations, contacts } from '@/lib/db/whatsapp-schema';
import { ConversationList } from '@/components/inbox/ConversationList';
import { MessageSquare } from 'lucide-react';

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

export default async function InboxPage() {
  const convs = await getConversations();

  return (
    <div className="flex h-[calc(100vh-57px)]">
      <ConversationList initialConversations={convs} />

      {/* Área vazia — selecione uma conversa */}
      <div className="flex flex-1 items-center justify-center bg-zinc-950">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/50">
            <MessageSquare size={28} className="text-zinc-500" />
          </div>
          <p className="text-sm font-medium text-zinc-400">
            Selecione uma conversa
          </p>
          <p className="mt-1 text-xs text-zinc-600">
            Escolha uma conversa na lista ao lado para começar
          </p>
        </div>
      </div>
    </div>
  );
}
