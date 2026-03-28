'use client';

import { useState, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, BarChart, Bar,
} from 'recharts';
import {
  Cpu, DollarSign, Zap, Activity, RefreshCw, TrendingUp, TrendingDown,
} from 'lucide-react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const PERIOD_OPTIONS = [
  { value: 7, label: '7 dias' },
  { value: 30, label: '30 dias' },
  { value: 90, label: '90 dias' },
];

function fmt(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtCost(usd: number) {
  if (usd < 0.001) return `$${(usd * 1000).toFixed(3)}m`;
  return `$${usd.toFixed(4)}`;
}

function fmtDate(dateStr: string) {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function fmtDateTime(dateStr: string) {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(dateStr));
}

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-zinc-800/50 rounded-lg ${className}`} />;
}

type TrendBadgeProps = { value: number | null };
function TrendBadge({ value }: TrendBadgeProps) {
  if (value === null) return null;
  const positive = value >= 0;
  return (
    <span className={`flex items-center gap-0.5 text-[10px] font-medium ${positive ? 'text-emerald-400' : 'text-red-400'}`}>
      {positive ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
      {positive ? '+' : ''}{value}%
    </span>
  );
}

type MetricCardProps = {
  title: string;
  value: string;
  sub?: string;
  icon: React.ReactNode;
  trend?: number | null;
  loading?: boolean;
};
function MetricCard({ title, value, sub, icon, trend, loading }: MetricCardProps) {
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

const WORKFLOW_COLORS: Record<string, string> = {
  agent_n8n_agencia: '#6366f1',
  reengagement_agent: '#f59e0b',
};

export default function TokensPage() {
  const [days, setDays] = useState(30);
  const [syncing, setSyncing] = useState(false);

  const { data, error, isLoading, mutate } = useSWR(
    `/api/tokens?days=${days}`,
    fetcher,
    { refreshInterval: 60_000 }
  );

  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      await fetch('/api/tokens/sync', { method: 'POST' });
      await mutate();
    } finally {
      setSyncing(false);
    }
  }, [mutate]);

  const s = data?.summary;
  const td = data?.today;

  const dailyChartData = (data?.daily || []).map((d: { day: string; totalTokens: number; promptTokens: number; completionTokens: number; estimatedCostUsd: number; executions: number }) => ({
    ...d,
    day: fmtDate(d.day),
  }));

  return (
    <div className="p-4 md:p-6 space-y-5 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">Tokens & Custo</h1>
          <p className="text-[11px] text-zinc-500 mt-0.5">Consumo do agente de IA (Gemini 2.5 Flash)</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Period selector */}
          <div className="flex items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-900 p-1">
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setDays(opt.value)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  days === opt.value
                    ? 'bg-zinc-700 text-zinc-100'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Sync button */}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors disabled:opacity-50"
            title="Sincronizar execuções do n8n"
          >
            <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Sincronizando...' : 'Sincronizar'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-900/40 bg-red-950/20 p-4 text-sm text-red-400">
          Erro ao carregar dados. Tente sincronizar primeiro.
        </div>
      )}

      {/* Metric Cards — Período */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          title={`Total tokens (${days}d)`}
          value={fmt(s?.totalTokens || 0)}
          sub={`${fmt(s?.promptTokens || 0)} in / ${fmt(s?.completionTokens || 0)} out`}
          icon={<Cpu size={16} />}
          trend={s?.trends?.tokens}
          loading={isLoading}
        />
        <MetricCard
          title={`Custo estimado (${days}d)`}
          value={fmtCost(s?.estimatedCostUsd || 0)}
          sub="Gemini 2.5 Flash"
          icon={<DollarSign size={16} />}
          trend={s?.trends?.cost}
          loading={isLoading}
        />
        <MetricCard
          title="Execuções"
          value={String(s?.executions || 0)}
          sub={`Média: ${fmt(s?.avgTokensPerExecution || 0)} tokens`}
          icon={<Zap size={16} />}
          trend={s?.trends?.executions}
          loading={isLoading}
        />
        <MetricCard
          title="Tokens hoje"
          value={fmt(td?.totalTokens || 0)}
          sub={`${td?.executions || 0} execuções · ${fmtCost(td?.estimatedCostUsd || 0)}`}
          icon={<Activity size={16} />}
          loading={isLoading}
        />
      </div>

      {/* Gráfico diário */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-medium text-zinc-300 mb-4">Tokens por dia</h2>
        {isLoading ? (
          <Skeleton className="h-52" />
        ) : dailyChartData.length === 0 ? (
          <div className="flex items-center justify-center h-52 text-xs text-zinc-600">
            Nenhum dado — clique em Sincronizar
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={dailyChartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#71717a' }} tickLine={false} axisLine={false} />
              <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: '#71717a' }} tickLine={false} axisLine={false} width={48} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#e4e4e7', marginBottom: 4 }}
                formatter={(v: number | string | undefined, name: string | number) => [fmt(typeof v === 'number' ? v : 0), name === 'promptTokens' ? 'Input' : name === 'completionTokens' ? 'Output' : 'Total']}
              />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
              <Line type="monotone" dataKey="promptTokens" name="Input" stroke="#6366f1" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="completionTokens" name="Output" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Por workflow */}
      {(data?.byWorkflow?.length || 0) > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-sm font-medium text-zinc-300 mb-4">Por workflow</h2>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={data.byWorkflow} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="workflowName" tick={{ fontSize: 11, fill: '#71717a' }} tickLine={false} axisLine={false} />
              <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: '#71717a' }} tickLine={false} axisLine={false} width={48} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
                formatter={(v: number) => [fmt(v), 'Tokens']}
              />
              <Bar dataKey="totalTokens" name="Tokens" radius={[4, 4, 0, 0]}
                fill="#6366f1"
              />
            </BarChart>
          </ResponsiveContainer>

          <div className="mt-3 space-y-2">
            {data.byWorkflow.map((w: { workflowName: string; totalTokens: number; executions: number; estimatedCostUsd: number }) => (
              <div key={w.workflowName} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full flex-shrink-0"
                    style={{ background: WORKFLOW_COLORS[w.workflowName] || '#71717a' }}
                  />
                  <span className="text-zinc-400">{w.workflowName}</span>
                </div>
                <div className="flex items-center gap-4 text-zinc-500">
                  <span>{w.executions} exec.</span>
                  <span className="text-zinc-300 font-medium tabular-nums">{fmt(w.totalTokens)} tokens</span>
                  <span className="text-emerald-400/70">{fmtCost(w.estimatedCostUsd)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabela de execuções recentes */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <h2 className="text-sm font-medium text-zinc-300">Execuções recentes</h2>
        </div>
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-8" />)}
          </div>
        ) : (data?.recent?.length || 0) === 0 ? (
          <div className="py-12 text-center text-xs text-zinc-600">
            Nenhuma execução sincronizada ainda — clique em Sincronizar
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
                  <th className="text-right px-4 py-2 font-medium">Executado em</th>
                </tr>
              </thead>
              <tbody>
                {data.recent.map((r: { executionId: string; workflowName: string; promptTokens: number; completionTokens: number; totalTokens: number; estimatedCostUsd: number; executedAt: string }) => (
                  <tr key={r.executionId} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="h-1.5 w-1.5 rounded-full flex-shrink-0"
                          style={{ background: WORKFLOW_COLORS[r.workflowName] || '#71717a' }}
                        />
                        <span className="text-zinc-400">{r.workflowName}</span>
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
