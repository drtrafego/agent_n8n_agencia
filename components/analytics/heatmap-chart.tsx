'use client';

interface HeatmapData {
  dow: string;
  hour: number;
  count: number;
}

const DAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function getColor(count: number, max: number): string {
  if (count === 0 || max === 0) return 'bg-zinc-800/40';
  const ratio = count / max;
  if (ratio > 0.75) return 'bg-indigo-500';
  if (ratio > 0.5) return 'bg-indigo-500/70';
  if (ratio > 0.25) return 'bg-indigo-500/40';
  return 'bg-indigo-500/20';
}

export function HeatmapChart({ data }: { data: HeatmapData[] }) {
  const lookup: Record<string, number> = {};
  let maxCount = 0;
  for (const d of data) {
    const key = `${d.dow}-${d.hour}`;
    lookup[key] = d.count;
    if (d.count > maxCount) maxCount = d.count;
  }

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[600px]">
        {/* Header hours */}
        <div className="flex items-center mb-1">
          <div className="w-10 shrink-0" />
          {HOURS.filter((h) => h % 2 === 0).map((h) => (
            <div key={h} className="flex-1 text-center text-[10px] text-zinc-600" style={{ minWidth: '20px' }}>
              {h}h
            </div>
          ))}
        </div>
        {/* Rows */}
        {DAYS.map((day) => (
          <div key={day} className="flex items-center gap-[2px] mb-[2px]">
            <div className="w-10 shrink-0 text-[10px] text-zinc-500 text-right pr-2">{day}</div>
            {HOURS.map((hour) => {
              const count = lookup[`${day}-${hour}`] || 0;
              return (
                <div
                  key={hour}
                  className={`flex-1 h-5 rounded-sm ${getColor(count, maxCount)} transition-colors hover:ring-1 hover:ring-indigo-400`}
                  title={`${day} ${hour}h: ${count} msgs`}
                  style={{ minWidth: '16px' }}
                />
              );
            })}
          </div>
        ))}
        {/* Legend */}
        <div className="flex items-center justify-end gap-1 mt-2">
          <span className="text-[10px] text-zinc-600 mr-1">Menos</span>
          <div className="w-3 h-3 rounded-sm bg-zinc-800/40" />
          <div className="w-3 h-3 rounded-sm bg-indigo-500/20" />
          <div className="w-3 h-3 rounded-sm bg-indigo-500/40" />
          <div className="w-3 h-3 rounded-sm bg-indigo-500/70" />
          <div className="w-3 h-3 rounded-sm bg-indigo-500" />
          <span className="text-[10px] text-zinc-600 ml-1">Mais</span>
        </div>
      </div>
    </div>
  );
}
