import { NextResponse } from 'next/server';
import { waDb } from '@/lib/db/whatsapp';
import { waTokenUsageLogs } from '@/lib/db/whatsapp-schema';
import { sql } from 'drizzle-orm';

const N8N_URL = process.env.N8N_API_URL || 'https://n8n.casaldotrafego.com';
const N8N_KEY = process.env.N8N_API_KEY || '';

// Workflows a monitorar
const WORKFLOWS = [
  { id: 'JmiydfZHpeU8tnic', name: 'agent_n8n_agencia' },
  { id: 'aBMaCWPodLaS8I6L', name: 'reengagement_agent' },
];

// Nós LLM do workflow principal
const LLM_NODES = ['OpenAI Chat Model1', 'OpenAI Chat Model2', 'OpenAI Chat Model3'];

// Preços Gemini 2.5 Flash (USD por token)
const COST_INPUT_PER_TOKEN = 0.15 / 1_000_000;
const COST_OUTPUT_PER_TOKEN = 0.60 / 1_000_000;

type N8nExecution = {
  id: string;
  workflowId: string;
  startedAt: string;
  status: string;
  data?: {
    resultData?: {
      runData?: Record<string, Array<{
        data?: {
          ai_languageModel?: Array<Array<{
            json?: {
              tokenUsage?: {
                promptTokens?: number;
                completionTokens?: number;
                totalTokens?: number;
              };
            };
          }>>;
        };
      }>>;
    };
  };
};

function extractTokens(execution: N8nExecution) {
  const runData = execution.data?.resultData?.runData || {};
  let promptTokens = 0;
  let completionTokens = 0;
  let model = 'gemini-2.5-flash';

  for (const nodeName of LLM_NODES) {
    const nodeRuns = runData[nodeName] || [];
    for (const run of nodeRuns) {
      const items = run.data?.ai_languageModel?.[0] || [];
      for (const item of items) {
        const usage = item.json?.tokenUsage;
        if (usage) {
          promptTokens += usage.promptTokens || 0;
          completionTokens += usage.completionTokens || 0;
        }
      }
    }
  }

  const totalTokens = promptTokens + completionTokens;
  const estimatedCostUsd =
    promptTokens * COST_INPUT_PER_TOKEN + completionTokens * COST_OUTPUT_PER_TOKEN;

  return { promptTokens, completionTokens, totalTokens, model, estimatedCostUsd };
}

async function fetchExecutions(workflowId: string): Promise<N8nExecution[]> {
  const url = `${N8N_URL}/api/v1/executions?workflowId=${workflowId}&status=success&includeData=true&limit=100`;
  const res = await fetch(url, {
    headers: { 'X-N8N-API-KEY': N8N_KEY },
    next: { revalidate: 0 },
  });
  if (!res.ok) return [];
  const json = await res.json();
  return json.data || [];
}

export async function POST() {
  try {
    let inserted = 0;
    let skipped = 0;

    for (const workflow of WORKFLOWS) {
      const executions = await fetchExecutions(workflow.id);

      for (const exec of executions) {
        // Pula se já foi sincronizado
        const existing = await waDb.execute(
          sql`SELECT id FROM wa_token_usage_logs WHERE execution_id = ${exec.id} LIMIT 1`
        );
        if (existing.rows.length > 0) { skipped++; continue; }

        const tokens = extractTokens(exec);
        if (tokens.totalTokens === 0) { skipped++; continue; }

        await waDb.insert(waTokenUsageLogs).values({
          executionId: exec.id,
          workflowId: workflow.id,
          workflowName: workflow.name,
          promptTokens: tokens.promptTokens,
          completionTokens: tokens.completionTokens,
          totalTokens: tokens.totalTokens,
          model: tokens.model,
          estimatedCostUsd: tokens.estimatedCostUsd,
          executedAt: new Date(exec.startedAt),
        });
        inserted++;
      }
    }

    return NextResponse.json({ ok: true, inserted, skipped });
  } catch (err) {
    console.error('Erro em /api/tokens/sync:', err);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}

export async function GET() {
  return POST();
}
