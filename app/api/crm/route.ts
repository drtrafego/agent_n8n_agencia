import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db/drizzle';
import { sql } from 'drizzle-orm';

const VALID_STAGES = [
  'novo',
  'qualificando',
  'interesse',
  'agendado',
  'realizada',
  'convertido',
  'sem_interesse',
] as const;

function classifyStage(obs: string | null): string | null {
  if (!obs) return null;
  const o = obs.toLowerCase();
  if (o.includes('realizada') || o.includes('reuniao realizada') || o.includes('reunião feita') || o.includes('call realizada')) return 'realizada';
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
    // IMPORTANTE: so reclassifica stage='novo' para nao interferir com stages manuais ou reengagement
    await db.execute(sql`
      UPDATE contacts SET
        stage = CASE
          WHEN observacoes_sdr ILIKE '%realizada%' OR observacoes_sdr ILIKE '%reuniao realizada%'
               OR observacoes_sdr ILIKE '%reunião feita%' OR observacoes_sdr ILIKE '%call realizada%'
               OR observacoes_sdr ILIKE '%reunião realizada%' OR observacoes_sdr ILIKE '%apresentacao feita%'
               OR observacoes_sdr ILIKE '%apresentação feita%'
            THEN 'realizada'
          WHEN observacoes_sdr ILIKE '%Status: agendado%'
               OR observacoes_sdr ILIKE '%convite disparado%' OR observacoes_sdr ILIKE '%call agendada%'
               OR observacoes_sdr ILIKE '%reuniao agendada%' OR observacoes_sdr ILIKE '%reunião agendada%'
               OR observacoes_sdr ILIKE '%agendou%'
               OR observacoes_sdr ILIKE '%confirmou%horario%' OR observacoes_sdr ILIKE '%confirmou%horário%'
            THEN 'agendado'
          WHEN observacoes_sdr ILIKE '%Status: sem interesse%' OR observacoes_sdr ILIKE '%sem interesse%'
               OR observacoes_sdr ILIKE '%nao quer%' OR observacoes_sdr ILIKE '%não quer%'
               OR observacoes_sdr ILIKE '%desistiu%' OR observacoes_sdr ILIKE '%recusou%'
            THEN 'sem_interesse'
          WHEN observacoes_sdr ILIKE '%Status: interesse%' OR observacoes_sdr ILIKE '%pediu para agendar%'
               OR observacoes_sdr ILIKE '%escolheu hor%' OR observacoes_sdr ILIKE '%quer saber mais%'
               OR observacoes_sdr ILIKE '%demonstrou interesse%' OR observacoes_sdr ILIKE '%quer agendar%'
               OR observacoes_sdr ILIKE '%interessado%' OR observacoes_sdr ILIKE '%interessada%'
               OR observacoes_sdr ILIKE '%pediu proposta%' OR observacoes_sdr ILIKE '%quer proposta%'
            THEN 'interesse'
          WHEN observacoes_sdr ILIKE '%Status: qualificando%' OR LENGTH(observacoes_sdr) > 20
            THEN 'qualificando'
          ELSE stage
        END,
        nicho = CASE
          WHEN nicho IS NOT NULL THEN nicho
          WHEN observacoes_sdr ILIKE '%clinica%' OR observacoes_sdr ILIKE '%clínica%' OR observacoes_sdr ILIKE '%odonto%' OR observacoes_sdr ILIKE '%fisio%' OR observacoes_sdr ILIKE '%saude%' OR observacoes_sdr ILIKE '%saúde%' OR observacoes_sdr ILIKE '%medic%' OR observacoes_sdr ILIKE '%médic%' OR observacoes_sdr ILIKE '%dentist%' THEN 'Saude'
          WHEN observacoes_sdr ILIKE '%imobili%' OR observacoes_sdr ILIKE '%imóve%' OR observacoes_sdr ILIKE '%corretor%' THEN 'Imobiliaria'
          WHEN observacoes_sdr ILIKE '%ecommerce%' OR observacoes_sdr ILIKE '%e-commerce%' OR observacoes_sdr ILIKE '%loja online%' OR observacoes_sdr ILIKE '%loja virtual%' OR observacoes_sdr ILIKE '%varejo%' THEN 'E-commerce'
          WHEN observacoes_sdr ILIKE '%advog%' OR observacoes_sdr ILIKE '%jurid%' OR observacoes_sdr ILIKE '%jurídic%' OR observacoes_sdr ILIKE '%direito%' THEN 'Advocacia'
          WHEN observacoes_sdr ILIKE '%restaurante%' OR observacoes_sdr ILIKE '%delivery%' OR observacoes_sdr ILIKE '%pizz%' OR observacoes_sdr ILIKE '%hamburgu%' THEN 'Alimentacao'
          WHEN observacoes_sdr ILIKE '%academia%' OR observacoes_sdr ILIKE '%crossfit%' OR observacoes_sdr ILIKE '%fitness%' OR observacoes_sdr ILIKE '%personal%' THEN 'Fitness'
          WHEN observacoes_sdr ILIKE '%seguro%' THEN 'Seguros'
          WHEN observacoes_sdr ILIKE '%estetica%' OR observacoes_sdr ILIKE '%estética%' OR observacoes_sdr ILIKE '%beleza%' OR observacoes_sdr ILIKE '%beauty%' OR observacoes_sdr ILIKE '%salao%' OR observacoes_sdr ILIKE '%salão%' THEN 'Estetica'
          WHEN observacoes_sdr ILIKE '%contab%' OR observacoes_sdr ILIKE '%fiscal%' THEN 'Contabilidade'
          WHEN observacoes_sdr ILIKE '%concession%' OR observacoes_sdr ILIKE '%veiculo%' OR observacoes_sdr ILIKE '%veículo%' OR observacoes_sdr ILIKE '%automotiv%' THEN 'Automotivo'
          WHEN observacoes_sdr ILIKE '%pet%' OR observacoes_sdr ILIKE '%banho%' OR observacoes_sdr ILIKE '%veterinar%' THEN 'Pet Shop'
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
      followup_count: number;
      last_bot_msg_at: string | null;
      last_lead_msg_at: string | null;
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
        COALESCE(msg_count.total, 0) as message_count,
        COALESCE(c.followup_count, 0)::int as followup_count,
        c.last_bot_msg_at,
        c.last_lead_msg_at
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
