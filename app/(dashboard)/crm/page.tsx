'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Search, X, MessageSquare, Clock, GripVertical, User, Phone,
  FileText, ChevronRight, Loader2, Save, ExternalLink, Filter,
  TrendingUp, RefreshCw, Flame, Snowflake, Zap,
  ArrowUpDown, BarChart3,
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────

interface Lead {
  id: number;
  nome: string | null;
  telefone: string | null;
  email: string | null;
  nicho: string | null;
  observacoes_sdr: string | null;
  stage: string;
  stage_updated_at: string | null;
  created_at: string;
  source: string | null;
  wa_contact_name: string | null;
  wa_phone: string | null;
  last_message: string | null;
  last_message_at: string | null;
  message_count: string;
  followup_count?: number;
  last_bot_msg_at?: string | null;
  last_lead_msg_at?: string | null;
}

interface Message {
  id: string;
  direction: string;
  body: string | null;
  sent_by: string | null;
  created_at: string;
  type: string;
}

interface LeadDetail {
  contact: {
    id: number;
    nome: string | null;
    telefone: string | null;
    email: string | null;
    nicho: string | null;
    observacoes_sdr: string | null;
    stage: string;
    source: string | null;
    created_at: string;
    updated_at: string;
    followup_count?: number;
    last_bot_msg_at?: string | null;
    last_lead_msg_at?: string | null;
  };
  messages: Message[];
}

// ─── Constants ───────────────────────────────────────────────────────

const STAGES = [
  { key: 'novo', label: 'Novo', color: 'bg-zinc-600', badgeBg: 'bg-zinc-700', textColor: 'text-zinc-300', borderColor: 'border-zinc-700', dotColor: '#71717a' },
  { key: 'qualificando', label: 'Qualificando', color: 'bg-blue-600', badgeBg: 'bg-blue-900/50', textColor: 'text-blue-300', borderColor: 'border-blue-800/50', dotColor: '#3b82f6' },
  { key: 'interesse', label: 'Interesse', color: 'bg-yellow-600', badgeBg: 'bg-yellow-900/50', textColor: 'text-yellow-300', borderColor: 'border-yellow-800/50', dotColor: '#eab308' },
  { key: 'agendado', label: 'Agendado', color: 'bg-green-600', badgeBg: 'bg-green-900/50', textColor: 'text-green-300', borderColor: 'border-green-800/50', dotColor: '#22c55e' },
  { key: 'realizada', label: 'Realizada', color: 'bg-emerald-600', badgeBg: 'bg-emerald-900/50', textColor: 'text-emerald-300', borderColor: 'border-emerald-800/50', dotColor: '#10b981' },
  { key: 'convertido', label: 'Convertido', color: 'bg-purple-600', badgeBg: 'bg-purple-900/50', textColor: 'text-purple-300', borderColor: 'border-purple-800/50', dotColor: '#a855f7' },
  { key: 'sem_interesse', label: 'Sem Interesse', color: 'bg-red-600', badgeBg: 'bg-red-900/50', textColor: 'text-red-300', borderColor: 'border-red-800/50', dotColor: '#ef4444' },
] as const;

const SOURCE_OPTIONS = [
  { value: '', label: 'Todas origens' },
  { value: 'whatsapp', label: 'WhatsApp Direto' },
  { value: 'whatsapp_campanha', label: 'WhatsApp Campanha' },
  { value: 'campanha', label: 'Meta Ads (legado)' },
  { value: 'direto', label: 'Direto (legado)' },
  { value: 'google', label: 'Google Ads' },
  { value: 'organico', label: 'Organico' },
  { value: 'indicacao', label: 'Indicacao' },
];

const SORT_OPTIONS = [
  { value: 'recent', label: 'Mais recente' },
  { value: 'oldest', label: 'Mais antigo' },
  { value: 'messages', label: 'Mais mensagens' },
  { value: 'activity', label: 'Ultima atividade' },
];

// ─── Source Icon ─────────────────────────────────────────────────────

const SOURCE_LABELS: Record<string, string> = {
  google: 'Origem: Google Ads',
  whatsapp: 'Origem: WhatsApp direto',
  whatsapp_campanha: 'Origem: WhatsApp via campanha (anuncio)',
  campanha: 'Origem: Meta Ads (legado)',
  direto: 'Origem: Direto',
  organico: 'Origem: Organico',
  indicacao: 'Origem: Indicacao',
};

function SourceIcon({ source, size = 14 }: { source: string | null; size?: number }) {
  const label = SOURCE_LABELS[source || ''] || 'Origem: WhatsApp';

  if (source === 'google') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="shrink-0" aria-label={label}>
        <title>{label}</title>
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
      </svg>
    );
  }
  if (source === 'whatsapp' || source === 'whatsapp_campanha' || source === 'direto' || !source) {
    return (
      <span className="relative shrink-0 inline-flex" title={label}>
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" fill="#25D366"/>
        </svg>
        {source === 'whatsapp_campanha' && (
          <span className="absolute -right-1 -top-1 flex h-2.5 w-2.5 items-center justify-center rounded-full bg-blue-500 text-[6px] font-bold text-white ring-1 ring-zinc-900">⚡</span>
        )}
      </span>
    );
  }
  if (source === 'campanha') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="shrink-0" aria-label={label}>
        <title>{label}</title>
        <path d="M12 2C6.477 2 2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.879V14.89h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.989C18.343 21.129 22 16.99 22 12c0-5.523-4.477-10-10-10z" fill="#1877F2"/>
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="shrink-0" aria-label={label}>
      <title>{label}</title>
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" fill="#25D366"/>
    </svg>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'agora';
  if (diffMin < 60) return `${diffMin}m`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 30) return `${diffD}d`;
  return `${Math.floor(diffD / 30)}mo`;
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function truncate(str: string | null, len: number): string {
  if (!str) return '';
  return str.length > len ? str.slice(0, len) + '...' : str;
}

/** Temperatura do lead baseada na atividade recente */
function getLeadTemperature(lead: Lead): 'hot' | 'warm' | 'cold' {
  const lastActivity = lead.last_message_at || lead.created_at;
  const diffH = (Date.now() - new Date(lastActivity).getTime()) / 3600000;
  if (diffH < 24) return 'hot';
  if (diffH < 72) return 'warm';
  return 'cold';
}

const TEMP_LABELS = {
  hot: 'Quente: ativo nas ultimas 24h',
  warm: 'Morno: ativo entre 24h e 72h',
  cold: 'Frio: sem atividade ha mais de 72h',
} as const;

function TemperatureIcon({ temp, size: s = 11 }: { temp: 'hot' | 'warm' | 'cold'; size?: number }) {
  if (temp === 'hot') return <span title={TEMP_LABELS.hot}><Flame size={s} className="text-orange-400" /></span>;
  if (temp === 'warm') return <span title={TEMP_LABELS.warm}><Zap size={s} className="text-yellow-400" /></span>;
  return <span title={TEMP_LABELS.cold}><Snowflake size={s} className="text-blue-400" /></span>;
}

// ─── Stats Bar ──────────────────────────────────────────────────────

function StatsBar({ data }: { data: Record<string, Lead[]> }) {
  const totalLeads = STAGES.reduce((sum, s) => sum + (data[s.key]?.length || 0), 0);
  const novos = data['novo']?.length || 0;
  const qualificando = data['qualificando']?.length || 0;
  const interesse = data['interesse']?.length || 0;
  const agendados = data['agendado']?.length || 0;
  const realizadas = data['realizada']?.length || 0;
  const convertidos = data['convertido']?.length || 0;
  const perdidos = data['sem_interesse']?.length || 0;

  const taxaQualif = totalLeads > 0 ? Math.round(((qualificando + interesse + agendados + realizadas + convertidos) / totalLeads) * 100) : 0;
  const taxaAgend = totalLeads > 0 ? Math.round(((agendados + realizadas + convertidos) / totalLeads) * 100) : 0;
  const taxaConv = totalLeads > 0 ? Math.round((convertidos / totalLeads) * 100) : 0;

  const stats = [
    { label: 'Total', value: totalLeads, color: 'text-zinc-100', tip: 'Total de leads no CRM' },
    { label: 'Novos', value: novos, color: 'text-zinc-400', tip: 'Leads que ainda nao foram qualificados' },
    { label: 'Qualificacao', value: `${taxaQualif}%`, color: 'text-blue-400', tip: '% de leads que passaram de Novo (qualificando + interesse + agendado + realizada + convertido)' },
    { label: 'Agendamento', value: `${taxaAgend}%`, color: 'text-green-400', tip: '% de leads que agendaram (agendado + realizada + convertido)' },
    { label: 'Conversao', value: `${taxaConv}%`, color: 'text-purple-400', tip: '% de leads convertidos em clientes' },
    { label: 'Perdidos', value: perdidos, color: 'text-red-400', tip: 'Leads marcados como sem interesse' },
  ];

  return (
    <div className="flex items-center gap-1 overflow-x-auto">
      {stats.map((s, i) => (
        <div key={s.label} className="flex items-center gap-1.5 shrink-0 cursor-default" title={s.tip}>
          {i > 0 && <span className="text-zinc-800 mx-1">|</span>}
          <span className="text-[10px] text-zinc-500">{s.label}</span>
          <span className={`text-xs font-bold ${s.color}`}>{s.value}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Lead Card ───────────────────────────────────────────────────────

function LeadCard({
  lead,
  onDragStart,
  onClick,
}: {
  lead: Lead;
  onDragStart: (e: React.DragEvent, leadId: number, fromStage: string) => void;
  onClick: (lead: Lead) => void;
}) {
  const displayName = lead.nome || lead.wa_contact_name || lead.telefone || 'Sem nome';
  const temp = getLeadTemperature(lead);
  const followups = lead.followup_count || 0;
  const lastActivity = lead.last_message_at || lead.stage_updated_at || lead.created_at;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, lead.id, lead.stage)}
      onClick={() => onClick(lead)}
      className="group bg-zinc-800/80 hover:bg-zinc-800 border border-zinc-700/50 hover:border-zinc-600 rounded-lg p-3 cursor-pointer transition-all duration-150 hover:shadow-lg hover:shadow-black/20"
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <GripVertical size={14} className="text-zinc-600 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
          <span className="text-sm font-medium text-zinc-100 truncate">{displayName}</span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <TemperatureIcon temp={temp} />
          <SourceIcon source={lead.source} size={13} />
          <ChevronRight size={14} className="text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>

      <div className="flex items-center gap-1.5 mb-2 flex-wrap">
        {lead.nicho && (
          <span title="Nicho/segmento do lead" className="inline-block text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-900/40 text-indigo-300 border border-indigo-800/30">
            {lead.nicho}
          </span>
        )}
        {followups > 0 && followups < 99 && (
          <span title={`${followups} follow-up(s) automatico(s) enviado(s)`} className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-amber-900/40 text-amber-300 border border-amber-800/30">
            {followups}x follow-up
          </span>
        )}
        {followups >= 99 && (
          <span title="Lembrete de reagendamento enviado (lead tinha reuniao agendada)" className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-pink-900/40 text-pink-300 border border-pink-800/30">
            Lembrete reagendamento
          </span>
        )}
      </div>

      {lead.last_message && (
        <p title="Ultima mensagem da conversa" className="text-xs text-zinc-500 mb-2 leading-relaxed line-clamp-2">{truncate(lead.last_message, 80)}</p>
      )}

      <div className="flex items-center justify-between text-[10px] text-zinc-600">
        <div className="flex items-center gap-3">
          <span title="Idade do lead (quando entrou)" className="flex items-center gap-1"><Clock size={10} />{timeAgo(lead.created_at)}</span>
          <span title="Total de mensagens trocadas" className="flex items-center gap-1"><MessageSquare size={10} />{lead.message_count}</span>
        </div>
        {lastActivity && lead.last_message_at && (
          <span title="Ultima atividade na conversa" className="text-zinc-700">ult. {timeAgo(lastActivity)}</span>
        )}
      </div>
    </div>
  );
}

// ─── Column ──────────────────────────────────────────────────────────

function KanbanColumn({
  stage, leads, totalLeads, onDragStart, onDrop, onCardClick,
}: {
  stage: (typeof STAGES)[number];
  leads: Lead[];
  totalLeads: number;
  onDragStart: (e: React.DragEvent, leadId: number, fromStage: string) => void;
  onDrop: (stageKey: string) => void;
  onCardClick: (lead: Lead) => void;
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const pct = totalLeads > 0 ? Math.round((leads.length / totalLeads) * 100) : 0;

  return (
    <div
      className={`flex flex-col min-w-[280px] w-[280px] shrink-0 rounded-xl transition-colors duration-150 ${isDragOver ? 'bg-zinc-800/50 ring-1 ring-indigo-500/30' : 'bg-zinc-900/50'}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => { e.preventDefault(); setIsDragOver(false); onDrop(stage.key); }}
    >
      <div className="flex items-center gap-2 px-3 py-3">
        <div className={`w-2.5 h-2.5 rounded-full ${stage.color}`} />
        <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">{stage.label}</h3>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="text-[10px] text-zinc-600">{pct}%</span>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${stage.badgeBg} ${stage.textColor}`}>{leads.length}</span>
        </div>
      </div>

      {/* Mini progress bar */}
      <div className="px-3 pb-2">
        <div className="h-0.5 bg-zinc-800 rounded-full overflow-hidden">
          <div className={`h-full ${stage.color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-2 min-h-[100px]">
        {leads.length === 0 && (
          <div className="flex items-center justify-center h-20 text-xs text-zinc-700 border border-dashed border-zinc-800 rounded-lg">Nenhum lead</div>
        )}
        {leads.map((lead) => (
          <LeadCard key={lead.id} lead={lead} onDragStart={onDragStart} onClick={onCardClick} />
        ))}
      </div>
    </div>
  );
}

// ─── Lead Modal ──────────────────────────────────────────────────────

function LeadModal({
  lead, onClose, onUpdate,
}: {
  lead: Lead;
  onClose: () => void;
  onUpdate: () => void;
}) {
  const [tab, setTab] = useState<'detalhes' | 'historico' | 'notas'>('detalhes');
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    nome: '', email: '', nicho: '', source: '', stage: '',
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/crm/lead/${lead.id}`)
      .then((r) => r.json())
      .then((data: LeadDetail) => {
        setDetail(data);
        setForm({
          nome: data.contact.nome || '',
          email: data.contact.email || '',
          nicho: data.contact.nicho || '',
          source: data.contact.source || 'direto',
          stage: data.contact.stage || 'novo',
        });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [lead.id]);

  useEffect(() => {
    if (tab === 'historico' && detail?.messages?.length) {
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, [tab, detail]);

  async function handleSave() {
    setSaving(true);
    try {
      const res = await fetch(`/api/crm/lead/${lead.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        onUpdate();
        onClose();
      }
    } finally {
      setSaving(false);
    }
  }

  // Escape key to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const displayName = lead.nome || lead.wa_contact_name || lead.telefone || 'Sem nome';
  const stageInfo = STAGES.find((s) => s.key === lead.stage) || STAGES[0];
  const temp = getLeadTemperature(lead);
  const followups = lead.followup_count || 0;
  const msgCount = detail?.messages?.length || Number(lead.message_count) || 0;
  const TABS = [
    { key: 'detalhes' as const, label: 'Detalhes', icon: User },
    { key: 'historico' as const, label: `Historico (${msgCount})`, icon: MessageSquare },
    { key: 'notas' as const, label: 'Notas SDR', icon: FileText },
  ];

  const allSourceOptions = SOURCE_OPTIONS.filter(o => o.value !== '');

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/70 z-40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-zinc-900 border border-zinc-700/50 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-zinc-800">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <SourceIcon source={lead.source} size={18} />
                <h2 className="text-base font-semibold text-zinc-100 truncate">{displayName}</h2>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${stageInfo.badgeBg} ${stageInfo.textColor}`}>
                  {stageInfo.label}
                </span>
                <TemperatureIcon temp={temp} />
              </div>
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                {lead.telefone && (
                  <span className="flex items-center gap-1 text-[11px] text-zinc-500"><Phone size={10} />{lead.telefone}</span>
                )}
                {lead.nicho && <span className="text-[11px] text-indigo-400">{lead.nicho}</span>}
                {followups > 0 && followups < 99 && <span className="text-[11px] text-amber-400">{followups}x follow-up</span>}
                {followups >= 99 && <span className="text-[11px] text-pink-400">Lembrete reagendamento</span>}
                <span className="text-[11px] text-zinc-600">Criado {timeAgo(lead.created_at)}</span>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              {/* Link para inbox */}
              {lead.telefone && (
                <a
                  href={`/inbox`}
                  className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-indigo-400 transition-colors"
                  title="Abrir no Inbox"
                >
                  <ExternalLink size={16} />
                </a>
              )}
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors">
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-zinc-800 px-5">
            {TABS.map((t) => {
              const Icon = t.icon;
              return (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                    tab === t.key
                      ? 'text-indigo-400 border-indigo-500'
                      : 'text-zinc-500 border-transparent hover:text-zinc-300'
                  }`}
                >
                  <Icon size={12} />
                  {t.label}
                </button>
              );
            })}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 size={24} className="text-zinc-600 animate-spin" />
              </div>
            ) : tab === 'detalhes' ? (
              <div className="p-5 space-y-4">
                {/* Info cards */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                    <p className="text-lg font-bold text-zinc-100">{msgCount}</p>
                    <p className="text-[10px] text-zinc-500">Mensagens</p>
                  </div>
                  <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                    <p className="text-lg font-bold text-zinc-100">{followups >= 99 ? '✓' : followups}</p>
                    <p className="text-[10px] text-zinc-500">{followups >= 99 ? 'Reagendamento' : 'Follow-ups'}</p>
                  </div>
                  <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                    <p className="text-lg font-bold text-zinc-100">{timeAgo(lead.created_at) || 'N/A'}</p>
                    <p className="text-[10px] text-zinc-500">Idade do lead</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="flex items-center gap-1.5 text-[11px] text-zinc-500 mb-1.5"><User size={11} />Nome</label>
                    <input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })}
                      className="w-full bg-zinc-800 border border-zinc-700/50 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-600/50" />
                  </div>
                  <div>
                    <label className="flex items-center gap-1.5 text-[11px] text-zinc-500 mb-1.5"><Phone size={11} />WhatsApp</label>
                    <input value={lead.telefone || ''} disabled
                      className="w-full bg-zinc-800/50 border border-zinc-700/30 rounded-lg px-3 py-2 text-sm text-zinc-500 cursor-not-allowed" />
                  </div>
                </div>

                <div>
                  <label className="text-[11px] text-zinc-500 mb-1.5 block">Email</label>
                  <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700/50 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-600/50" />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-[11px] text-zinc-500 mb-1.5 block">Nicho</label>
                    <input value={form.nicho} onChange={(e) => setForm({ ...form, nicho: e.target.value })}
                      className="w-full bg-zinc-800 border border-zinc-700/50 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-600/50" />
                  </div>
                  <div>
                    <label className="text-[11px] text-zinc-500 mb-1.5 block">Origem</label>
                    <select value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}
                      className="w-full bg-zinc-800 border border-zinc-700/50 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-600/50">
                      {allSourceOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-[11px] text-zinc-500 mb-1.5 block">Etapa</label>
                    <select value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value })}
                      className="w-full bg-zinc-800 border border-zinc-700/50 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-600/50">
                      {STAGES.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <button onClick={handleSave} disabled={saving}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50">
                    <Save size={14} />{saving ? 'Salvando...' : 'Salvar'}
                  </button>
                  <button onClick={onClose} className="flex items-center gap-2 text-zinc-400 hover:text-zinc-200 text-sm px-4 py-2 rounded-lg transition-colors">
                    <X size={14} />Cancelar
                  </button>
                </div>
              </div>
            ) : tab === 'historico' ? (
              <div className="px-4 py-3 space-y-2 min-h-[300px]">
                {(!detail?.messages || detail.messages.length === 0) && (
                  <div className="flex flex-col items-center justify-center h-64 text-zinc-600">
                    <MessageSquare size={32} className="mb-2" />
                    <p className="text-sm">Nenhuma mensagem</p>
                  </div>
                )}
                {detail?.messages?.map((msg, i) => {
                  const isOut = msg.direction === 'outbound';
                  const showDate = i === 0 || formatDate(msg.created_at) !== formatDate(detail.messages[i - 1].created_at);
                  return (
                    <div key={msg.id}>
                      {showDate && (
                        <div className="flex justify-center my-3">
                          <span className="text-[10px] text-zinc-600 bg-zinc-800 px-3 py-1 rounded-full">{formatDate(msg.created_at)}</span>
                        </div>
                      )}
                      <div className={`flex ${isOut ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] rounded-xl px-3 py-2 ${isOut ? 'bg-green-900/40 border border-green-800/30 text-green-100' : 'bg-zinc-800 border border-zinc-700/50 text-zinc-200'}`}>
                          {msg.sent_by && isOut && <p className="text-[10px] text-green-500/70 mb-0.5 font-medium">{msg.sent_by}</p>}
                          <p className="text-xs leading-relaxed whitespace-pre-wrap break-words">{msg.body || `[${msg.type}]`}</p>
                          <p className={`text-[10px] mt-1 ${isOut ? 'text-green-600/60' : 'text-zinc-600'} text-right`}>{formatTime(msg.created_at)}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>
            ) : (
              /* Notas SDR */
              <div className="p-5">
                <div className="flex items-center gap-1.5 mb-3">
                  <FileText size={14} className="text-indigo-400" />
                  <span className="text-xs font-semibold text-zinc-300">Notas do Agente SDR</span>
                </div>
                {detail?.contact?.observacoes_sdr ? (
                  <div className="bg-zinc-800/50 border border-zinc-700/30 rounded-lg p-4">
                    <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">{detail.contact.observacoes_sdr}</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-zinc-600">
                    <FileText size={32} className="mb-2" />
                    <p className="text-sm">Nenhuma nota registrada</p>
                  </div>
                )}
                <p className="text-[10px] text-zinc-600 mt-3">Notas geradas automaticamente pelo agente de IA durante a conversa.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────

export default function CRMPage() {
  const [data, setData] = useState<Record<string, Lead[]>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [sortBy, setSortBy] = useState('recent');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [dragData, setDragData] = useState<{ leadId: number; fromStage: string } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const res = await fetch('/api/crm');
      const json = await res.json();
      setData(json);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Erro ao carregar CRM:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Auto-refresh a cada 30s
  useEffect(() => {
    const interval = setInterval(() => fetchData(true), 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  function handleDragStart(e: React.DragEvent, leadId: number, fromStage: string) {
    setDragData({ leadId, fromStage });
    e.dataTransfer.effectAllowed = 'move';
  }

  async function handleDrop(toStage: string) {
    if (!dragData || dragData.fromStage === toStage) { setDragData(null); return; }
    const newData = { ...data };
    const fromLeads = [...(newData[dragData.fromStage] || [])];
    const leadIndex = fromLeads.findIndex((l) => l.id === dragData.leadId);
    if (leadIndex === -1) { setDragData(null); return; }
    const [lead] = fromLeads.splice(leadIndex, 1);
    newData[dragData.fromStage] = fromLeads;
    newData[toStage] = [{ ...lead, stage: toStage }, ...(newData[toStage] || [])];
    setData(newData);
    setDragData(null);
    try {
      const res = await fetch('/api/crm', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ contactId: lead.id, newStage: toStage }) });
      if (!res.ok) fetchData();
    } catch { fetchData(); }
  }

  const getFilteredLeads = useCallback((stageKey: string): Lead[] => {
    let leads = data[stageKey] || [];

    // Filtro de busca
    if (search.trim()) {
      const q = search.toLowerCase();
      leads = leads.filter((l) =>
        (l.nome && l.nome.toLowerCase().includes(q)) ||
        (l.wa_contact_name && l.wa_contact_name.toLowerCase().includes(q)) ||
        (l.telefone && l.telefone.includes(q)) ||
        (l.nicho && l.nicho.toLowerCase().includes(q)) ||
        (l.email && l.email.toLowerCase().includes(q))
      );
    }

    // Filtro de origem
    if (sourceFilter) {
      leads = leads.filter((l) => l.source === sourceFilter);
    }

    // Ordenacao
    leads = [...leads].sort((a, b) => {
      if (sortBy === 'oldest') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      if (sortBy === 'messages') return Number(b.message_count) - Number(a.message_count);
      if (sortBy === 'activity') {
        const aTime = new Date(a.last_message_at || a.created_at).getTime();
        const bTime = new Date(b.last_message_at || b.created_at).getTime();
        return bTime - aTime;
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

    return leads;
  }, [data, search, sourceFilter, sortBy]);

  const totalLeads = useMemo(() => STAGES.reduce((sum, s) => sum + (data[s.key]?.length || 0), 0), [data]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-57px)]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={32} className="text-indigo-500 animate-spin" />
          <p className="text-sm text-zinc-500">Carregando CRM...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      {/* Header */}
      <div className="flex flex-col gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <BarChart3 size={16} className="text-indigo-400" />
            <h1 className="text-sm font-semibold text-zinc-100">CRM</h1>
            <span className="text-xs text-zinc-600">{totalLeads} leads</span>
          </div>

          {/* Stats */}
          <div className="flex-1 hidden md:block">
            <StatsBar data={data} />
          </div>

          <div className="flex items-center gap-2 ml-auto">
            {/* Filtros toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${showFilters ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-600/30' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'}`}
            >
              <Filter size={12} />
              Filtros
              {sourceFilter && <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />}
            </button>

            {/* Refresh */}
            <button
              onClick={() => fetchData()}
              disabled={refreshing}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors disabled:opacity-50"
              title={`Atualizado ${timeAgo(lastRefresh.toISOString())}`}
            >
              <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
            </button>

            {/* Search */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input type="text" placeholder="Buscar..." value={search} onChange={(e) => setSearch(e.target.value)}
                className="w-48 bg-zinc-800/50 border border-zinc-700/50 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-600/50 focus:ring-1 focus:ring-indigo-600/20 transition-colors" />
              {search && (
                <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-zinc-700 text-zinc-500">
                  <X size={12} />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Filtros expandidos */}
        {showFilters && (
          <div className="flex items-center gap-3 pt-1 pb-1">
            <div className="flex items-center gap-2">
              <label className="text-[10px] text-zinc-500 uppercase tracking-wider">Origem:</label>
              <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}
                className="bg-zinc-800 border border-zinc-700/50 rounded-lg px-2.5 py-1 text-xs text-zinc-300 focus:outline-none focus:border-indigo-600/50">
                {SOURCE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-[10px] text-zinc-500 uppercase tracking-wider">Ordenar:</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
                className="bg-zinc-800 border border-zinc-700/50 rounded-lg px-2.5 py-1 text-xs text-zinc-300 focus:outline-none focus:border-indigo-600/50">
                {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>

            {(sourceFilter || sortBy !== 'recent') && (
              <button
                onClick={() => { setSourceFilter(''); setSortBy('recent'); }}
                className="text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Limpar filtros
              </button>
            )}
          </div>
        )}

        {/* Stats mobile */}
        <div className="block md:hidden">
          <StatsBar data={data} />
        </div>
      </div>

      {/* Kanban */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        <div className="flex gap-3 p-4 h-full min-w-max">
          {STAGES.map((stage) => (
            <KanbanColumn
              key={stage.key}
              stage={stage}
              leads={getFilteredLeads(stage.key)}
              totalLeads={totalLeads}
              onDragStart={handleDragStart}
              onDrop={handleDrop}
              onCardClick={setSelectedLead}
            />
          ))}
        </div>
      </div>

      {selectedLead && (
        <LeadModal lead={selectedLead} onClose={() => setSelectedLead(null)} onUpdate={fetchData} />
      )}
    </div>
  );
}
