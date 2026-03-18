'use client';

import { useEffect, useRef } from 'react';
import type { SSEEvent } from '@/lib/sse/emitter';

export function useSSE(
  conversationId: string,
  onEvent: (event: SSEEvent) => void
) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!conversationId) return;

    let es: EventSource;
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      es = new EventSource(
        `/api/whatsapp/sse/${conversationId}`
      );

      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data) as SSEEvent;
          onEventRef.current(event);
        } catch {
          // Ignorar dados malformados
        }
      };

      es.onerror = () => {
        es.close();
        // Reconectar após 3s
        retryTimeout = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      clearTimeout(retryTimeout);
      es?.close();
    };
  }, [conversationId]);
}
