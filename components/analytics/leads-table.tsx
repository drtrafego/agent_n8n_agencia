'use client';

import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { MessageSquare, ExternalLink } from 'lucide-react';
import Link from 'next/link';

interface Lead {
  id: string;
  name: string;
  phone: string;
  last_message: string;
  last_message_at: string;
  status: string;
  observacoes: string;
  msg_count: number;
  first_contact: string;
  conversation_id: string;
}

const STATUS_STYLES: Record<string, { label: string; dot: string; bg: string; text: string }> = {
  agendado: { label: 'Agendado', dot: 'bg-emerald-400', bg: 'bg-emerald-500/10', text: 'text-emerald-400' },
  qualificando: { label: 'Qualificando', dot: 'bg-amber-400', bg: 'bg-amber-500/10', text: 'text-amber-400' },
  sem_interesse: { label: 'Sem interesse', dot: 'bg-red-400', bg: 'bg-red-500/10', text: 'text-red-400' },
  novo: { label: 'Novo', dot: 'bg-indigo-400', bg: 'bg-indigo-500/10', text: 'text-indigo-400' },
};

export function LeadsTable({ leads }: { leads: Lead[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className="text-left py-3 px-4 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Contato</th>
            <th className="text-left py-3 px-4 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider hidden md:table-cell">Ultima msg</th>
            <th className="text-center py-3 px-4 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Msgs</th>
            <th className="text-left py-3 px-4 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Status</th>
            <th className="text-left py-3 px-4 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider hidden lg:table-cell">Quando</th>
            <th className="text-left py-3 px-4 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider hidden xl:table-cell">Observacoes</th>
            <th className="text-center py-3 px-4 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider w-10"></th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead, i) => {
            const style = STATUS_STYLES[lead.status] || STATUS_STYLES.novo;
            return (
              <tr key={i} className="border-b border-zinc-800/30 hover:bg-zinc-800/20 transition-colors group">
                <td className="py-3 px-4">
                  <div>
                    <span className="text-zinc-200 font-medium text-sm">{lead.name}</span>
                    <span className="block text-[11px] text-zinc-600 font-mono">{lead.phone}</span>
                  </div>
                </td>
                <td className="py-3 px-4 hidden md:table-cell max-w-[220px]">
                  <span className="text-zinc-400 text-xs line-clamp-1">{lead.last_message || '-'}</span>
                </td>
                <td className="py-3 px-4 text-center">
                  <div className="flex items-center justify-center gap-1">
                    <MessageSquare className="h-3 w-3 text-zinc-600" />
                    <span className="text-xs text-zinc-400">{lead.msg_count}</span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium ${style.bg} ${style.text}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
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
                <td className="py-3 px-4 hidden xl:table-cell max-w-[280px]">
                  <span className="text-zinc-500 text-xs line-clamp-2">{lead.observacoes || '-'}</span>
                </td>
                <td className="py-3 px-4 text-center">
                  {lead.conversation_id && (
                    <Link
                      href={`/inbox/${lead.conversation_id}`}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-zinc-700"
                    >
                      <ExternalLink className="h-3.5 w-3.5 text-zinc-500 hover:text-zinc-300" />
                    </Link>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {leads.length === 0 && (
        <div className="text-center py-12 text-zinc-600 text-sm">Nenhum lead encontrado</div>
      )}
    </div>
  );
}
