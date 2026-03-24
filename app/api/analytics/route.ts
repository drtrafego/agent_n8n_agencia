import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db/drizzle';
import { sql } from 'drizzle-orm';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const days = Number(searchParams.get('days') || '30');
    const statusFilter = searchParams.get('status') || 'all';

    // Use make_interval for safe parameterized interval
    const sinceDate = sql`NOW() - make_interval(days => ${days})`;
    const prevDate = sql`NOW() - make_interval(days => ${days * 2})`;

    // ============================================
    // 1. SUMMARY METRICS
    // ============================================
    const totalLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(*) as count FROM wa_contacts WHERE created_at >= ${sinceDate}`
    );

    const respondedLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(DISTINCT c.id) as count
          FROM wa_contacts c
          JOIN wa_conversations conv ON conv.contact_id = c.id
          JOIN wa_messages m ON m.conversation_id = conv.id
          WHERE m.direction = 'outbound' AND m.sent_by = 'bot'
            AND c.created_at >= ${sinceDate}`
    );

    const scheduledLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(*) as count FROM contacts
          WHERE (observacoes_sdr ILIKE '%agendad%' OR observacoes_sdr ILIKE '%call%' OR observacoes_sdr ILIKE '%convite disparado%')
            AND created_at >= ${sinceDate}`
    );

    const interestedLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(*) as count FROM (
            SELECT conv.contact_id
            FROM wa_conversations conv
            JOIN wa_messages m ON m.conversation_id = conv.id
            JOIN wa_contacts wc ON wc.id = conv.contact_id
            WHERE m.direction = 'inbound'
              AND wc.created_at >= ${sinceDate}
            GROUP BY conv.contact_id
            HAVING COUNT(*) >= 3
          ) sub`
    );

    // ============================================
    // 2. PREVIOUS PERIOD (for comparison)
    // ============================================
    const prevLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(*) as count FROM wa_contacts
          WHERE created_at >= ${prevDate}
            AND created_at < ${sinceDate}`
    );

    const prevScheduled = await db.execute<{ count: string }>(
      sql`SELECT COUNT(*) as count FROM contacts
          WHERE (observacoes_sdr ILIKE '%agendad%' OR observacoes_sdr ILIKE '%call%' OR observacoes_sdr ILIKE '%convite disparado%')
            AND created_at >= ${prevDate}
            AND created_at < ${sinceDate}`
    );

    // ============================================
    // 3. RESPONSE TIME METRICS
    // ============================================
    const responseTimeStats = await db.execute<{ avg_sec: string; min_sec: string; max_sec: string; p50_sec: string }>(
      sql`SELECT
            COALESCE(AVG(rt), 0)::int as avg_sec,
            COALESCE(MIN(rt), 0)::int as min_sec,
            COALESCE(MAX(rt), 0)::int as max_sec,
            COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rt), 0)::int as p50_sec
          FROM (
            SELECT EXTRACT(EPOCH FROM (
              (SELECT MIN(m2.created_at) FROM wa_messages m2
               WHERE m2.conversation_id = m.conversation_id
                 AND m2.direction = 'outbound' AND m2.created_at > m.created_at)
              - m.created_at
            )) as rt
            FROM wa_messages m
            WHERE m.direction = 'inbound' AND m.created_at >= ${sinceDate}
          ) sub WHERE rt > 0 AND rt < 3600`
    );

    // ============================================
    // 4. AVG MESSAGES TO SCHEDULE
    // ============================================
    const avgMsgsToSchedule = await db.execute<{ avg_msgs: string }>(
      sql`SELECT COALESCE(AVG(msg_count), 0)::int as avg_msgs FROM (
            SELECT COUNT(*) as msg_count
            FROM wa_messages m
            JOIN wa_conversations conv ON conv.id = m.conversation_id
            JOIN wa_contacts wc ON wc.id = conv.contact_id
            JOIN contacts ct ON ct.telefone = wc.wa_id
            WHERE ct.observacoes_sdr ILIKE '%agendad%' OR ct.observacoes_sdr ILIKE '%convite disparado%'
            GROUP BY conv.id
          ) sub`
    );

    // ============================================
    // 5. LEAD STATUS BREAKDOWN
    // ============================================
    const leadStatuses = await db.execute<{ status: string; count: string }>(
      sql`SELECT
            CASE
              WHEN observacoes_sdr ILIKE '%agendad%' OR observacoes_sdr ILIKE '%convite disparado%' THEN 'agendado'
              WHEN observacoes_sdr ILIKE '%sem interesse%' THEN 'sem_interesse'
              ELSE 'qualificando'
            END as status,
            COUNT(*) as count
          FROM contacts
          GROUP BY status`
    );

    // ============================================
    // 6. DAILY MESSAGES
    // ============================================
    const dailyMessages = await db.execute<{ date: string; inbound: string; outbound: string; total: string }>(
      sql`SELECT
            DATE(created_at) as date,
            SUM(CASE WHEN direction = 'inbound' THEN 1 ELSE 0 END) as inbound,
            SUM(CASE WHEN direction = 'outbound' THEN 1 ELSE 0 END) as outbound,
            COUNT(*) as total
          FROM wa_messages
          WHERE created_at >= ${sinceDate}
          GROUP BY DATE(created_at)
          ORDER BY date ASC`
    );

    // ============================================
    // 7. DAILY LEADS
    // ============================================
    const dailyLeads = await db.execute<{ date: string; count: string }>(
      sql`SELECT DATE(created_at) as date, COUNT(*) as count
          FROM wa_contacts
          WHERE created_at >= ${sinceDate}
          GROUP BY DATE(created_at)
          ORDER BY date ASC`
    );

    // ============================================
    // 8. HOURLY HEATMAP
    // ============================================
    const heatmapData = await db.execute<{ dow: string; hour: string; count: string }>(
      sql`SELECT
            EXTRACT(DOW FROM created_at)::int as dow,
            EXTRACT(HOUR FROM created_at)::int as hour,
            COUNT(*) as count
          FROM wa_messages
          WHERE direction = 'inbound'
            AND created_at >= ${sinceDate}
          GROUP BY dow, hour
          ORDER BY dow, hour`
    );

    // ============================================
    // 9. TOP NICHES
    // ============================================
    const nicheData = await db.execute<{ niche: string; count: string }>(
      sql`SELECT
            CASE
              WHEN observacoes_sdr ILIKE '%clinica%' OR observacoes_sdr ILIKE '%saude%' OR observacoes_sdr ILIKE '%medic%' OR observacoes_sdr ILIKE '%odonto%' OR observacoes_sdr ILIKE '%dentist%' THEN 'Saude/Clinica'
              WHEN observacoes_sdr ILIKE '%imobili%' OR observacoes_sdr ILIKE '%corretor%imov%' OR observacoes_sdr ILIKE '%imoveis%' THEN 'Imobiliaria'
              WHEN observacoes_sdr ILIKE '%ecommerce%' OR observacoes_sdr ILIKE '%loja%' OR observacoes_sdr ILIKE '%varejo%' OR observacoes_sdr ILIKE '%eletron%' THEN 'E-commerce'
              WHEN observacoes_sdr ILIKE '%advog%' OR observacoes_sdr ILIKE '%juridic%' THEN 'Advocacia'
              WHEN observacoes_sdr ILIKE '%restaurante%' OR observacoes_sdr ILIKE '%delivery%' THEN 'Alimentacao'
              WHEN observacoes_sdr ILIKE '%academia%' OR observacoes_sdr ILIKE '%crossfit%' OR observacoes_sdr ILIKE '%fitness%' THEN 'Fitness'
              WHEN observacoes_sdr ILIKE '%seguro%' THEN 'Seguros'
              WHEN observacoes_sdr ILIKE '%estetica%' OR observacoes_sdr ILIKE '%beleza%' OR observacoes_sdr ILIKE '%beauty%' THEN 'Estetica'
              WHEN observacoes_sdr ILIKE '%contab%' OR observacoes_sdr ILIKE '%fiscal%' THEN 'Contabilidade'
              WHEN observacoes_sdr ILIKE '%concession%' OR observacoes_sdr ILIKE '%veiculo%' THEN 'Automotivo'
              ELSE 'Outros'
            END as niche,
            COUNT(*) as count
          FROM contacts
          WHERE observacoes_sdr IS NOT NULL AND observacoes_sdr != ''
          GROUP BY niche
          ORDER BY count DESC`
    );

    // ============================================
    // 10. BEST DAY OF WEEK
    // ============================================
    const bestDayData = await db.execute<{ dow: string; count: string }>(
      sql`SELECT EXTRACT(DOW FROM created_at)::int as dow, COUNT(*) as count
          FROM wa_contacts
          WHERE created_at >= ${sinceDate}
          GROUP BY dow
          ORDER BY count DESC`
    );

    // ============================================
    // 11. RECENT LEADS
    // ============================================
    let statusWhere = sql`1=1`;
    if (statusFilter === 'agendado') statusWhere = sql`(ct.observacoes_sdr ILIKE '%agendad%' OR ct.observacoes_sdr ILIKE '%convite disparado%')`;
    else if (statusFilter === 'qualificando') statusWhere = sql`ct.observacoes_sdr IS NOT NULL AND ct.observacoes_sdr NOT ILIKE '%agendad%' AND ct.observacoes_sdr NOT ILIKE '%convite disparado%' AND ct.observacoes_sdr NOT ILIKE '%sem interesse%'`;
    else if (statusFilter === 'sem_interesse') statusWhere = sql`ct.observacoes_sdr ILIKE '%sem interesse%'`;
    else if (statusFilter === 'novo') statusWhere = sql`ct.observacoes_sdr IS NULL`;

    const recentLeads = await db.execute<{
      id: string; name: string; phone: string; last_message: string;
      last_message_at: string; status: string; observacoes: string;
      msg_count: string; first_contact: string; conversation_id: string;
    }>(
      sql`SELECT
            wc.id,
            COALESCE(ct.nome, wc.name, wc.wa_id) as name,
            COALESCE(wc.phone, wc.wa_id) as phone,
            conv.last_message,
            conv.last_message_at,
            CASE
              WHEN ct.observacoes_sdr ILIKE '%agendad%' OR ct.observacoes_sdr ILIKE '%convite disparado%' THEN 'agendado'
              WHEN ct.observacoes_sdr ILIKE '%sem interesse%' THEN 'sem_interesse'
              WHEN ct.observacoes_sdr IS NOT NULL THEN 'qualificando'
              ELSE 'novo'
            END as status,
            COALESCE(ct.observacoes_sdr, '') as observacoes,
            COALESCE((SELECT COUNT(*) FROM wa_messages m WHERE m.conversation_id = conv.id), 0) as msg_count,
            wc.created_at as first_contact,
            conv.id as conversation_id
          FROM wa_contacts wc
          JOIN wa_conversations conv ON conv.contact_id = wc.id
          LEFT JOIN contacts ct ON ct.telefone = wc.wa_id
          WHERE ${statusWhere}
          ORDER BY conv.last_message_at DESC NULLS LAST
          LIMIT 50`
    );

    // ============================================
    // COMPUTE RESULTS
    // ============================================
    const totalCount = Number(totalLeads[0]?.count || 0);
    const respondedCount = Number(respondedLeads[0]?.count || 0);
    const interestedCount = Number(interestedLeads[0]?.count || 0);
    const scheduledCount = Number(scheduledLeads[0]?.count || 0);
    const prevLeadCount = Number(prevLeads[0]?.count || 0);
    const prevScheduledCount = Number(prevScheduled[0]?.count || 0);

    const DOW_NAMES = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'];

    const heatmap = (heatmapData || []).map((row) => ({
      dow: DOW_NAMES[Number(row.dow)] || '?',
      hour: Number(row.hour),
      count: Number(row.count),
    }));

    const leadsTrend = prevLeadCount > 0 ? Math.round(((totalCount - prevLeadCount) / prevLeadCount) * 100) : 0;
    const scheduledTrend = prevScheduledCount > 0 ? Math.round(((scheduledCount - prevScheduledCount) / prevScheduledCount) * 100) : 0;

    const totalMsgs = await db.execute<{ c: string }>(
      sql`SELECT COUNT(*) as c FROM wa_messages WHERE created_at >= ${sinceDate}`
    );

    return NextResponse.json({
      period: { days, label: days === 7 ? '7 dias' : days === 30 ? '30 dias' : days === 90 ? '90 dias' : `${days}d` },
      summary: {
        totalLeads: totalCount,
        responded: respondedCount,
        interested: interestedCount,
        scheduled: scheduledCount,
        totalMessages: Number(totalMsgs[0]?.c || 0),
        avgResponseTimeSec: Number(responseTimeStats[0]?.avg_sec || 0),
        medianResponseTimeSec: Number(responseTimeStats[0]?.p50_sec || 0),
        avgMsgsToSchedule: Number(avgMsgsToSchedule[0]?.avg_msgs || 0),
        conversionRate: totalCount > 0 ? Math.round((scheduledCount / totalCount) * 100) : 0,
        responseRate: totalCount > 0 ? Math.round((respondedCount / totalCount) * 100) : 0,
      },
      trends: { leads: leadsTrend, scheduled: scheduledTrend },
      funnel: [
        { stage: 'Leads', value: totalCount, dropRate: 0 },
        { stage: 'Responderam', value: respondedCount, dropRate: totalCount > 0 ? Math.round(((totalCount - respondedCount) / totalCount) * 100) : 0 },
        { stage: 'Interesse', value: interestedCount, dropRate: respondedCount > 0 ? Math.round(((respondedCount - interestedCount) / respondedCount) * 100) : 0 },
        { stage: 'Agendaram', value: scheduledCount, dropRate: interestedCount > 0 ? Math.round(((interestedCount - scheduledCount) / interestedCount) * 100) : 0 },
      ],
      statusBreakdown: (leadStatuses || []).map((s) => ({ status: s.status, count: Number(s.count) })),
      niches: (nicheData || []).map((n) => ({ niche: n.niche, count: Number(n.count) })),
      dailyMessages: (dailyMessages || []).map((d) => ({ date: d.date, inbound: Number(d.inbound), outbound: Number(d.outbound), total: Number(d.total) })),
      dailyLeads: (dailyLeads || []).map((d) => ({ date: d.date, count: Number(d.count) })),
      heatmap,
      bestDay: bestDayData.length > 0 ? DOW_NAMES[Number(bestDayData[0].dow)] : '-',
      bestDayData: (bestDayData || []).map((d) => ({ day: DOW_NAMES[Number(d.dow)], count: Number(d.count) })),
      recentLeads: (recentLeads || []).map((l) => ({ ...l, msg_count: Number(l.msg_count) })),
    });
  } catch (error) {
    console.error('Analytics error:', error);
    return NextResponse.json({ error: 'Failed to fetch analytics', details: String(error) }, { status: 500 });
  }
}
