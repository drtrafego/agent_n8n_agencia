'use client';

import { useState, useEffect, useCallback } from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { ConversationItem } from './ConversationItem';
import { useSSE } from './SSEListener';
import type { ConversationWithContact } from '@/lib/db/whatsapp-schema';
import type { SSEEvent } from '@/lib/sse/emitter';

interface ConversationListProps {
  initialConversations: ConversationWithContact[];
}

export function ConversationList({ initialConversations }: ConversationListProps) {
  const [conversations, setConversations] =
    useState<ConversationWithContact[]>(initialConversations);
  const [search, setSearch] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const pathname = usePathname();

  const refreshConversations = useCallback(async (silent = true) => {
    if (!silent) setRefreshing(true);
    try {
      const res = await fetch('/api/whatsapp/conversations');
      if (res.ok) {
        const data: ConversationWithContact[] = await res.json();
        setConversations(data);
      }
    } catch {
      // silencioso
    } finally {
      if (!silent) setRefreshing(false);
    }
  }, []);

  // Refresh automático a cada 30s para não depender só do SSE
  useEffect(() => {
    refreshConversations(true);
    const timer = setInterval(() => refreshConversations(true), 30_000);
    return () => clearInterval(timer);
  }, [refreshConversations]);

  const activeId = pathname.split('/inbox/')[1] || '';

  useSSE('all', (event: SSEEvent) => {
    if (event.type === 'conversation-update') {
      setConversations((prev) =>
        prev
          .map((c) =>
            c.id === event.conversationId
              ? {
                  ...c,
                  lastMessage: event.lastMessage,
                  lastMessageAt: new Date(event.lastMessageAt),
                  unreadCount: c.id === activeId ? 0 : event.unreadCount,
                }
              : c
          )
          .sort((a, b) => {
            const aTime = a.lastMessageAt ? new Date(a.lastMessageAt).getTime() : 0;
            const bTime = b.lastMessageAt ? new Date(b.lastMessageAt).getTime() : 0;
            return bTime - aTime;
          })
      );
    }

    if (event.type === 'bot-toggle') {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === event.conversationId ? { ...c, botActive: event.botActive } : c
        )
      );
    }
  });

  const filtered = conversations.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.contact.name?.toLowerCase().includes(q) ||
      c.contact.phone?.includes(q) ||
      c.lastMessage?.toLowerCase().includes(q)
    );
  });

  return (
    <aside className="flex w-full md:w-80 md:shrink-0 flex-col border-r border-zinc-800 bg-zinc-900">
      {/* Header */}
      <div className="border-b border-zinc-800 px-4 py-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-zinc-100">WhatsApp Inbox</h2>
          <button
            onClick={() => refreshConversations(false)}
            disabled={refreshing}
            className="flex items-center justify-center h-6 w-6 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors disabled:opacity-40"
            title="Atualizar conversas"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          </button>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar conversa..."
            className="w-full rounded-lg bg-zinc-800 py-2 pl-8 pr-3 text-xs text-zinc-300 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-600"
          />
        </div>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto p-2">
        {filtered.length === 0 ? (
          <p className="py-8 text-center text-xs text-zinc-600">
            {search ? 'Nenhuma conversa encontrada' : 'Nenhuma conversa ainda'}
          </p>
        ) : (
          filtered.map((conv) => (
            <ConversationItem
              key={conv.id}
              conversation={conv}
              isActive={conv.id === activeId}
            />
          ))
        )}
      </div>
    </aside>
  );
}
