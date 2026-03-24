import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db/drizzle';
import { sql } from 'drizzle-orm';

const VALID_STAGES = [
  'novo',
  'qualificando',
  'interesse',
  'agendado',
  'convertido',
  'sem_interesse',
] as const;

export async function GET() {
  try {
    const rows = await db.execute<{
      id: number;
      nome: string | null;
      telefone: string | null;
      email: string | null;
      nicho: string | null;
      observacoes_sdr: string | null;
      stage: string;
      stage_updated_at: string | null;
      created_at: string;
      wa_contact_name: string | null;
      wa_phone: string | null;
      last_message: string | null;
      last_message_at: string | null;
      message_count: string;
    }>(sql`
      SELECT
        c.id,
        c.nome,
        c.telefone,
        c.email,
        c.nicho,
        c.observacoes_sdr,
        COALESCE(c.stage, 'novo') as stage,
        c.stage_updated_at,
        c.created_at,
        wc.name as wa_contact_name,
        wc.phone as wa_phone,
        conv.last_message,
        conv.last_message_at,
        COALESCE(msg_count.total, 0) as message_count
      FROM contacts c
      LEFT JOIN wa_contacts wc ON wc.phone = c.telefone
      LEFT JOIN wa_conversations conv ON conv.contact_id = wc.id
      LEFT JOIN LATERAL (
        SELECT COUNT(*)::int as total
        FROM wa_messages m
        WHERE m.conversation_id = conv.id
      ) msg_count ON true
      ORDER BY c.created_at DESC
    `);

    // Group by stage
    type Row = (typeof rows)[number];
    const grouped: Record<string, Row[]> = {};
    for (const stage of VALID_STAGES) {
      grouped[stage] = [];
    }

    for (const row of rows) {
      const stage = VALID_STAGES.includes(row.stage as any) ? row.stage : 'novo';
      if (!grouped[stage]) grouped[stage] = [];
      grouped[stage].push(row);
    }

    return NextResponse.json(grouped);
  } catch (err) {
    console.error('Erro em GET /api/crm:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const body = await req.json();
    const { contactId, newStage } = body;

    if (!contactId || !newStage) {
      return NextResponse.json(
        { error: 'contactId e newStage sao obrigatorios' },
        { status: 400 }
      );
    }

    if (!VALID_STAGES.includes(newStage)) {
      return NextResponse.json(
        { error: 'Stage invalido' },
        { status: 400 }
      );
    }

    await db.execute(sql`
      UPDATE contacts
      SET stage = ${newStage},
          stage_updated_at = NOW(),
          updated_at = NOW()
      WHERE id = ${contactId}
    `);

    return NextResponse.json({ success: true });
  } catch (err) {
    console.error('Erro em PATCH /api/crm:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
