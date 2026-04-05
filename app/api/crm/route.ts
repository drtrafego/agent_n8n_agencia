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

export async function GET() {
  try {
    // Auto-classify NICHO only (nicho extraction from observacoes_sdr)
    // STAGE e controlado exclusivamente pelo bot n8n (via postgresTool $fromAI)
    // e por drag-and-drop manual no CRM. Nao reclassificamos stage aqui
    // para evitar falsos positivos (ex: bot escreve "demonstrou interesse" em primeira interacao).
    await db.execute(sql`
      UPDATE contacts SET
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
        END
      WHERE nicho IS NULL AND observacoes_sdr IS NOT NULL AND LENGTH(observacoes_sdr) > 10
    `);

    // Leads com 6+ follow-ups sem resposta E sem mensagem do lead há 72h → sem_interesse
    // Regra conservadora: só descarta se realmente não houve nenhuma interação recente
    // Nao toca em leads que ja avancaram (interesse, agendado, realizada, convertido)
    await db.execute(sql`
      UPDATE contacts SET
        stage = 'sem_interesse',
        stage_updated_at = NOW()
      WHERE followup_count >= 6
        AND stage IN ('novo', 'qualificando')
        AND (last_lead_msg_at IS NULL OR last_lead_msg_at < NOW() - INTERVAL '72 hours')
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
      ad_id: string | null;
      ad_name: string | null;
      campaign_id: string | null;
      campaign_name: string | null;
      adset_id: string | null;
      adset_name: string | null;
      utm_source: string | null;
      utm_medium: string | null;
      utm_campaign: string | null;
      utm_content: string | null;
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
        c.ad_id,
        c.ad_name,
        c.campaign_id,
        c.campaign_name,
        c.adset_id,
        c.adset_name,
        c.utm_source,
        c.utm_medium,
        c.utm_campaign,
        c.utm_content,
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
