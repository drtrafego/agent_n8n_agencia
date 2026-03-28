'use client';

import { useState } from 'react';
import useSWR from 'swr';
import {
  Activity,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Send,
  Loader2,
  AlertTriangle,
} from 'lucide-react';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

type HealthCheck = { ok: boolean; detail: string };

type LogEntry = {
  id: string;
  payload: unknown;
  status: string;
  error_msg: string | null;
  created_at: string;
};

type LogsResponse = {
  health: {
    meta: HealthCheck;
    supabase: HealthCheck;
    n8n: HealthCheck;
  };
  logs: LogEntry[];
  fetchedAt: string;
  error?: string;
};

const TEST_PHONE = '5511999999999'; // hardcoded test number

function StatusBadge({ ok }: { ok: boolean }) {
  return ok ? (
    <CheckCircle2 size={16} className="text-emerald-400" />
  ) : (
    <XCircle size={16} className="text-red-400" />
  );
}

function HealthCard({
  label,
  check,
}: {
  label: string;
  check: HealthCheck | undefined;
}) {
  if (!check) return null;
  return (
    <div className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
      <StatusBadge ok={check.ok} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-zinc-200">{label}</p>
        <p className="truncate text-xs text-zinc-500">{check.detail}</p>
      </div>
    </div>
  );
}

export default function LogsPage() {
  const { data, error, isLoading, mutate } = useSWR<LogsResponse>(
    '/api/logs',
    fetcher,
    { refreshInterval: 10_000 }
  );

  const [testResult, setTestResult] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [expandedLog, setExpandedLog] = useState<string | null>(null);

  async function handleTestSend() {
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/logs/test-send', { method: 'POST' });
      const json = await res.json();
      if (res.ok) {
        setTestResult(`Success: message ID ${json.messageId ?? 'sent'}`);
      } else {
        setTestResult(`Error ${res.status}: ${json.error ?? 'unknown'}`);
      }
    } catch (err) {
      setTestResult(`Network error: ${String(err)}`);
    } finally {
      setTestLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={20} className="text-indigo-400" />
          <h1 className="text-lg font-semibold text-zinc-100">System Logs</h1>
        </div>
        <button
          onClick={() => mutate()}
          className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
        >
          <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Health checks */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
          Health Checks
        </h2>
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-300">
            <AlertTriangle size={14} />
            Failed to load health data
          </div>
        )}
        <div className="grid gap-2 sm:grid-cols-3">
          <HealthCard label="Meta API" check={data?.health?.meta} />
          <HealthCard label="Supabase DB" check={data?.health?.supabase} />
          <HealthCard label="n8n Webhook" check={data?.health?.n8n} />
        </div>
        {data?.fetchedAt && (
          <p className="text-[10px] text-zinc-600">
            Last check: {new Date(data.fetchedAt).toLocaleTimeString()} (auto-refresh 10s)
          </p>
        )}
      </section>

      {/* Test Send */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
          Test Send
        </h2>
        <div className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
          <div className="flex-1">
            <p className="text-sm text-zinc-300">
              Send a test message to <code className="text-xs text-indigo-400">{TEST_PHONE}</code>
            </p>
            {testResult && (
              <p
                className={`mt-1 text-xs ${
                  testResult.startsWith('Success') ? 'text-emerald-400' : 'text-red-400'
                }`}
              >
                {testResult}
              </p>
            )}
          </div>
          <button
            onClick={handleTestSend}
            disabled={testLoading}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
          >
            {testLoading ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Send size={12} />
            )}
            Test Send
          </button>
        </div>
      </section>

      {/* Webhook Logs */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
          Recent Webhook Events ({data?.logs?.length ?? 0})
        </h2>
        <div className="overflow-hidden rounded-lg border border-zinc-800">
          {isLoading && !data ? (
            <div className="flex items-center justify-center py-12 text-zinc-500">
              <Loader2 size={20} className="animate-spin" />
            </div>
          ) : !data?.logs?.length ? (
            <div className="py-12 text-center text-sm text-zinc-600">
              No webhook events found
            </div>
          ) : (
            <div className="max-h-[500px] overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-zinc-900 text-zinc-500">
                  <tr>
                    <th className="px-4 py-2 font-medium">Time</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium">Error</th>
                    <th className="px-4 py-2 font-medium">Payload</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/50">
                  {data.logs.map((log) => (
                    <tr
                      key={log.id}
                      className="transition-colors hover:bg-zinc-900/60"
                    >
                      <td className="whitespace-nowrap px-4 py-2 text-zinc-400">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
                            log.status === 'processed'
                              ? 'bg-emerald-950 text-emerald-400'
                              : log.status === 'error'
                              ? 'bg-red-950 text-red-400'
                              : 'bg-zinc-800 text-zinc-400'
                          }`}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td className="max-w-[200px] truncate px-4 py-2 text-red-400">
                        {log.error_msg || '-'}
                      </td>
                      <td className="px-4 py-2">
                        <button
                          onClick={() =>
                            setExpandedLog(expandedLog === log.id ? null : log.id)
                          }
                          className="text-indigo-400 hover:text-indigo-300"
                        >
                          {expandedLog === log.id ? 'hide' : 'view'}
                        </button>
                        {expandedLog === log.id && (
                          <pre className="mt-2 max-h-48 overflow-auto rounded bg-zinc-950 p-2 text-[10px] text-zinc-400">
                            {JSON.stringify(log.payload, null, 2)}
                          </pre>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
