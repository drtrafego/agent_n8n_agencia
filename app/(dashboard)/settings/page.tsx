import { Settings, Webhook, Phone, Bot } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-zinc-100">Configurações</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Configure a integração com o WhatsApp Business
        </p>
      </div>

      <div className="space-y-4">
        {/* Webhook */}
        <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Webhook size={16} className="text-indigo-400" />
            <h2 className="text-sm font-semibold text-zinc-200">
              Webhook da Meta
            </h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-zinc-500">
                URL do Webhook (configurar no Meta Developers)
              </label>
              <code className="block rounded-lg bg-zinc-800 px-3 py-2 text-xs text-zinc-300 break-all">
                {process.env.NEXT_PUBLIC_APP_URL || 'https://seu-dominio.com'}
                /api/whatsapp/webhook
              </code>
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-500">
                Verify Token
              </label>
              <code className="block rounded-lg bg-zinc-800 px-3 py-2 text-xs text-zinc-500">
                {process.env.META_WEBHOOK_VERIFY_TOKEN
                  ? '••••••••••••'
                  : 'Não configurado'}
              </code>
            </div>
          </div>
        </section>

        {/* Número */}
        <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Phone size={16} className="text-indigo-400" />
            <h2 className="text-sm font-semibold text-zinc-200">
              Número WhatsApp
            </h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-zinc-500">
                Phone Number ID
              </label>
              <code className="block rounded-lg bg-zinc-800 px-3 py-2 text-xs text-zinc-500">
                {process.env.META_PHONE_NUMBER_ID
                  ? '••••••••••••'
                  : 'Não configurado'}
              </code>
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-500">
                WABA ID
              </label>
              <code className="block rounded-lg bg-zinc-800 px-3 py-2 text-xs text-zinc-500">
                {process.env.META_WABA_ID ? '••••••••••••' : 'Não configurado'}
              </code>
            </div>
          </div>
        </section>

        {/* n8n */}
        <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Bot size={16} className="text-indigo-400" />
            <h2 className="text-sm font-semibold text-zinc-200">Bot / n8n</h2>
          </div>
          <div>
            <label className="mb-1 block text-xs text-zinc-500">
              URL do Webhook n8n
            </label>
            <code className="block rounded-lg bg-zinc-800 px-3 py-2 text-xs text-zinc-300 break-all">
              {process.env.N8N_WEBHOOK_URL || 'Não configurado'}
            </code>
          </div>
          <p className="mt-3 text-xs text-zinc-600">
            O bot receberá mensagens automaticamente quando bot_active = true em cada conversa.
          </p>
        </section>

        {/* Status */}
        <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Settings size={16} className="text-indigo-400" />
            <h2 className="text-sm font-semibold text-zinc-200">Status das variáveis</h2>
          </div>
          <div className="space-y-2">
            {[
              ['META_WHATSAPP_TOKEN', process.env.META_WHATSAPP_TOKEN],
              ['META_PHONE_NUMBER_ID', process.env.META_PHONE_NUMBER_ID],
              ['META_APP_SECRET', process.env.META_APP_SECRET],
              ['META_WEBHOOK_VERIFY_TOKEN', process.env.META_WEBHOOK_VERIFY_TOKEN],
              ['DATABASE_URL', process.env.DATABASE_URL],
              ['N8N_WEBHOOK_URL', process.env.N8N_WEBHOOK_URL],
              ['BLOB_READ_WRITE_TOKEN', process.env.BLOB_READ_WRITE_TOKEN],
            ].map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <code className="text-xs text-zinc-400">{key}</code>
                <span
                  className={`text-xs font-medium ${value ? 'text-emerald-400' : 'text-red-400'}`}
                >
                  {value ? '✓ Configurado' : '✗ Ausente'}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
