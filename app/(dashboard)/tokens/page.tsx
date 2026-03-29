'use client';

import { useState, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, BarChart, Bar, ComposedChart, Area,
} from 'recharts';
import {
  Cpu, DollarSign, Zap, Activity, RefreshCw, TrendingUp, TrendingDown,
} from 'lucide-react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const PERIOD_OPTIONS = [
  { value: 7,  label: '7 dias'  },
  { value: 30, label: '30 dias' },
  { value: 90, label: '90 dias' },
];

// Paleta por workflow (auto-fallback para desconhecidos)
const WF_PALETTE = ['#6366f1', '#f59e0b', '#10b981', '#f43f5e', '#3b82f6'];
function wfColor(name: string, idx: number) {
  const map: Record<string, string> = {
    agent_n8n_agencia:        '#6366f1',
    'reengagement agent_n8n_agencia': '#f59e0b',
    calendar_agent_n8n_agencia: '#10b981',
  };
  return map[name] ?? WF_PALETTE[idx % WF_PALETTE.length];
}

function fmt(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtCost(usd: number) {
  if (usd === 0) return '$0';
  if (usd < 0.0001) return `$${(usd * 1_000_000).toFixed(1)}µ`;
  if (usd < 0.01)   return `$${usd.toFixed(5)}`;
  return `$${usd.toFixed(4)}`;
}

function fmtDate(s: string) {
  return new Date(s + 'T12:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function fmtDateTime(s: string) {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(s));
}

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-zinc-800/50 rounded-lg ${className}`} />;
}

function TrendBadge({ value }: { value: number | null }) {
  if (value === null) return null;
  const up = value >= 0;
  return (
    <span className={`flex items-center gap-0.5 text-[10px] font-medium ${up ? 'text-emerald-400' : 'text-red-400'}`}>
      {up ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
      {up ? '+' : ''}{value}%
    </span>
  );
}

function MetricCard({
  title, value, sub, icon, trend, loading,
}: {
  title: string; value: string; sub?: string;
  icon: React.ReactNode; trend?: number | null; loading?: boolean;
}) {
  if (loading) return <Skeleton className="h-28" />;
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-zinc-500">{title}</span>
        <span className="text-zinc-600">{icon}</span>
      </div>
      <p className="text-2xl font-bold text-zinc-100 tabular-nums">{value}</p>
      <div className="flex items-center gap-2 mt-1">
        {sub && <p className="text-[11px] text-zinc-500">{sub}</p>}
        <TrendBadge value={trend ?? null} />
      </div>
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const tooltipStyle: any = {
  contentStyle: { background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 },
  labelStyle: { color: '#e4e4e7', marginBottom: 4 },
};

type DailyRow = {
  day: string; totalTokens: number; promptTokens: number;
  completionTokens: number; estimatedCostUsd: number; executions: number;
};
type WfRow = { workflowName: string; totalTokens: number; estimatedCostUsd: number; executions: number };
type RecentRow = {
  executionId: string; workflowName: string; promptTokens: number;
  completionTokens: number; totalTokens: number; estimatedCostUsd: number; executedAt: string;
};

export default function TokensPage() {
  const [days, setDays] = useState(30);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');

  const { data, error, isLoading, mutate } = useSWR(
    `/api/tokens?days=${days}`,
    fetcher,
    { refreshInterval: 60_000 },
  );

  const handleSync = useCallback(async () => {
    setSyncing(true);
    setSyncMsg('');
    try {
      const res  = await fetch('/api/tokens/sync', { method: 'POST' });
      const json = await res.json();
      if (json.error) {
        setSyncMsg(`Erro: ${json.error}`);
      } else {
        setSyncMsg(`✓ ${json.inserted} novas · ${json.skipped} já salvas`);
        await mutate();
      }
    } catch {
      setSyncMsg('Erro ao conectar com n8n');
    } finally {
      setSyncing(false);
    }
  }, [mutate]);

  const s  = data?.summary;
  const td = data?.today;

  const daily: DailyRow[] = (data?.daily ?? []).map((d: DailyRow) => ({
    ...d,
    day:          fmtDate(d.day),
    costMilliUsd: +(d.estimatedCostUsd * 1000).toFixed(4), // em mili-dólar p/ escala legível
  }));

  const byWf: WfRow[] = data?.byWorkflow ?? [];

  return (
    <div className="p-4 md:p-6 space-y-5 max-w-[1200px] mx-auto">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">Tokens & Custo</h1>
          <p className="text-[11px] text-zinc-500 mt-0.5">
            agent_n8n_agencia · Gemini 2.5 Flash
          </p>
        </div>

        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-900 p-1">
              {PERIOD_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setDays(opt.value)}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                    days === opt.value ? 'bg-zinc-700 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} />
              {syncing ? 'Sincronizando...' : 'Sincronizar histórico'}
            </button>
          </div>
          {syncMsg && <p className="text-[10px] text-zinc-500">{syncMsg}</p>}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-900/40 bg-red-950/20 p-4 text-sm text-red-400">
          Erro ao carregar dados. Tente sincronizar primeiro.
        </div>
      )}

      {/* ── Métricas ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          title={`Tokens (${days}d)`}
          value={fmt(s?.totalTokens ?? 0)}
          sub={`${fmt(s?.promptTokens ?? 0)} in · ${fmt(s?.completionTokens ?? 0)} out`}
          icon={<Cpu size={16} />}
          trend={s?.trends?.tokens}
          loading={isLoading}
        />
        <MetricCard
          title={`Custo (${days}d)`}
          value={fmtCost(s?.estimatedCostUsd ?? 0)}
          sub={`Custo/exec: ${fmtCost((s?.estimatedCostUsd ?? 0) / Math.max(s?.executions ?? 1, 1))}`}
          icon={<DollarSign size={16} />}
          trend={s?.trends?.cost}
          loading={isLoading}
        />
        <MetricCard
          title="Execuções"
          value={String(s?.executions ?? 0)}
          sub={`Média: ${fmt(s?.avgTokensPerExecution ?? 0)} tok/exec`}
          icon={<Zap size={16} />}
          trend={s?.trends?.executions}
          loading={isLoading}
        />
        <MetricCard
          title="Hoje"
          value={fmt(td?.totalTokens ?? 0)}
          sub={`${td?.executions ?? 0} exec · ${fmtCost(td?.estimatedCostUsd ?? 0)}`}
          icon={<Activity size={16} />}
          loading={isLoading}
        />
      </div>

      {/* ── Tokens + Custo por dia (gráfico combinado) ── */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-zinc-300">Tokens vs Custo por dia</h2>
          <span className="text-[10px] text-zinc-600">custo em mili-USD (×0,001)</span>
        </div>
        {isLoading ? (
          <Skeleton className="h-56" />
        ) : daily.length === 0 ? (
          <div className="flex items-center justify-center h-56 text-xs text-zinc-600">
            Nenhum dado — clique em &ldquo;Sincronizar histórico&rdquo;
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={daily} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#71717a' }} tickLine={false} axisLine={false} />
              {/* Eixo esquerdo: tokens */}
              <YAxis
                yAxisId="tokens"
                tickFormatter={fmt}
                tick={{ fontSize: 11, fill: '#71717a' }}
                tickLine={false} axisLine={false} width={44}
              />
              {/* Eixo direito: custo em mili-USD */}
              <YAxis
                yAxisId="cost"
                orientation="right"
                tickFormatter={(v) => `$${v}m`}
                tick={{ fontSize: 11, fill: '#71717a' }}
                tickLine={false} axisLine={false} width={50}
              />
              <Tooltip
                {...tooltipStyle}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: unknown, name: unknown) => {
                  const val = typeof v === 'number' ? v : 0;
                  if (name === 'costMilliUsd') return [`$${val}m`, 'Custo (mUSD)'];
                  if (name === 'promptTokens')     return [fmt(val), 'Input'];
                  if (name === 'completionTokens') return [fmt(val), 'Output'];
                  return [fmt(val), String(name)];
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                }) as any}
              />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
              <Bar yAxisId="tokens" dataKey="promptTokens"     name="Input tokens"  fill="#6366f1" stackId="tk" radius={[0,0,0,0]} />
              <Bar yAxisId="tokens" dataKey="completionTokens" name="Output tokens" fill="#818cf8" stackId="tk" radius={[3,3,0,0]} />
              <Line yAxisId="cost"  dataKey="costMilliUsd"     name="Custo (mUSD)"
                stroke="#f59e0b" strokeWidth={2} dot={{ r: 3, fill: '#f59e0b' }} type="monotone" />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Por workflow ── */}
      {byWf.length > 0 && (
        <div className="grid md:grid-cols-2 gap-4">
          {/* Barras: tokens */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
            <h2 className="text-sm font-medium text-zinc-300 mb-4">Tokens por workflow</h2>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={byWf} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="workflowName" tick={{ fontSize: 10, fill: '#71717a' }}
                  tickFormatter={(v: string) => v.replace(' agent_n8n_agencia', '').replace('_agent_n8n_agencia', '')}
                  tickLine={false} axisLine={false} />
                <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: '#71717a' }} tickLine={false} axisLine={false} width={44} />
                <Tooltip
                  {...tooltipStyle}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={((v: unknown) => [fmt(typeof v === 'number' ? v : 0), 'Tokens']) as any}
                />
                {byWf.map((w, i) => (
                  <Bar key={w.workflowName} dataKey="totalTokens" name="Tokens"
                    fill={wfColor(w.workflowName, i)} radius={[4, 4, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Detalhes por workflow */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
            <h2 className="text-sm font-medium text-zinc-300 mb-4">Custo por workflow</h2>
            <div className="space-y-3">
              {byWf.map((w, i) => {
                const pct = s?.totalTokens ? Math.round((w.totalTokens / s.totalTokens) * 100) : 0;
                return (
                  <div key={w.workflowName} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full" style={{ background: wfColor(w.workflowName, i) }} />
                        <span className="text-zinc-400 truncate max-w-[160px]">{w.workflowName}</span>
                      </div>
                      <div className="flex items-center gap-3 text-zinc-500 shrink-0">
                        <span>{w.executions} exec</span>
                        <span className="text-zinc-300 font-medium tabular-nums">{fmt(w.totalTokens)}</span>
                        <span className="text-emerald-400 tabular-nums">{fmtCost(w.estimatedCostUsd)}</span>
                      </div>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-zinc-800">
                      <div
                        className="h-1.5 rounded-full transition-all"
                        style={{ width: `${pct}%`, background: wfColor(w.workflowName, i) }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Total */}
            <div className="mt-4 pt-3 border-t border-zinc-800 flex justify-between text-xs">
              <span className="text-zinc-500">Total acumulado ({days}d)</span>
              <div className="flex gap-4">
                <span className="text-zinc-300 font-medium">{fmt(s?.totalTokens ?? 0)} tokens</span>
                <span className="text-emerald-400 font-semibold">{fmtCost(s?.estimatedCostUsd ?? 0)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Execuções recentes ── */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <h2 className="text-sm font-medium text-zinc-300">Execuções recentes</h2>
        </div>
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-8" />)}
          </div>
        ) : (data?.recent?.length ?? 0) === 0 ? (
          <div className="py-12 text-center text-xs text-zinc-600">
            Nenhuma execução sincronizada ainda — clique em &ldquo;Sincronizar histórico&rdquo;
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500">
                  <th className="text-left px-4 py-2 font-medium">Workflow</th>
                  <th className="text-right px-4 py-2 font-medium">Input</th>
                  <th className="text-right px-4 py-2 font-medium">Output</th>
                  <th className="text-right px-4 py-2 font-medium">Total</th>
                  <th className="text-right px-4 py-2 font-medium">Custo</th>
                  <th className="text-right px-4 py-2 font-medium">Executado</th>
                </tr>
              </thead>
              <tbody>
                {(data.recent as RecentRow[]).map((r, i) => (
                  <tr key={r.executionId} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full flex-shrink-0"
                          style={{ background: wfColor(r.workflowName, i) }} />
                        <span className="text-zinc-400 truncate max-w-[180px]">{r.workflowName}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-right text-zinc-500 tabular-nums">{fmt(r.promptTokens)}</td>
                    <td className="px-4 py-2.5 text-right text-zinc-500 tabular-nums">{fmt(r.completionTokens)}</td>
                    <td className="px-4 py-2.5 text-right text-zinc-300 font-medium tabular-nums">{fmt(r.totalTokens)}</td>
                    <td className="px-4 py-2.5 text-right text-emerald-400/80 tabular-nums">{fmtCost(r.estimatedCostUsd)}</td>
                    <td className="px-4 py-2.5 text-right text-zinc-500">{fmtDateTime(r.executedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-[10px] text-zinc-700 text-center pb-2">
        Preços estimados: Gemini 2.5 Flash · $0,15/1M input · $0,60/1M output
      </p>
    </div>
  );
}
