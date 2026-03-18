'use client';

import { useState, useEffect, useRef } from 'react';
import { AlertTriangle } from 'lucide-react';
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

  // Marcar como lido ao abrir
  useEffect(() => {
    fetch('/api/whatsapp/read', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversationId: conversation.id }),
    }).catch(console.error);
  }, [conversation.id]);

  // Auto-scroll para o fim
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // SSE — escutar novas mensagens
  useSSE(conversation.id, (event: SSEEvent) => {
    if (event.type === 'message' && event.conversationId === conversation.id) {
      setMessages((prev) => {
        // Evitar duplicatas
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
    <div className="flex flex-col h-full">
      {/* Header do chat */}
      <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/50 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white">
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
      <MessageInput
        conversationId={conversation.id}
        disabled={false}
      />
    </div>
  );
}
