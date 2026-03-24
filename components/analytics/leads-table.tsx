'use client';

import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface Lead {
  name: string;
  phone: string;
  last_message: string;
  last_message_at: string;
  status: string;
  observacoes: string;
}

const STATUS_STYLES: Record<string, { label: string; bg: string; text: string }> = {
  agendado: { label: 'Agendado', bg: 'bg-green-500/10', text: 'text-green-400' },
  qualificando: { label: 'Qualificando', bg: 'bg-amber-500/10', text: 'text-amber-400' },
  sem_interesse: { label: 'Sem interesse', bg: 'bg-red-500/10', text: 'text-red-400' },
  novo: { label: 'Novo', bg: 'bg-indigo-500/10', text: 'text-indigo-400' },
};

export function LeadsTable({ leads }: { leads: Lead[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className="text-left py-3 px-4 text-xs font-medium text-zinc-500 uppercase">Contato</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-zinc-500 uppercase hidden md:table-cell">Ultima msg</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-zinc-500 uppercase">Status</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-zinc-500 uppercase hidden lg:table-cell">Quando</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-zinc-500 uppercase hidden xl:table-cell">Observacoes</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead, i) => {
            const style = STATUS_STYLES[lead.status] || STATUS_STYLES.novo;
            return (
              <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                <td className="py-3 px-4">
                  <div>
                    <span className="text-zinc-200 font-medium">{lead.name}</span>
                    <span className="block text-[11px] text-zinc-600">{lead.phone}</span>
                  </div>
                </td>
                <td className="py-3 px-4 hidden md:table-cell">
                  <span className="text-zinc-400 text-xs line-clamp-1 max-w-[200px]">
                    {lead.last_message || '-'}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${style.bg} ${style.text}`}>
                    {style.label}
                  </span>
                </td>
                <td className="py-3 px-4 hidden lg:table-cell">
                  <span className="text-zinc-500 text-xs">
                    {lead.last_message_at
                      ? formatDistanceToNow(new Date(lead.last_message_at), { addSuffix: true, locale: ptBR })
                      : '-'}
                  </span>
                </td>
                <td className="py-3 px-4 hidden xl:table-cell">
                  <span className="text-zinc-500 text-xs line-clamp-2 max-w-[300px]">
                    {lead.observacoes || '-'}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {leads.length === 0 && (
        <div className="text-center py-10 text-zinc-600 text-sm">Nenhum lead encontrado</div>
      )}
    </div>
  );
}
