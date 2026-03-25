'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MetricCard } from '@/components/analytics/metric-card';
import { FunnelChart } from '@/components/analytics/funnel-chart';
import { DailyChart } from '@/components/analytics/daily-chart';
import { StatusChart } from '@/components/analytics/status-chart';
import { HeatmapChart } from '@/components/analytics/heatmap-chart';
import { NicheChart } from '@/components/analytics/niche-chart';
import { SourceChart } from '@/components/analytics/source-chart';
import { LeadsTable } from '@/components/analytics/leads-table';
import {
  Users, MessageSquare, CalendarCheck, Clock, TrendingUp, Percent,
  Zap, BarChart3, Target, Timer, Globe,
} from 'lucide-react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

function formatTime(seconds: number): string {
  if (!seconds || seconds === 0) return '0s';
  if (seconds < 60) return `${seconds}s`;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
}

const PERIOD_OPTIONS = [
  { value: 7, label: '7 dias' },
  { value: 30, label: '30 dias' },
  { value: 90, label: '90 dias' },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'novo', label: 'Novos' },
  { value: 'qualificando', label: 'Qualificando' },
  { value: 'agendado', label: 'Agendados' },
  { value: 'sem_interesse', label: 'Sem interesse' },
];

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-zinc-800/50 rounded-lg ${className}`} />;
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const [statusFilter, setStatusFilter] = useState('all');

  const { data, error, isLoading } = useSWR(
    `/api/analytics?days=${days}&status=${statusFilter}`,
    fetcher,
    { refreshInterval: 30000, revalidateOnFocus: true }
  );

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-3">
        <BarChart3 className="h-10 w-10 text-zinc-700" />
        <p className="text-zinc-500">Erro ao carregar analytics</p>
        <p className="text-xs text-zinc-700">{error?.message || 'Tente novamente'}</p>
      </div>
    );
  }

  const s = data?.summary;
  const trends = data?.trends;

  return (
    <div className="p-4 md:p-6 space-y-5 max-w-[1440px] mx-auto">
      {/* Header + Filters */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">Analytics</h1>
          <p className="text-[11px] text-zinc-500 mt-0.5">Performance do agente em tempo real</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Period selector */}
          <div className="flex items-center bg-zinc-900 border border-zinc-800 rounded-lg p-0.5">
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setDays(opt.value)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  days === opt.value
                    ? 'bg-indigo-600 text-white'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-[100px]" />)
        ) : (
          <>
            <MetricCard
              title="Total Leads"
              value={s?.totalLeads || 0}
              icon={Users}
              trend={trends?.leads}
              subtitle={`vs periodo anterior`}
              color="text-indigo-400"
            />
            <MetricCard
              title="Agendaram Call"
              value={s?.scheduled || 0}
              icon={CalendarCheck}
              trend={trends?.scheduled}
              subtitle={`${s?.conversionRate || 0}% de conversao`}
              color="text-emerald-400"
            />
            <MetricCard
              title="Tempo Resposta"
              value={formatTime(s?.medianResponseTimeSec || 0)}
              icon={Clock}
              subtitle={`media: ${formatTime(s?.avgResponseTimeSec || 0)}`}
              color="text-purple-400"
            />
            <MetricCard
              title="Msgs ate Agendar"
              value={s?.avgMsgsToSchedule || 0}
              icon={Zap}
              subtitle="media de mensagens"
              color="text-amber-400"
            />
            <MetricCard
              title="Total Mensagens"
              value={s?.totalMessages || 0}
              icon={MessageSquare}
              subtitle={`${s?.responseRate || 0}% taxa resposta`}
              color="text-blue-400"
            />
          </>
        )}
      </div>

      {/* Row 1: Funnel + Status + Source + Niches */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[320px]" />)
        ) : (
          <>
            <Card className="bg-zinc-900/80 border-zinc-800">
              <CardHeader className="pb-1">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                    <Target className="h-4 w-4 text-indigo-400" />
                    Funil de Conversao
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <FunnelChart data={data?.funnel || []} />
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/80 border-zinc-800">
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-amber-400" />
                  Status dos Leads
                </CardTitle>
              </CardHeader>
              <CardContent>
                <StatusChart data={data?.statusBreakdown || []} />
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/80 border-zinc-800">
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                  <Globe className="h-4 w-4 text-cyan-400" />
                  Origem dos Leads
                </CardTitle>
              </CardHeader>
              <CardContent>
                <SourceChart data={data?.sourceBreakdown || []} />
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/80 border-zinc-800">
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-400" />
                  Top Nichos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <NicheChart data={data?.niches || []} />
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Row 2: Daily Messages + Heatmap */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {isLoading ? (
          <>
            <Skeleton className="h-[320px] lg:col-span-3" />
            <Skeleton className="h-[320px] lg:col-span-2" />
          </>
        ) : (
          <>
            <Card className="bg-zinc-900/80 border-zinc-800 lg:col-span-3">
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-blue-400" />
                  Mensagens por Dia
                </CardTitle>
              </CardHeader>
              <CardContent>
                <DailyChart data={data?.dailyMessages || []} />
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/80 border-zinc-800 lg:col-span-2">
              <CardHeader className="pb-1">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                    <Timer className="h-4 w-4 text-purple-400" />
                    Mapa de Calor
                  </CardTitle>
                  {data?.bestDay && (
                    <span className="text-[10px] text-zinc-500">
                      Melhor dia: <span className="text-indigo-400 font-medium">{data.bestDay}</span>
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-zinc-600 mt-0.5">Horarios de maior atividade (msgs inbound)</p>
              </CardHeader>
              <CardContent>
                <HeatmapChart data={data?.heatmap || []} />
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Leads Table */}
      <Card className="bg-zinc-900/80 border-zinc-800">
        <CardHeader className="pb-2">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
            <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
              <Users className="h-4 w-4 text-indigo-400" />
              Leads ({data?.recentLeads?.length || 0})
            </CardTitle>
            {/* Status filter */}
            <div className="flex items-center bg-zinc-800 rounded-lg p-0.5">
              {STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setStatusFilter(opt.value)}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                    statusFilter === opt.value
                      ? 'bg-zinc-700 text-zinc-200'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <Skeleton className="h-[400px] m-4" />
          ) : (
            <LeadsTable leads={data?.recentLeads || []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
