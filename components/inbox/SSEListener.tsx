'use client';

import { useEffect, useRef, useCallback } from 'react';
import type { SSEEvent } from '@/lib/sse/emitter';

/**
 * Robust SSE hook with:
 * - Auto-reconnect with exponential backoff (capped at 30s)
 * - Polling fallback every 30s that refreshes conversations & messages
 * - Recovery of missed messages on reconnection
 */
export function useSSE(
  conversationId: string,
  onEvent: (event: SSEEvent) => void
) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const pollConversations = useCallback(async () => {
    if (conversationId !== 'all') return;
    try {
      const res = await fetch('/api/whatsapp/conversations');
      if (!res.ok) return;
      const convs = await res.json();
      // Emit synthetic conversation-update events for every conversation
      for (const c of convs) {
        onEventRef.current({
          type: 'conversation-update',
          conversationId: c.id,
          lastMessage: c.lastMessage ?? '',
          lastMessageAt: c.lastMessageAt ?? new Date().toISOString(),
          unreadCount: c.unreadCount ?? 0,
        });
      }
    } catch {
      // silently ignore poll errors
    }
  }, [conversationId]);

  const pollMessages = useCallback(async () => {
    if (conversationId === 'all') return;
    try {
      const res = await fetch(`/api/whatsapp/messages/${conversationId}`);
      if (!res.ok) return;
      const msgs = await res.json();
      // Emit each message; the ChatWindow deduplicates by id
      for (const msg of msgs) {
        onEventRef.current({
          type: 'message',
          conversationId,
          message: msg,
        });
      }
    } catch {
      // silently ignore poll errors
    }
  }, [conversationId]);

  useEffect(() => {
    if (!conversationId) return;

    let es: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout>;
    let pollInterval: ReturnType<typeof setInterval>;
    let retryCount = 0;
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      es = new EventSource(`/api/whatsapp/sse/${conversationId}`);

      es.onopen = () => {
        retryCount = 0; // reset backoff on successful connection
      };

      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data) as SSEEvent;
          onEventRef.current(event);
        } catch {
          // Ignore malformed data
        }
      };

      es.onerror = () => {
        es?.close();
        es = null;
        if (cancelled) return;

        // Exponential backoff capped at 30s
        const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
        retryCount++;
        retryTimeout = setTimeout(connect, delay);
      };
    }

    connect();

    // Polling fallback — refresh state every 30s in case SSE dropped events
    const poll = conversationId === 'all' ? pollConversations : pollMessages;
    pollInterval = setInterval(poll, 30000);

    // Also poll once on page visibility restore (tab regain focus)
    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        poll();
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      cancelled = true;
      clearTimeout(retryTimeout);
      clearInterval(pollInterval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      es?.close();
    };
  }, [conversationId, pollConversations, pollMessages]);
}
