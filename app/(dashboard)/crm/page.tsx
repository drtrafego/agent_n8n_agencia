'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search,
  X,
  MessageSquare,
  Clock,
  GripVertical,
  User,
  Phone,
  FileText,
  ChevronRight,
  Loader2,
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
  wa_contact_name: string | null;
  wa_phone: string | null;
  last_message: string | null;
  last_message_at: string | null;
  message_count: string;
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
  };
  messages: Message[];
}

// ─── Constants ───────────────────────────────────────────────────────

const STAGES = [
  { key: 'novo', label: 'Novo', color: 'bg-zinc-600', badgeBg: 'bg-zinc-700', textColor: 'text-zinc-300', borderColor: 'border-zinc-700' },
  { key: 'qualificando', label: 'Qualificando', color: 'bg-blue-600', badgeBg: 'bg-blue-900/50', textColor: 'text-blue-300', borderColor: 'border-blue-800/50' },
  { key: 'interesse', label: 'Interesse', color: 'bg-yellow-600', badgeBg: 'bg-yellow-900/50', textColor: 'text-yellow-300', borderColor: 'border-yellow-800/50' },
  { key: 'agendado', label: 'Agendado', color: 'bg-green-600', badgeBg: 'bg-green-900/50', textColor: 'text-green-300', borderColor: 'border-green-800/50' },
  { key: 'convertido', label: 'Convertido', color: 'bg-purple-600', badgeBg: 'bg-purple-900/50', textColor: 'text-purple-300', borderColor: 'border-purple-800/50' },
  { key: 'sem_interesse', label: 'Sem Interesse', color: 'bg-red-600', badgeBg: 'bg-red-900/50', textColor: 'text-red-300', borderColor: 'border-red-800/50' },
] as const;

// ─── Helpers ─────────────────────────────────────────────────────────

function timeAgo(dateStr: string): string {
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
  const diffM = Math.floor(diffD / 30);
  return `${diffM}mo`;
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function truncate(str: string | null, len: number): string {
  if (!str) return '';
  return str.length > len ? str.slice(0, len) + '...' : str;
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

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, lead.id, lead.stage)}
      onClick={() => onClick(lead)}
      className="group bg-zinc-800/80 hover:bg-zinc-800 border border-zinc-700/50 hover:border-zinc-600 rounded-lg p-3 cursor-pointer transition-all duration-150 hover:shadow-lg hover:shadow-black/20"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <GripVertical size={14} className="text-zinc-600 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
          <span className="text-sm font-medium text-zinc-100 truncate">
            {displayName}
          </span>
        </div>
        <ChevronRight size={14} className="text-zinc-600 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {lead.nicho && (
        <span className="inline-block text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-900/40 text-indigo-300 border border-indigo-800/30 mb-2">
          {lead.nicho}
        </span>
      )}

      {lead.last_message && (
        <p className="text-xs text-zinc-500 mb-2 leading-relaxed">
          {truncate(lead.last_message, 80)}
        </p>
      )}

      <div className="flex items-center gap-3 text-[10px] text-zinc-600">
        <span className="flex items-center gap-1">
          <Clock size={10} />
          {timeAgo(lead.created_at)}
        </span>
        <span className="flex items-center gap-1">
          <MessageSquare size={10} />
          {lead.message_count}
        </span>
      </div>
    </div>
  );
}

// ─── Column ──────────────────────────────────────────────────────────

function KanbanColumn({
  stage,
  leads,
  onDragStart,
  onDrop,
  onCardClick,
}: {
  stage: (typeof STAGES)[number];
  leads: Lead[];
  onDragStart: (e: React.DragEvent, leadId: number, fromStage: string) => void;
  onDrop: (stageKey: string) => void;
  onCardClick: (lead: Lead) => void;
}) {
  const [isDragOver, setIsDragOver] = useState(false);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave() {
    setIsDragOver(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    onDrop(stage.key);
  }

  return (
    <div
      className={`flex flex-col min-w-[280px] w-[280px] shrink-0 rounded-xl transition-colors duration-150 ${
        isDragOver ? 'bg-zinc-800/50' : 'bg-zinc-900/50'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-3">
        <div className={`w-2 h-2 rounded-full ${stage.color}`} />
        <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
          {stage.label}
        </h3>
        <span className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full ${stage.badgeBg} ${stage.textColor}`}>
          {leads.length}
        </span>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-2 min-h-[100px]">
        {leads.length === 0 && (
          <div className="flex items-center justify-center h-20 text-xs text-zinc-700 border border-dashed border-zinc-800 rounded-lg">
            Nenhum lead
          </div>
        )}
        {leads.map((lead) => (
          <LeadCard
            key={lead.id}
            lead={lead}
            onDragStart={onDragStart}
            onClick={onCardClick}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Slide-over Conversation Panel ───────────────────────────────────

function ConversationPanel({
  lead,
  onClose,
}: {
  lead: Lead;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/crm/lead/${lead.id}`)
      .then((res) => res.json())
      .then((data) => {
        setDetail(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [lead.id]);

  useEffect(() => {
    if (detail?.messages?.length) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [detail]);

  const displayName = lead.nome || lead.wa_contact_name || lead.telefone || 'Sem nome';
  const stageInfo = STAGES.find((s) => s.key === lead.stage) || STAGES[0];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-zinc-900 border-l border-zinc-800 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800 bg-zinc-900/95">
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <X size={18} />
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-zinc-100 truncate">
                {displayName}
              </h2>
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${stageInfo.badgeBg} ${stageInfo.textColor}`}>
                {stageInfo.label}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              {lead.telefone && (
                <span className="flex items-center gap-1 text-[11px] text-zinc-500">
                  <Phone size={10} />
                  {lead.telefone}
                </span>
              )}
              {lead.nicho && (
                <span className="text-[11px] text-indigo-400">
                  {lead.nicho}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Observacoes */}
        {lead.observacoes_sdr && (
          <div className="px-4 py-2 border-b border-zinc-800 bg-zinc-800/30">
            <div className="flex items-center gap-1.5 mb-1">
              <FileText size={11} className="text-zinc-500" />
              <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
                Notas SDR
              </span>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              {lead.observacoes_sdr}
            </p>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <Loader2 size={24} className="text-zinc-600 animate-spin" />
            </div>
          )}

          {!loading && (!detail?.messages || detail.messages.length === 0) && (
            <div className="flex flex-col items-center justify-center h-full text-zinc-600">
              <MessageSquare size={32} className="mb-2" />
              <p className="text-sm">Nenhuma mensagem</p>
            </div>
          )}

          {!loading &&
            detail?.messages?.map((msg, i) => {
              const isOutbound = msg.direction === 'outbound';
              const showDate =
                i === 0 ||
                formatDate(msg.created_at) !==
                  formatDate(detail.messages[i - 1].created_at);

              return (
                <div key={msg.id}>
                  {showDate && (
                    <div className="flex justify-center my-3">
                      <span className="text-[10px] text-zinc-600 bg-zinc-800 px-3 py-1 rounded-full">
                        {formatDate(msg.created_at)}
                      </span>
                    </div>
                  )}
                  <div
                    className={`flex ${isOutbound ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-xl px-3 py-2 ${
                        isOutbound
                          ? 'bg-green-900/40 border border-green-800/30 text-green-100'
                          : 'bg-zinc-800 border border-zinc-700/50 text-zinc-200'
                      }`}
                    >
                      {msg.sent_by && isOutbound && (
                        <p className="text-[10px] text-green-500/70 mb-0.5 font-medium">
                          {msg.sent_by}
                        </p>
                      )}
                      <p className="text-xs leading-relaxed whitespace-pre-wrap break-words">
                        {msg.body || `[${msg.type}]`}
                      </p>
                      <p
                        className={`text-[10px] mt-1 ${
                          isOutbound ? 'text-green-600/60' : 'text-zinc-600'
                        } text-right`}
                      >
                        {formatTime(msg.created_at)}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          <div ref={messagesEndRef} />
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
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [dragData, setDragData] = useState<{ leadId: number; fromStage: string } | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/crm');
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('Erro ao carregar CRM:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function handleDragStart(e: React.DragEvent, leadId: number, fromStage: string) {
    setDragData({ leadId, fromStage });
    e.dataTransfer.effectAllowed = 'move';
    // Make the drag ghost semi-transparent
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = '0.5';
      setTimeout(() => {
        (e.currentTarget as HTMLElement).style.opacity = '1';
      }, 0);
    }
  }

  async function handleDrop(toStage: string) {
    if (!dragData) return;
    if (dragData.fromStage === toStage) {
      setDragData(null);
      return;
    }

    // Optimistic update
    const newData = { ...data };
    const fromLeads = [...(newData[dragData.fromStage] || [])];
    const leadIndex = fromLeads.findIndex((l) => l.id === dragData.leadId);
    if (leadIndex === -1) {
      setDragData(null);
      return;
    }

    const [lead] = fromLeads.splice(leadIndex, 1);
    const updatedLead = { ...lead, stage: toStage };
    newData[dragData.fromStage] = fromLeads;
    newData[toStage] = [updatedLead, ...(newData[toStage] || [])];
    setData(newData);
    setDragData(null);

    // API call
    try {
      const res = await fetch('/api/crm', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contactId: lead.id, newStage: toStage }),
      });
      if (!res.ok) {
        // Revert on error
        fetchData();
      }
    } catch {
      fetchData();
    }
  }

  function handleCardClick(lead: Lead) {
    setSelectedLead(lead);
  }

  // Filter leads by search
  function getFilteredLeads(stageKey: string): Lead[] {
    const leads = data[stageKey] || [];
    if (!search.trim()) return leads;
    const q = search.toLowerCase();
    return leads.filter(
      (l) =>
        (l.nome && l.nome.toLowerCase().includes(q)) ||
        (l.wa_contact_name && l.wa_contact_name.toLowerCase().includes(q)) ||
        (l.telefone && l.telefone.includes(q))
    );
  }

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

  const totalLeads = STAGES.reduce(
    (sum, s) => sum + (data[s.key]?.length || 0),
    0
  );

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      {/* Top bar */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2">
          <User size={16} className="text-indigo-400" />
          <h1 className="text-sm font-semibold text-zinc-100">CRM</h1>
          <span className="text-xs text-zinc-600">{totalLeads} leads</span>
        </div>

        <div className="flex-1 max-w-sm ml-auto">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
            />
            <input
              type="text"
              placeholder="Buscar por nome ou telefone..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-zinc-800/50 border border-zinc-700/50 rounded-lg pl-9 pr-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-600/50 focus:ring-1 focus:ring-indigo-600/20 transition-colors"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-zinc-700 text-zinc-500"
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Kanban board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        <div className="flex gap-3 p-4 h-full min-w-max">
          {STAGES.map((stage) => (
            <KanbanColumn
              key={stage.key}
              stage={stage}
              leads={getFilteredLeads(stage.key)}
              onDragStart={handleDragStart}
              onDrop={handleDrop}
              onCardClick={handleCardClick}
            />
          ))}
        </div>
      </div>

      {/* Conversation slide-over */}
      {selectedLead && (
        <ConversationPanel
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
        />
      )}
    </div>
  );
}
