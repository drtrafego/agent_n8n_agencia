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

    if (isNaN(contactId)) {
      return NextResponse.json({ error: 'ID invalido' }, { status: 400 });
    }

    // Get contact info
    const contact = await db.execute<{
      id: number;
      nome: string | null;
      telefone: string | null;
      email: string | null;
      nicho: string | null;
      observacoes_sdr: string | null;
      stage: string;
    }>(sql`
      SELECT id, nome, telefone, email, nicho, observacoes_sdr, stage
      FROM contacts
      WHERE id = ${contactId}
      LIMIT 1
    `);

    if (!contact.length) {
      return NextResponse.json({ error: 'Contato nao encontrado' }, { status: 404 });
    }

    // Get all messages through wa_contacts -> wa_conversations -> wa_messages
    const messages = await db.execute<{
      id: string;
      direction: string;
      body: string | null;
      sent_by: string | null;
      created_at: string;
      type: string;
    }>(sql`
      SELECT
        m.id,
        m.direction,
        m.body,
        m.sent_by,
        m.created_at,
        m.type
      FROM wa_messages m
      JOIN wa_conversations conv ON conv.id = m.conversation_id
      JOIN wa_contacts wc ON wc.id = conv.contact_id
      JOIN contacts c ON c.telefone = wc.phone
      WHERE c.id = ${contactId}
      ORDER BY m.created_at ASC
    `);

    return NextResponse.json({
      contact: contact[0],
      messages,
    });
  } catch (err) {
    console.error('Erro em GET /api/crm/lead/[id]:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
