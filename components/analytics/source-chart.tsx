'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface SourceData {
  source: string;
  count: number;
}

const SOURCE_LABELS: Record<string, string> = {
  direto: 'WhatsApp Direto',
  campanha: 'Meta Ads',
  google: 'Google',
};

const SOURCE_COLORS: Record<string, string> = {
  direto: '#25D366',
  campanha: '#1877F2',
  google: '#EA4335',
};

function SourceIcon({ source, size = 16 }: { source: string; size?: number }) {
  if (source === 'campanha') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="shrink-0">
        <path d="M12 2C6.477 2 2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.879V14.89h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.989C18.343 21.129 22 16.99 22 12c0-5.523-4.477-10-10-10z" fill="#1877F2"/>
      </svg>
    );
  }
  if (source === 'google') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="shrink-0">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
      </svg>
    );
  }
  // WhatsApp
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="shrink-0">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" fill="#25D366"/>
    </svg>
  );
}

export function SourceChart({ data }: { data: SourceData[] }) {
  const total = data.reduce((acc, d) => acc + d.count, 0);

  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-[250px] text-zinc-600 text-sm">
        Sem dados de origem
      </div>
    );
  }

  const formatted = data.map((d) => ({
    name: SOURCE_LABELS[d.source] || d.source,
    value: d.count,
    color: SOURCE_COLORS[d.source] || '#71717a',
    source: d.source,
  }));

  return (
    <div className="flex flex-col gap-4">
      <div className="w-full h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={formatted}
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={70}
              paddingAngle={4}
              dataKey="value"
            >
              {formatted.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
              itemStyle={{ color: '#e4e4e7' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {/* Legend with icons */}
      <div className="flex flex-col gap-2 px-2">
        {formatted.map((entry) => {
          const pct = total > 0 ? Math.round((entry.value / total) * 100) : 0;
          return (
            <div key={entry.source} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <SourceIcon source={entry.source} size={14} />
                <span className="text-xs text-zinc-400">{entry.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-zinc-300">{entry.value}</span>
                <span className="text-[10px] text-zinc-600">({pct}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
