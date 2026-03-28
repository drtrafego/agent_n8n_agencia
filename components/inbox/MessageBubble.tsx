'use client';

import { Check, CheckCheck, FileText, Image as ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatTime } from '@/lib/dateUtils';
import type { Message } from '@/lib/db/whatsapp-schema';

interface MessageBubbleProps {
  message: Message;
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'sent') return <Check size={12} className="text-zinc-400" />;
  if (status === 'delivered')
    return <CheckCheck size={12} className="text-zinc-400" />;
  if (status === 'read')
    return <CheckCheck size={12} className="text-blue-400" />;
  return null;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isInbound = message.direction === 'inbound';
  const isBot = message.sentBy === 'bot';

  const bubbleClass = cn(
    'max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm',
    isInbound
      ? 'bg-zinc-800 text-zinc-100 rounded-bl-sm'
      : isBot
        ? 'bg-indigo-600 text-white rounded-br-sm'
        : 'bg-zinc-700 text-zinc-100 rounded-br-sm'
  );

  return (
    <div
      className={cn(
        'flex flex-col gap-0.5',
        isInbound ? 'items-start' : 'items-end'
      )}
    >
      {/* Label remetente (apenas outbound) */}
      {!isInbound && (
        <span className="text-[10px] text-zinc-500 px-1">
          {isBot ? '🤖 Bot' : '👤 Você'}
        </span>
      )}

      <div className={bubbleClass}>
        {/* Mídia */}
        {message.type === 'image' && message.mediaUrl && (
          <div className="mb-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={message.mediaUrl}
              alt="Imagem"
              className="rounded-lg max-h-60 w-auto"
            />
          </div>
        )}

        {message.type === 'document' && message.mediaUrl && (
          <a
            href={message.mediaUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 mb-2 text-current hover:opacity-80"
          >
            <FileText size={20} />
            <span className="text-xs underline">
              {message.mediaFilename || 'Documento'}
            </span>
          </a>
        )}

        {message.type === 'audio' && message.mediaUrl && (
          <audio controls className="mb-2 max-w-full" src={message.mediaUrl} />
        )}

        {/* Texto */}
        {message.body && (
          <p className="whitespace-pre-wrap break-words">{message.body}</p>
        )}

        {/* Placeholder para mídia sem texto */}
        {!message.body &&
          !['image', 'document', 'audio'].includes(message.type) && (
            <div className="flex items-center gap-2 text-zinc-400">
              <ImageIcon size={16} />
              <span className="text-xs">[mídia]</span>
            </div>
          )}
      </div>

      {/* Horário + status */}
      <div
        className={cn(
          'flex items-center gap-1 px-1',
          isInbound ? 'flex-row' : 'flex-row-reverse'
        )}
      >
        <span className="text-[10px] text-zinc-600">
          {formatTime(message.createdAt)}
        </span>
        {!isInbound && <StatusIcon status={message.status} />}
      </div>
    </div>
  );
}
