'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Send, Paperclip, Image as ImageIcon, FileText, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MessageInputProps {
  conversationId: string;
  disabled?: boolean;
  onMessageSent?: () => void;
}

type AttachType = 'image' | 'document' | null;

export function MessageInput({
  conversationId,
  disabled,
  onMessageSent,
}: MessageInputProps) {
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [attachPreview, setAttachPreview] = useState<{
    file: File;
    url: string;
    type: AttachType;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function handleSend() {
    if (sending || (!text.trim() && !attachPreview)) return;
    setSending(true);

    try {
      let msgType: 'text' | 'image' | 'document' = 'text';
      let mediaUrl: string | undefined;
      let filename: string | undefined;

      if (attachPreview) {
        // Upload do arquivo
        const form = new FormData();
        form.append('file', attachPreview.file);
        const uploadRes = await fetch('/api/whatsapp/media/upload', {
          method: 'POST',
          body: form,
        });
        if (!uploadRes.ok) throw new Error('Falha no upload');
        const uploaded = await uploadRes.json();
        mediaUrl = uploaded.url;
        filename = uploaded.filename;
        msgType = attachPreview.type === 'image' ? 'image' : 'document';
      }

      const res = await fetch('/api/whatsapp/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversationId,
          type: msgType,
          body: text.trim() || undefined,
          mediaUrl,
          filename,
          sentBy: 'human',
        }),
      });

      if (!res.ok) throw new Error('Falha ao enviar');

      setText('');
      setAttachPreview(null);
      onMessageSent?.();
    } catch (err) {
      console.error('Erro ao enviar mensagem:', err);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const isImage = file.type.startsWith('image/');
    const url = URL.createObjectURL(file);
    setAttachPreview({ file, url, type: isImage ? 'image' : 'document' });
    setShowAttachMenu(false);

    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function openFilePicker(accept: string) {
    if (fileInputRef.current) {
      fileInputRef.current.accept = accept;
      fileInputRef.current.click();
    }
    setShowAttachMenu(false);
  }

  return (
    <div className="border-t border-zinc-800 bg-zinc-950 p-3">
      {/* Preview do anexo */}
      {attachPreview && (
        <div className="mb-2 flex items-center gap-2 rounded-lg bg-zinc-800/60 px-3 py-2">
          {attachPreview.type === 'image' ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={attachPreview.url}
              alt="Preview"
              className="h-12 w-12 rounded object-cover"
            />
          ) : (
            <FileText size={20} className="text-zinc-400" />
          )}
          <span className="flex-1 truncate text-xs text-zinc-300">
            {attachPreview.file.name}
          </span>
          <button
            onClick={() => setAttachPreview(null)}
            className="text-zinc-500 hover:text-zinc-300"
          >
            <X size={16} />
          </button>
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Botão de anexo */}
        <div className="relative">
          <button
            onClick={() => setShowAttachMenu((v) => !v)}
            disabled={disabled || sending}
            className="flex h-9 w-9 items-center justify-center rounded-full text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 disabled:opacity-50"
          >
            <Paperclip size={18} />
          </button>

          {showAttachMenu && (
            <div className="absolute bottom-11 left-0 z-10 flex flex-col gap-1 rounded-xl bg-zinc-800 p-2 shadow-xl">
              <button
                onClick={() => openFilePicker('image/*')}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
              >
                <ImageIcon size={16} />
                Imagem
              </button>
              <button
                onClick={() => openFilePicker('.pdf,application/pdf')}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
              >
                <FileText size={16} />
                PDF
              </button>
            </div>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Digite uma mensagem..."
          disabled={disabled || sending}
          rows={1}
          className={cn(
            'flex-1 resize-none rounded-2xl bg-zinc-800 px-4 py-2 text-sm text-zinc-100',
            'placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-600',
            'max-h-32 min-h-[36px] overflow-y-auto disabled:opacity-50'
          )}
          style={{ height: 'auto' }}
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, 128) + 'px';
          }}
        />

        {/* Botão enviar */}
        <button
          onClick={handleSend}
          disabled={disabled || sending || (!text.trim() && !attachPreview)}
          className={cn(
            'flex h-9 w-9 items-center justify-center rounded-full transition-colors',
            'bg-indigo-600 text-white hover:bg-indigo-500',
            'disabled:opacity-40 disabled:cursor-not-allowed'
          )}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
