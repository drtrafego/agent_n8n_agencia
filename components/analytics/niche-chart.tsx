'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface NicheData {
  niche: string;
  count: number;
}

export function NicheChart({ data }: { data: NicheData[] }) {
  const sorted = [...data].filter((d) => d.niche !== 'Outros').sort((a, b) => b.count - a.count).slice(0, 8);

  return (
    <div className="w-full h-[250px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sorted} layout="vertical" margin={{ top: 5, right: 20, left: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
          <XAxis type="number" stroke="#71717a" fontSize={11} />
          <YAxis type="category" dataKey="niche" stroke="#71717a" fontSize={11} width={90} tick={{ fill: '#a1a1aa' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px', fontSize: '12px' }}
            labelStyle={{ color: '#e4e4e7' }}
            itemStyle={{ color: '#818cf8' }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) => [`${value} leads`, 'Quantidade']}
          />
          <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
