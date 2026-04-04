import { NextResponse } from 'next/server';
import { waDb } from '@/lib/db/whatsapp';
import { waTokenUsageLogs } from '@/lib/db/whatsapp-schema';
import { sql } from 'drizzle-orm';

const N8N_URL = process.env.N8N_API_URL || 'https://n8n.casaldotrafego.com';
const N8N_KEY = process.env.N8N_API_KEY || '';
const WORKFLOW_PATTERN = 'agent_n8n_agencia'; // auto-descobre qualquer workflow com esse nome

// Preços Gemini 2.5 Flash (USD por token)
const COST_INPUT  = 0.15 / 1_000_000;
const COST_OUTPUT = 0.60 / 1_000_000;

const headers = { 'X-N8N-API-KEY': N8N_KEY };

// ── Tipos ────────────────────────────────────────────────────────────────────

type N8nWorkflow = { id: string; name: string; active: boolean };

type LLMItem = { json?: { tokenUsage?: { promptTokens?: number; completionTokens?: number } } };
type NodeRun  = { data?: { ai_languageModel?: LLMItem[][] } };
type RunData  = Record<string, NodeRun[]>;

type N8nExecution = {
  id: number;
  startedAt: string;
  status: string;
  data?: { resultData?: { runData?: RunData } };
};

// ── Helpers ──────────────────────────────────────────────────────────────────

async function n8nGet(path: string) {
  const res = await fetch(`${N8N_URL}${path}`, { headers, cache: 'no-store' });
  if (!res.ok) throw new Error(`n8n ${path} → ${res.status}`);
  return res.json();
}

/** Busca todos os workflows que contêm WORKFLOW_PATTERN no nome */
async function discoverWorkflows(): Promise<N8nWorkflow[]> {
  const json = await n8nGet('/api/v1/workflows?limit=100');
  return (json.data as N8nWorkflow[]).filter((w) =>
    w.name.toLowerCase().includes(WORKFLOW_PATTERN)
  );
}

/** Busca execuções bem-sucedidas de um workflow (com paginação).
 *  Se lastSyncDate fornecido, busca somente execuções posteriores.
 *  Limita a 500 execuções por workflow para evitar timeout. */
async function fetchAllExecutions(workflowId: string, lastSyncDate?: string | null): Promise<N8nExecution[]> {
  const all: N8nExecution[] = [];
  let cursor: string | null = null;
  const MAX_EXECUTIONS = 500;

  do {
    const qs = new URLSearchParams({
      workflowId,
      status: 'success',
      includeData: 'true',
      limit: '100',
      ...(cursor ? { cursor } : {}),
    });
    const json = await n8nGet(`/api/v1/executions?${qs}`);
    const batch = json.data as N8nExecution[];

    for (const exec of batch) {
      // Se temos data de ultimo sync, pula execuções já processadas
      if (lastSyncDate && new Date(exec.startedAt) <= new Date(lastSyncDate)) {
        // Execuções vem em ordem decrescente; se encontrou uma antiga, para
        return all;
      }
      all.push(exec);
    }

    cursor = json.nextCursor ?? null;
  } while (cursor && all.length < MAX_EXECUTIONS);

  return all;
}

/** Extrai tokens de QUALQUER nó LLM da execução (auto-detecção) */
function extractTokens(execution: N8nExecution) {
  const runData: RunData = execution.data?.resultData?.runData ?? {};
  let promptTokens = 0;
  let completionTokens = 0;

  for (const runs of Object.values(runData)) {
    for (const run of runs) {
      const items = run.data?.ai_languageModel?.[0] ?? [];
      for (const item of items) {
        promptTokens    += item.json?.tokenUsage?.promptTokens    ?? 0;
        completionTokens += item.json?.tokenUsage?.completionTokens ?? 0;
      }
    }
  }

  return {
    promptTokens,
    completionTokens,
    totalTokens: promptTokens + completionTokens,
    estimatedCostUsd: promptTokens * COST_INPUT + completionTokens * COST_OUTPUT,
  };
}

// ── Handler ──────────────────────────────────────────────────────────────────

/** Busca a data da execução mais recente já salva para evitar reprocessar tudo */
async function getLastSyncDate(): Promise<string | null> {
  try {
    const rows = await waDb.execute<{ newest: string | null }>(
      sql`SELECT MAX(executed_at) as newest FROM wa_token_usage_logs`
    );
    return (rows as unknown as { newest: string | null }[])[0]?.newest ?? null;
  } catch {
    return null;
  }
}

export async function POST() {
  try {
    const workflows = await discoverWorkflows();
    const lastSync = await getLastSyncDate();
    let inserted = 0;
    let skipped  = 0;

    for (const wf of workflows) {
      const executions = await fetchAllExecutions(wf.id, lastSync);

      for (const exec of executions) {
        const tokens = extractTokens(exec);
        if (tokens.totalTokens === 0) { skipped++; continue; }

        // ON CONFLICT DO NOTHING evita duplicatas sem pre-query
        const result = await waDb
          .insert(waTokenUsageLogs)
          .values({
            executionId:     String(exec.id),
            workflowId:      wf.id,
            workflowName:    wf.name,
            promptTokens:    tokens.promptTokens,
            completionTokens: tokens.completionTokens,
            totalTokens:     tokens.totalTokens,
            model:           'gemini-2.5-flash',
            estimatedCostUsd: tokens.estimatedCostUsd,
            executedAt:      new Date(exec.startedAt),
          })
          .onConflictDoNothing()
          .returning({ id: waTokenUsageLogs.id });

        result.length > 0 ? inserted++ : skipped++;
      }
    }

    return NextResponse.json({
      ok: true,
      workflows: workflows.map((w) => w.name),
      inserted,
      skipped,
      since: lastSync,
    });
  } catch (err) {
    console.error('Erro em /api/tokens/sync:', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

export const GET = POST;
