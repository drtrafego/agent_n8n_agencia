import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db/drizzle';
import { sql } from 'drizzle-orm';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const contactId = Number(id);
    if (isNaN(contactId)) return NextResponse.json({ error: 'ID invalido' }, { status: 400 });

    const contact = await db.execute<{
      id: number; nome: string | null; telefone: string | null; email: string | null;
      nicho: string | null; observacoes_sdr: string | null; stage: string;
      source: string | null; created_at: string; updated_at: string;
      followup_count: number; last_bot_msg_at: string | null; last_lead_msg_at: string | null;
    }>(sql`SELECT id, nome, telefone, email, nicho, observacoes_sdr, stage, source, created_at, updated_at, COALESCE(followup_count, 0)::int as followup_count, last_bot_msg_at, last_lead_msg_at FROM contacts WHERE id = ${contactId} LIMIT 1`);

    if (!contact.length) return NextResponse.json({ error: 'Contato nao encontrado' }, { status: 404 });

    const messages = await db.execute<{
      id: string; direction: string; body: string | null; sent_by: string | null; created_at: string; type: string;
    }>(sql`
      SELECT m.id, m.direction, m.body, m.sent_by, m.created_at, m.type
      FROM wa_messages m
      JOIN wa_conversations conv ON conv.id = m.conversation_id
      JOIN wa_contacts wc ON wc.id = conv.contact_id
      JOIN contacts c ON c.telefone = wc.phone
      WHERE c.id = ${contactId}
      ORDER BY m.created_at ASC
    `);

    return NextResponse.json({ contact: contact[0], messages });
  } catch (err) {
    console.error('Erro em GET /api/crm/lead/[id]:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const contactId = Number(id);
    if (isNaN(contactId)) return NextResponse.json({ error: 'ID invalido' }, { status: 400 });

    const body = await req.json();

    const followupCount = body.followup_count !== undefined ? Number(body.followup_count) : null;

    await db.execute(sql`
      UPDATE contacts SET
        nome = COALESCE(${body.nome ?? null}, nome),
        email = COALESCE(${body.email ?? null}, email),
        nicho = COALESCE(${body.nicho ?? null}, nicho),
        source = COALESCE(${body.source ?? null}, source),
        stage = COALESCE(${body.stage ?? null}, stage),
        followup_count = COALESCE(${followupCount}, followup_count),
        stage_updated_at = CASE WHEN ${body.stage ?? null} IS NOT NULL THEN NOW() ELSE stage_updated_at END,
        updated_at = NOW()
      WHERE id = ${contactId}
    `);

    return NextResponse.json({ success: true });
  } catch (err) {
    console.error('Erro em PATCH /api/crm/lead/[id]:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
