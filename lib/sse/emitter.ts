import { EventEmitter } from 'events';

declare global {
  // eslint-disable-next-line no-var
  var sseEmitter: EventEmitter | undefined;
}

if (!global.sseEmitter) {
  global.sseEmitter = new EventEmitter();
  global.sseEmitter.setMaxListeners(100);
}

export const sseEmitter = global.sseEmitter;

export type SSEEvent =
  | {
      type: 'message';
      conversationId: string;
      message: Record<string, unknown>;
    }
  | {
      type: 'status';
      conversationId: string;
      messageId: string;
      status: string;
    }
  | {
      type: 'bot-toggle';
      conversationId: string;
      botActive: boolean;
    }
  | {
      type: 'conversation-update';
      conversationId: string;
      lastMessage: string;
      lastMessageAt: string;
      unreadCount: number;
    };

export function emitSSE(event: SSEEvent) {
  sseEmitter.emit('event', event);
}
