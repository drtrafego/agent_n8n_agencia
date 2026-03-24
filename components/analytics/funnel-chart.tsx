'use client';

interface FunnelData {
  stage: string;
  value: number;
  dropRate: number;
}

export function FunnelChart({ data }: { data: FunnelData[] }) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="space-y-3">
      {data.map((item, i) => {
        const widthPct = Math.max((item.value / maxValue) * 100, 8);
        const colors = ['bg-indigo-500', 'bg-blue-500', 'bg-amber-500', 'bg-emerald-500'];
        const bgColors = ['bg-indigo-500/10', 'bg-blue-500/10', 'bg-amber-500/10', 'bg-emerald-500/10'];

        return (
          <div key={item.stage}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-zinc-400">{item.stage}</span>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-zinc-200">{item.value}</span>
                {i > 0 && item.dropRate > 0 && (
                  <span className="text-[10px] text-red-400/80">-{item.dropRate}%</span>
                )}
              </div>
            </div>
            <div className={`w-full h-7 rounded-md ${bgColors[i]}`}>
              <div
                className={`h-full rounded-md ${colors[i]} transition-all duration-700`}
                style={{ width: `${widthPct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
