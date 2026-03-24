import { NextResponse } from 'next/server';
import { db } from '@/lib/db/drizzle';
import { sql } from 'drizzle-orm';

export async function GET() {
  try {
    // 1. Total leads (contacts)
    const totalLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(*) as count FROM wa_contacts`
    );

    // 2. Leads that responded (have outbound bot messages)
    const respondedLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(DISTINCT c.id) as count
          FROM wa_contacts c
          JOIN wa_conversations conv ON conv.contact_id = c.id
          JOIN wa_messages m ON m.conversation_id = conv.id
          WHERE m.direction = 'outbound' AND m.sent_by = 'bot'`
    );

    // 3. Leads with scheduled calls (observacoes_sdr contains 'agendad')
    const scheduledLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(*) as count FROM contacts
          WHERE observacoes_sdr ILIKE '%agendad%'
             OR observacoes_sdr ILIKE '%call%'
             OR observacoes_sdr ILIKE '%reuniao%'`
    );

    // 4. Leads by status from contacts table
    const leadStatuses = await db.execute<{ status: string; count: string }>(
      sql`SELECT
            CASE
              WHEN observacoes_sdr ILIKE '%agendad%' OR observacoes_sdr ILIKE '%call agendada%' THEN 'agendado'
              WHEN observacoes_sdr ILIKE '%sem interesse%' OR observacoes_sdr ILIKE '%nao tem interesse%' THEN 'sem_interesse'
              ELSE 'qualificando'
            END as status,
            COUNT(*) as count
          FROM contacts
          GROUP BY status`
    );

    // 5. Messages per day (last 30 days)
    const dailyMessages = await db.execute<{ date: string; inbound: string; outbound: string }>(
      sql`SELECT
            DATE(created_at) as date,
            SUM(CASE WHEN direction = 'inbound' THEN 1 ELSE 0 END) as inbound,
            SUM(CASE WHEN direction = 'outbound' THEN 1 ELSE 0 END) as outbound
          FROM wa_messages
          WHERE created_at >= NOW() - INTERVAL '30 days'
          GROUP BY DATE(created_at)
          ORDER BY date ASC`
    );

    // 6. Leads per day (last 30 days)
    const dailyLeads = await db.execute<{ date: string; count: string }>(
      sql`SELECT DATE(created_at) as date, COUNT(*) as count
          FROM wa_contacts
          WHERE created_at >= NOW() - INTERVAL '30 days'
          GROUP BY DATE(created_at)
          ORDER BY date ASC`
    );

    // 7. Average response time (bot response time after human message)
    const avgResponseTime = await db.execute<{ avg_seconds: string }>(
      sql`SELECT COALESCE(AVG(response_time), 0) as avg_seconds FROM (
            SELECT EXTRACT(EPOCH FROM (
              (SELECT MIN(m2.created_at) FROM wa_messages m2
               WHERE m2.conversation_id = m.conversation_id
                 AND m2.direction = 'outbound'
                 AND m2.created_at > m.created_at)
              - m.created_at
            )) as response_time
            FROM wa_messages m
            WHERE m.direction = 'inbound'
              AND m.created_at >= NOW() - INTERVAL '30 days'
          ) sub
          WHERE response_time IS NOT NULL AND response_time > 0 AND response_time < 3600`
    );

    // 8. Total conversations and messages
    const totals = await db.execute<{ conversations: string; messages: string }>(
      sql`SELECT
            (SELECT COUNT(*) FROM wa_conversations) as conversations,
            (SELECT COUNT(*) FROM wa_messages) as messages`
    );

    // 9. Recent leads with last message
    const recentLeads = await db.execute<{
      name: string;
      phone: string;
      last_message: string;
      last_message_at: string;
      status: string;
      observacoes: string;
    }>(
      sql`SELECT
            COALESCE(ct.nome, wc.name, wc.wa_id) as name,
            COALESCE(wc.phone, wc.wa_id) as phone,
            conv.last_message,
            conv.last_message_at,
            CASE
              WHEN ct.observacoes_sdr ILIKE '%agendad%' OR ct.observacoes_sdr ILIKE '%call agendada%' THEN 'agendado'
              WHEN ct.observacoes_sdr ILIKE '%sem interesse%' THEN 'sem_interesse'
              WHEN ct.observacoes_sdr IS NOT NULL THEN 'qualificando'
              ELSE 'novo'
            END as status,
            COALESCE(ct.observacoes_sdr, '') as observacoes
          FROM wa_contacts wc
          JOIN wa_conversations conv ON conv.contact_id = wc.id
          LEFT JOIN contacts ct ON ct.telefone = wc.wa_id
          ORDER BY conv.last_message_at DESC NULLS LAST
          LIMIT 20`
    );

    // 10. Conversion funnel
    const totalContactsCount = Number(totalLeads[0]?.count || 0);
    const respondedCount = Number(respondedLeads[0]?.count || 0);

    // Interested = have more than 2 bot responses (beyond first greeting)
    const interestedLeads = await db.execute<{ count: string }>(
      sql`SELECT COUNT(DISTINCT conv.contact_id) as count
          FROM wa_conversations conv
          JOIN wa_messages m ON m.conversation_id = conv.id
          WHERE m.direction = 'inbound'
          GROUP BY conv.contact_id
          HAVING COUNT(*) >= 3`
    );
    const interestedCount = Number(interestedLeads[0]?.count || 0);
    const scheduledCount = Number(scheduledLeads[0]?.count || 0);

    return NextResponse.json({
      summary: {
        totalLeads: totalContactsCount,
        responded: respondedCount,
        interested: interestedCount,
        scheduled: scheduledCount,
        totalConversations: Number(totals[0]?.conversations || 0),
        totalMessages: Number(totals[0]?.messages || 0),
        avgResponseTimeSec: Math.round(Number(avgResponseTime[0]?.avg_seconds || 0)),
        conversionRate: totalContactsCount > 0
          ? Math.round((scheduledCount / totalContactsCount) * 100)
          : 0,
      },
      funnel: [
        { stage: 'Leads', value: totalContactsCount },
        { stage: 'Responderam', value: respondedCount },
        { stage: 'Interesse', value: interestedCount },
        { stage: 'Agendaram', value: scheduledCount },
      ],
      statusBreakdown: (leadStatuses || []).map((s) => ({
        status: s.status,
        count: Number(s.count),
      })),
      dailyMessages: (dailyMessages || []).map((d) => ({
        date: d.date,
        inbound: Number(d.inbound),
        outbound: Number(d.outbound),
      })),
      dailyLeads: (dailyLeads || []).map((d) => ({
        date: d.date,
        count: Number(d.count),
      })),
      recentLeads: recentLeads || [],
    });
  } catch (error) {
    console.error('Analytics error:', error);
    return NextResponse.json({ error: 'Failed to fetch analytics' }, { status: 500 });
  }
}
