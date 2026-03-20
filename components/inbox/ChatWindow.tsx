'use client';

import { useState, useEffect, useRef } from 'react';
import { AlertTriangle, ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { BotToggle } from './BotToggle';
import { useSSE } from './SSEListener';
import type { Message, Conversation, Contact } from '@/lib/db/whatsapp-schema';
import type { SSEEvent } from '@/lib/sse/emitter';

interface ChatWindowProps {
  conversation: Conversation & { contact: Contact };
  initialMessages: Message[];
}

export function ChatWindow({ conversation, initialMessages }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [botActive, setBotActive] = useState(conversation.botActive);
  const bottomRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    fetch('/api/whatsapp/read', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversationId: conversation.id }),
    }).catch(console.error);
  }, [conversation.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useSSE(conversation.id, (event: SSEEvent) => {
    if (event.type === 'message' && event.conversationId === conversation.id) {
      setMessages((prev) => {
        const exists = prev.some((m) => m.id === (event.message as Message).id);
        if (exists) return prev;
        return [...prev, event.message as Message];
      });
    }

    if (event.type === 'bot-toggle' && event.conversationId === conversation.id) {
      setBotActive(event.botActive);
    }
  });

  return (
    <div className="flex flex-col h-full w-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/50 px-4 py-3">
        <div className="flex items-center gap-3">
          {/* Botão voltar — apenas mobile */}
          <button
            onClick={() => router.push('/inbox')}
            className="md:hidden flex items-center justify-center h-8 w-8 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
            aria-label="Voltar"
          >
            <ArrowLeft size={18} />
          </button>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white shrink-0">
            {(conversation.contact.name || conversation.contact.waId)[0].toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-100">
              {conversation.contact.name || conversation.contact.waId}
            </p>
            <p className="text-xs text-zinc-500">+{conversation.contact.phone}</p>
          </div>
        </div>
        <BotToggle
          conversationId={conversation.id}
          initialBotActive={botActive}
          onToggle={setBotActive}
        />
      </div>

      {/* Banner modo humano */}
      {!botActive && (
        <div className="flex items-center gap-2 bg-orange-500/10 border-b border-orange-500/20 px-4 py-2">
          <AlertTriangle size={14} className="text-orange-400" />
          <span className="text-xs text-orange-400">
            Atendimento humano ativo — bot pausado
          </span>
        </div>
      )}

      {/* Mensagens */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex flex-col gap-3">
          {messages.length === 0 && (
            <p className="text-center text-sm text-zinc-600 py-8">
              Nenhuma mensagem ainda
            </p>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <MessageInput conversationId={conversation.id} disabled={false} />
    </div>
  );
}
