'use client';

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface AdsData {
  ad_name: string;
  campaign_name: string;
  leads: number;
}

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#818cf8', '#4f46e5', '#4338ca', '#3730a3', '#312e81'];

function truncate(str: string, max: number) {
  if (!str || str === '(direto)' || str === '(sem campanha)') return str;
  return str.length > max ? str.slice(0, max) + '…' : str;
}

export function AdsChart({ data }: { data: AdsData[] }) {
  const byAd = data
    .filter((d) => d.ad_name !== '(direto)' && d.ad_name !== '(sem campanha)')
    .reduce<Record<string, number>>((acc, d) => {
      acc[d.ad_name] = (acc[d.ad_name] || 0) + d.leads;
      return acc;
    }, {});

  const byCampaign = data
    .filter((d) => d.campaign_name !== '(sem campanha)')
    .reduce<Record<string, number>>((acc, d) => {
      acc[d.campaign_name] = (acc[d.campaign_name] || 0) + d.leads;
      return acc;
    }, {});

  const adRows = Object.entries(byAd)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name, leads]) => ({ name, leads }));

  const campaignRows = Object.entries(byCampaign)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, leads]) => ({ name, leads }));

  if (adRows.length === 0 && campaignRows.length === 0) {
    return (
      <div className="flex items-center justify-center h-[220px] text-zinc-600 text-sm">
        Sem dados de anúncios no período
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {adRows.length > 0 && (
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Leads por anúncio</p>
          <ResponsiveContainer width="100%" height={Math.max(80, adRows.length * 28)}>
            <BarChart data={adRows} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="name"
                width={140}
                tick={{ fill: '#a1a1aa', fontSize: 10 }}
                tickFormatter={(v) => truncate(v, 20)}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px', fontSize: 11 }}
                itemStyle={{ color: '#e4e4e7' }}
                formatter={(v: number, _: string, p) => [v, p.payload.name]}
                labelFormatter={() => ''}
              />
              <Bar dataKey="leads" radius={[0, 4, 4, 0]} maxBarSize={16}>
                {adRows.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {campaignRows.length > 0 && (
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Leads por campanha</p>
          <div className="flex flex-col gap-1.5">
            {campaignRows.map((row, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                <span className="text-[11px] text-zinc-400 flex-1 truncate" title={row.name}>
                  {truncate(row.name, 28)}
                </span>
                <span className="text-xs font-medium text-zinc-300">{row.leads}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
