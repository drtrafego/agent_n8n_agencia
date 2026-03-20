import { desc, eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { waConversations, waContacts } from '@/lib/db/whatsapp-schema';
import { ConversationList } from '@/components/inbox/ConversationList';
import { MessageSquare } from 'lucide-react';

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

export default async function InboxPage() {
  const convs = await getConversations();

  return (
    <div className="flex h-[calc(100dvh-57px)] md:h-[calc(100vh-57px)]">
      {/* Mobile: lista ocupa tela toda. Desktop: w-80 fixo */}
      <ConversationList initialConversations={convs} />

      {/* Área vazia — só visível no desktop */}
      <div className="hidden md:flex flex-1 items-center justify-center bg-zinc-950">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/50">
            <MessageSquare size={28} className="text-zinc-500" />
          </div>
          <p className="text-sm font-medium text-zinc-400">Selecione uma conversa</p>
          <p className="mt-1 text-xs text-zinc-600">
            Escolha uma conversa na lista ao lado para começar
          </p>
        </div>
      </div>
    </div>
  );
}
