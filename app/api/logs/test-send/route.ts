import { NextResponse } from 'next/server';
import { sendTextMessage } from '@/lib/meta/client';

const TEST_PHONE = '5511999999999';

export async function POST() {
  try {
    const result = await sendTextMessage(
      TEST_PHONE,
      `[TEST] Mensagem de teste do sistema - ${new Date().toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })}`
    );

    if (!result.success) {
      return NextResponse.json(
        { error: result.error || 'Meta API error' },
        { status: 502 }
      );
    }

    const data = result.data as { messages?: { id: string }[] } | undefined;
    const messageId = data?.messages?.[0]?.id ?? null;

    return NextResponse.json({ ok: true, messageId });
  } catch (err) {
    console.error('/api/logs/test-send error:', err);
    return NextResponse.json(
      { error: String(err) },
      { status: 500 }
    );
  }
}
