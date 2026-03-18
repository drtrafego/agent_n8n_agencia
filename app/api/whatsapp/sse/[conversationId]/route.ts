import { NextRequest } from 'next/server';
import { sseEmitter, type SSEEvent } from '@/lib/sse/emitter';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

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
        const relevant =
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

      req.signal.addEventListener('abort', () => {
        clearInterval(heartbeat);
        sseEmitter.off('event', send);
        try {
          controller.close();
        } catch {
          // Já fechado
        }
      });
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
