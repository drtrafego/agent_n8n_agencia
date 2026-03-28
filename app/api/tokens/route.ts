import { NextRequest, NextResponse } from 'next/server';
import { waDb } from '@/lib/db/whatsapp';
import { sql } from 'drizzle-orm';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const days = Number(searchParams.get('days') || '30');

    // ── Totais do período ──────────────────────────────────────────
    const totals = await waDb.execute<{
      total_tokens: string;
      prompt_tokens: string;
      completion_tokens: string;
      estimated_cost: string;
      executions: string;
    }>(sql`
      SELECT
        COALESCE(SUM(total_tokens), 0)        AS total_tokens,
        COALESCE(SUM(prompt_tokens), 0)       AS prompt_tokens,
        COALESCE(SUM(completion_tokens), 0)   AS completion_tokens,
        COALESCE(SUM(estimated_cost_usd), 0)  AS estimated_cost,
        COUNT(*)                              AS executions
      FROM wa_token_usage_logs
      WHERE executed_at >= NOW() - make_interval(days => ${days})
    `);

    // ── Período anterior (para calcular tendência) ─────────────────
    const prevTotals = await waDb.execute<{
      total_tokens: string;
      estimated_cost: string;
      executions: string;
    }>(sql`
      SELECT
        COALESCE(SUM(total_tokens), 0)        AS total_tokens,
        COALESCE(SUM(estimated_cost_usd), 0)  AS estimated_cost,
        COUNT(*)                              AS executions
      FROM wa_token_usage_logs
      WHERE executed_at >= NOW() - make_interval(days => ${days * 2})
        AND executed_at <  NOW() - make_interval(days => ${days})
    `);

    // ── Hoje ───────────────────────────────────────────────────────
    const today = await waDb.execute<{
      total_tokens: string;
      estimated_cost: string;
      executions: string;
    }>(sql`
      SELECT
        COALESCE(SUM(total_tokens), 0)        AS total_tokens,
        COALESCE(SUM(estimated_cost_usd), 0)  AS estimated_cost,
        COUNT(*)                              AS executions
      FROM wa_token_usage_logs
      WHERE executed_at >= CURRENT_DATE AT TIME ZONE 'America/Sao_Paulo'
    `);

    // ── Por workflow ───────────────────────────────────────────────
    const byWorkflow = await waDb.execute<{
      workflow_name: string;
      total_tokens: string;
      estimated_cost: string;
      executions: string;
    }>(sql`
      SELECT
        workflow_name,
        COALESCE(SUM(total_tokens), 0)        AS total_tokens,
        COALESCE(SUM(estimated_cost_usd), 0)  AS estimated_cost,
        COUNT(*)                              AS executions
      FROM wa_token_usage_logs
      WHERE executed_at >= NOW() - make_interval(days => ${days})
      GROUP BY workflow_name
      ORDER BY SUM(total_tokens) DESC
    `);

    // ── Diário (últimos N dias) ────────────────────────────────────
    const daily = await waDb.execute<{
      day: string;
      total_tokens: string;
      prompt_tokens: string;
      completion_tokens: string;
      estimated_cost: string;
      executions: string;
    }>(sql`
      SELECT
        DATE(executed_at AT TIME ZONE 'America/Sao_Paulo') AS day,
        COALESCE(SUM(total_tokens), 0)        AS total_tokens,
        COALESCE(SUM(prompt_tokens), 0)       AS prompt_tokens,
        COALESCE(SUM(completion_tokens), 0)   AS completion_tokens,
        COALESCE(SUM(estimated_cost_usd), 0)  AS estimated_cost,
        COUNT(*)                              AS executions
      FROM wa_token_usage_logs
      WHERE executed_at >= NOW() - make_interval(days => ${days})
      GROUP BY DATE(executed_at AT TIME ZONE 'America/Sao_Paulo')
      ORDER BY day ASC
    `);

    // ── Execuções recentes ─────────────────────────────────────────
    const recent = await waDb.execute<{
      execution_id: string;
      workflow_name: string;
      total_tokens: string;
      prompt_tokens: string;
      completion_tokens: string;
      estimated_cost_usd: string;
      model: string;
      executed_at: string;
    }>(sql`
      SELECT execution_id, workflow_name, total_tokens,
             prompt_tokens, completion_tokens, estimated_cost_usd, model, executed_at
      FROM wa_token_usage_logs
      ORDER BY executed_at DESC
      LIMIT 20
    `);

    const t = totals.rows[0];
    const p = prevTotals.rows[0];
    const td = today.rows[0];

    const trend = (curr: number, prev: number) => {
      if (!prev) return null;
      return Math.round(((curr - prev) / prev) * 100);
    };

    const currTokens = Number(t.total_tokens);
    const prevTokens = Number(p.total_tokens);
    const currCost = Number(t.estimated_cost);
    const prevCost = Number(p.estimated_cost);
    const currExec = Number(t.executions);
    const prevExec = Number(p.executions);

    return NextResponse.json({
      summary: {
        totalTokens: currTokens,
        promptTokens: Number(t.prompt_tokens),
        completionTokens: Number(t.completion_tokens),
        estimatedCostUsd: currCost,
        executions: currExec,
        avgTokensPerExecution: currExec > 0 ? Math.round(currTokens / currExec) : 0,
        trends: {
          tokens: trend(currTokens, prevTokens),
          cost: trend(currCost, prevCost),
          executions: trend(currExec, prevExec),
        },
      },
      today: {
        totalTokens: Number(td.total_tokens),
        estimatedCostUsd: Number(td.estimated_cost),
        executions: Number(td.executions),
      },
      byWorkflow: byWorkflow.rows.map((r) => ({
        workflowName: r.workflow_name,
        totalTokens: Number(r.total_tokens),
        estimatedCostUsd: Number(r.estimated_cost),
        executions: Number(r.executions),
      })),
      daily: daily.rows.map((r) => ({
        day: r.day,
        totalTokens: Number(r.total_tokens),
        promptTokens: Number(r.prompt_tokens),
        completionTokens: Number(r.completion_tokens),
        estimatedCostUsd: Number(r.estimated_cost),
        executions: Number(r.executions),
      })),
      recent: recent.rows.map((r) => ({
        executionId: r.execution_id,
        workflowName: r.workflow_name,
        totalTokens: Number(r.total_tokens),
        promptTokens: Number(r.prompt_tokens),
        completionTokens: Number(r.completion_tokens),
        estimatedCostUsd: Number(r.estimated_cost_usd),
        model: r.model,
        executedAt: r.executed_at,
      })),
    });
  } catch (err) {
    console.error('Erro em /api/tokens:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
