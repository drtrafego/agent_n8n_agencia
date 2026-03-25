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

function classifyStage(obs: string | null): string | null {
  if (!obs) return null;
  const o = obs.toLowerCase();
  if (o.includes('agendad') || o.includes('convite disparado') || o.includes('call agendada')) return 'agendado';
  if (o.includes('sem interesse')) return 'sem_interesse';
  if (o.includes('email') || o.includes('qualificand')) return 'interesse';
  if (o.length > 20) return 'qualificando';
  return null;
}

function classifyNicho(obs: string | null): string | null {
  if (!obs) return null;
  const o = obs.toLowerCase();
  if (/cl[ií]nica|odonto|dentist|sa[uú]de|fisio|m[eé]dic/.test(o)) return 'Saude';
  if (/imobili|im[oó]veis|corretor/.test(o)) return 'Imobiliaria';
  if (/ecommerce|eletr[oô]n|loja|varejo/.test(o)) return 'E-commerce';
  if (/advog|jur[ií]dic|direito/.test(o)) return 'Advocacia';
  if (/restaurante|delivery/.test(o)) return 'Alimentacao';
  if (/academia|crossfit|fitness/.test(o)) return 'Fitness';
  if (/seguro/.test(o)) return 'Seguros';
  if (/est[eé]tica|beleza|beauty/.test(o)) return 'Estetica';
  if (/contab|fiscal/.test(o)) return 'Contabilidade';
  if (/concession|ve[ií]culo/.test(o)) return 'Automotivo';
  if (/pet|banho|tosa/.test(o)) return 'Pet Shop';
  if (/arquitet/.test(o)) return 'Arquitetura';
  if (/viag|turismo|ag[eê]ncia de viag/.test(o)) return 'Turismo';
  if (/constru|material/.test(o)) return 'Construcao';
  return null;
}

export async function GET() {
  try {
    // Auto-classify contacts that are still 'novo' but have observacoes
    await db.execute(sql`
      UPDATE contacts SET
        stage = CASE
          WHEN observacoes_sdr ILIKE '%Status: agendado%' OR observacoes_sdr ILIKE '%convite disparado%' OR observacoes_sdr ILIKE '%call agendada%' THEN 'agendado'
          WHEN observacoes_sdr ILIKE '%Status: sem interesse%' OR observacoes_sdr ILIKE '%sem interesse%' THEN 'sem_interesse'
          WHEN observacoes_sdr ILIKE '%Status: interesse%' OR observacoes_sdr ILIKE '%pediu para agendar%' OR observacoes_sdr ILIKE '%escolheu hor%' THEN 'interesse'
          WHEN observacoes_sdr ILIKE '%Status: qualificando%' OR LENGTH(observacoes_sdr) > 20 THEN 'qualificando'
          ELSE stage
        END,
        nicho = CASE
          WHEN nicho IS NOT NULL THEN nicho
          WHEN observacoes_sdr ILIKE '%clinica%' OR observacoes_sdr ILIKE '%odonto%' OR observacoes_sdr ILIKE '%fisio%' OR observacoes_sdr ILIKE '%saude%' THEN 'Saude'
          WHEN observacoes_sdr ILIKE '%imobili%' THEN 'Imobiliaria'
          WHEN observacoes_sdr ILIKE '%ecommerce%' OR observacoes_sdr ILIKE '%loja%' THEN 'E-commerce'
          WHEN observacoes_sdr ILIKE '%advog%' THEN 'Advocacia'
          WHEN observacoes_sdr ILIKE '%restaurante%' OR observacoes_sdr ILIKE '%delivery%' THEN 'Alimentacao'
          WHEN observacoes_sdr ILIKE '%academia%' OR observacoes_sdr ILIKE '%crossfit%' THEN 'Fitness'
          WHEN observacoes_sdr ILIKE '%seguro%' THEN 'Seguros'
          WHEN observacoes_sdr ILIKE '%estetica%' OR observacoes_sdr ILIKE '%beleza%' THEN 'Estetica'
          WHEN observacoes_sdr ILIKE '%contab%' THEN 'Contabilidade'
          WHEN observacoes_sdr ILIKE '%concession%' THEN 'Automotivo'
          WHEN observacoes_sdr ILIKE '%pet%' OR observacoes_sdr ILIKE '%banho%' THEN 'Pet Shop'
          WHEN observacoes_sdr ILIKE '%arquitet%' THEN 'Arquitetura'
          WHEN observacoes_sdr ILIKE '%viag%' OR observacoes_sdr ILIKE '%turismo%' THEN 'Turismo'
          WHEN observacoes_sdr ILIKE '%constru%' OR observacoes_sdr ILIKE '%material%' THEN 'Construcao'
          ELSE nicho
        END,
        stage_updated_at = NOW()
      WHERE stage = 'novo' AND observacoes_sdr IS NOT NULL AND LENGTH(observacoes_sdr) > 10
    `);

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
      source: string | null;
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
        c.source,
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
