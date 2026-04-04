import { NextRequest } from 'next/server';
import { sseEmitter, type SSEEvent } from '@/lib/sse/emitter';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

// Tempo maximo de conexao SSE (5 minutos).
// Frontend reconecta automaticamente via useSSE hook (backoff exponencial).
// Isso evita que a funcao Vercel fique ativa indefinidamente consumindo CPU.
const SSE_MAX_DURATION_MS = 5 * 60 * 1000;

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ conversationId: string }> }
) {
  const { conversationId } = await params;
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    start(controller) {
      // Enviar heartbeat inicial
      controller.enqueue(encoder.encode(': heartbeat\n\n'));

      const send = (event: SSEEvent) => {
        // 'all' subscription receives every event; specific subscription
        // receives only its own conversation + broadcasts to 'all'
        const relevant =
          conversationId === 'all' ||
          event.conversationId === conversationId ||
          event.conversationId === 'all';
        if (!relevant) return;

        try {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(event)}\n\n`)
          );
        } catch {
          // Conexão fechada
        }
      };

      sseEmitter.on('event', send);

      // Heartbeat a cada 25s para manter conexão
      const heartbeat = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(': heartbeat\n\n'));
        } catch {
          clearInterval(heartbeat);
        }
      }, 25000);

      // Timeout: encerra a conexao apos SSE_MAX_DURATION_MS.
      // O frontend reconecta automaticamente (useSSE hook com backoff).
      const timeout = setTimeout(() => {
        cleanup();
      }, SSE_MAX_DURATION_MS);

      const cleanup = () => {
        clearInterval(heartbeat);
        clearTimeout(timeout);
        sseEmitter.off('event', send);
        try {
          controller.close();
        } catch {
          // Já fechado
        }
      };

      req.signal.addEventListener('abort', cleanup);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
