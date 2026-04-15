'use client';

interface AdsData {
  ad_name: string;
  campaign_name: string;
  leads: number;
}

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#818cf8', '#4f46e5', '#4338ca', '#c4b5fd', '#ddd6fe', '#3730a3', '#312e81'];

function truncate(s: string, max: number): string {
  if (!s) return '';
  return s.length > max ? s.slice(0, max) + '...' : s;
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
    .slice(0, 8);

  const campaignRows = Object.entries(byCampaign)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const maxAd = adRows[0]?.[1] || 1;

  if (adRows.length === 0 && campaignRows.length === 0) {
    return (
      <div className="flex items-center justify-center h-[120px] text-zinc-600 text-sm">
        Sem dados de anuncios no periodo
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {adRows.length > 0 && (
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-3">Leads por anuncio</p>
          <div className="flex flex-col gap-2">
            {adRows.map(([name, leads], i) => (
              <div key={name} className="flex items-center gap-2">
                <span className="text-[11px] text-zinc-400 w-[140px] shrink-0 truncate" title={name}>
                  {truncate(name, 22)}
                </span>
                <div className="flex-1 h-4 bg-zinc-800 rounded-sm overflow-hidden">
                  <div
                    className="h-full rounded-sm transition-all"
                    style={{
                      width: `${Math.max(4, (leads / maxAd) * 100)}%`,
                      backgroundColor: COLORS[i % COLORS.length],
                    }}
                  />
                </div>
                <span className="text-xs font-medium text-zinc-300 w-6 text-right shrink-0">{leads}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {campaignRows.length > 0 && (
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Leads por campanha</p>
          <div className="flex flex-col gap-1.5">
            {campaignRows.map(([name, leads], i) => (
              <div key={name} className="flex items-center gap-2">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="text-[11px] text-zinc-400 flex-1 truncate" title={name}>
                  {truncate(name, 30)}
                </span>
                <span className="text-xs font-medium text-zinc-300">{leads}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
