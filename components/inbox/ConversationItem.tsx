'use client';

import Link from 'next/link';
import { Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeShort } from '@/lib/dateUtils';
import type { ConversationWithContact } from '@/lib/db/whatsapp-schema';

interface ConversationItemProps {
  conversation: ConversationWithContact;
  isActive?: boolean;
}

const AVATAR_COLORS = [
  'bg-indigo-600',
  'bg-purple-600',
  'bg-pink-600',
  'bg-emerald-600',
  'bg-amber-600',
  'bg-sky-600',
];

function getAvatarColor(str: string) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export function ConversationItem({
  conversation,
  isActive,
}: ConversationItemProps) {
  const name =
    conversation.contact.name || conversation.contact.waId || 'Desconhecido';
  const initials = name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase();
  const avatarColor = getAvatarColor(conversation.contact.id);

  const timeAgo = conversation.lastMessageAt
    ? formatRelativeShort(conversation.lastMessageAt)
    : null;

  return (
    <Link href={`/inbox/${conversation.id}`}>
      <div
        className={cn(
          'flex items-center gap-3 rounded-xl px-3 py-3 transition-colors cursor-pointer',
          isActive
            ? 'bg-zinc-800'
            : 'hover:bg-zinc-800/60'
        )}
      >
        {/* Avatar */}
        <div
          className={cn(
            'relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white',
            avatarColor
          )}
        >
          {initials}
          {/* Indicador online */}
          {conversation.unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full bg-indigo-500 ring-2 ring-zinc-900" />
          )}
        </div>

        {/* Conteúdo */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-1">
            <span
              className={cn(
                'truncate text-sm',
                conversation.unreadCount > 0
                  ? 'font-semibold text-zinc-100'
                  : 'font-medium text-zinc-300'
              )}
            >
              {name}
            </span>
            <span className="shrink-0 text-[10px] text-zinc-600">
              {timeAgo}
            </span>
          </div>

          <div className="flex items-center justify-between gap-1 mt-0.5">
            <span className="truncate text-xs text-zinc-500">
              {conversation.lastMessage || 'Sem mensagens'}
            </span>

            <div className="flex shrink-0 items-center gap-1">
              {!conversation.botActive && (
                <span title="Modo humano">
                  <Bot size={11} className="text-orange-400" />
                </span>
              )}
              {conversation.unreadCount > 0 && (
                <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-indigo-600 px-1 text-[10px] font-bold text-white">
                  {conversation.unreadCount > 99 ? '99+' : conversation.unreadCount}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
