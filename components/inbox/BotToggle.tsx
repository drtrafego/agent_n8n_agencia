'use client';

import { useState } from 'react';
import { Bot, User } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BotToggleProps {
  conversationId: string;
  initialBotActive: boolean;
  onToggle?: (botActive: boolean) => void;
}

export function BotToggle({
  conversationId,
  initialBotActive,
  onToggle,
}: BotToggleProps) {
  const [botActive, setBotActive] = useState(initialBotActive);
  const [loading, setLoading] = useState(false);

  async function handleToggle() {
    if (loading) return;
    setLoading(true);
    const newValue = !botActive;

    try {
      const res = await fetch('/api/whatsapp/bot-toggle', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversationId, botActive: newValue }),
      });

      if (res.ok) {
        setBotActive(newValue);
        onToggle?.(newValue);
      }
    } catch (err) {
      console.error('Erro ao alternar bot:', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleToggle}
        disabled={loading}
        className={cn(
          'flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-all',
          botActive
            ? 'bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30'
            : 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30',
          loading && 'opacity-50 cursor-not-allowed'
        )}
      >
        {botActive ? (
          <>
            <Bot size={14} />
            Bot ativo
          </>
        ) : (
          <>
            <User size={14} />
            Modo humano
          </>
        )}
      </button>

      {/* Switch visual */}
      <button
        onClick={handleToggle}
        disabled={loading}
        aria-label="Alternar bot"
        className={cn(
          'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
          botActive ? 'bg-indigo-600' : 'bg-orange-500',
          loading && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span
          className={cn(
            'inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform',
            botActive ? 'translate-x-5' : 'translate-x-1'
          )}
        />
      </button>
    </div>
  );
}
