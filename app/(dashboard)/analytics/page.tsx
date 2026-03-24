'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MetricCard } from '@/components/analytics/metric-card';
import { FunnelChart } from '@/components/analytics/funnel-chart';
import { DailyChart } from '@/components/analytics/daily-chart';
import { StatusChart } from '@/components/analytics/status-chart';
import { LeadsTable } from '@/components/analytics/leads-table';
import { Users, MessageSquare, CalendarCheck, Clock, TrendingUp, Percent } from 'lucide-react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
}

function SkeletonCard() {
  return <div className="h-[106px] rounded-xl bg-zinc-900 border border-zinc-800 animate-pulse" />;
}

function SkeletonChart() {
  return <div className="h-[320px] rounded-xl bg-zinc-900 border border-zinc-800 animate-pulse" />;
}

export default function AnalyticsPage() {
  const { data, error, isLoading } = useSWR('/api/analytics', fetcher, {
    refreshInterval: 30000,
  });

  if (error) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <p className="text-zinc-500">Erro ao carregar analytics</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">Analytics</h1>
        <p className="text-xs text-zinc-500 mt-1">Visao geral do desempenho do agente</p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <MetricCard
              title="Total Leads"
              value={data?.summary?.totalLeads || 0}
              icon={Users}
              color="text-indigo-400"
            />
            <MetricCard
              title="Responderam"
              value={data?.summary?.responded || 0}
              icon={MessageSquare}
              color="text-blue-400"
            />
            <MetricCard
              title="Interesse"
              value={data?.summary?.interested || 0}
              icon={TrendingUp}
              color="text-amber-400"
            />
            <MetricCard
              title="Agendaram"
              value={data?.summary?.scheduled || 0}
              icon={CalendarCheck}
              color="text-green-400"
            />
            <MetricCard
              title="Tempo Resposta"
              value={formatTime(data?.summary?.avgResponseTimeSec || 0)}
              subtitle="media do bot"
              icon={Clock}
              color="text-purple-400"
            />
            <MetricCard
              title="Conversao"
              value={`${data?.summary?.conversionRate || 0}%`}
              subtitle="lead → call"
              icon={Percent}
              color="text-emerald-400"
            />
          </>
        )}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <>
            <SkeletonChart />
            <SkeletonChart />
            <SkeletonChart />
          </>
        ) : (
          <>
            <Card className="bg-zinc-900 border-zinc-800 lg:col-span-1">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-zinc-300">Funil de Conversao</CardTitle>
              </CardHeader>
              <CardContent>
                <FunnelChart data={data?.funnel || []} />
              </CardContent>
            </Card>

            <Card className="bg-zinc-900 border-zinc-800 lg:col-span-1">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-zinc-300">Mensagens (30 dias)</CardTitle>
              </CardHeader>
              <CardContent>
                <DailyChart data={data?.dailyMessages || []} />
              </CardContent>
            </Card>

            <Card className="bg-zinc-900 border-zinc-800 lg:col-span-1">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-zinc-300">Status dos Leads</CardTitle>
              </CardHeader>
              <CardContent>
                <StatusChart data={data?.statusBreakdown || []} />
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Leads Table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-zinc-300">Leads Recentes</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="h-[300px] animate-pulse" />
          ) : (
            <LeadsTable leads={data?.recentLeads || []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
