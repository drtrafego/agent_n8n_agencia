// Tipos do payload de webhook da Meta WhatsApp Cloud API

export type MetaWebhookPayload = {
  object: string;
  entry: MetaEntry[];
};

export type MetaEntry = {
  id: string;
  changes: MetaChange[];
};

export type MetaChange = {
  value: MetaChangeValue;
  field: string;
};

export type MetaChangeValue = {
  messaging_product: string;
  metadata: { display_phone_number: string; phone_number_id: string };
  contacts?: MetaContact[];
  messages?: MetaMessage[];
  statuses?: MetaStatus[];
};

export type MetaContact = {
  profile: { name: string };
  wa_id: string;
};

export type MetaReferral = {
  source_url?: string;
  source_type?: string;
  source_id?: string;
  headline?: string;
  body?: string;
};

export type MetaMessage = {
  from: string;
  id: string;
  timestamp: string;
  type: 'text' | 'image' | 'document' | 'audio' | 'video' | 'sticker';
  text?: { body: string };
  image?: { id: string; mime_type: string; sha256: string; caption?: string };
  document?: {
    id: string;
    mime_type: string;
    sha256: string;
    filename: string;
    caption?: string;
  };
  audio?: { id: string; mime_type: string };
  video?: { id: string; mime_type: string; caption?: string };
  referral?: MetaReferral;
};

export type MetaStatus = {
  id: string;
  status: 'sent' | 'delivered' | 'read' | 'failed';
  timestamp: string;
  recipient_id: string;
  errors?: Array<{ code: number; title: string }>;
};

export function parseWebhookPayload(payload: MetaWebhookPayload) {
  const value = payload.entry?.[0]?.changes?.[0]?.value;
  if (!value) return null;

  return {
    value,
    messages: value.messages || [],
    statuses: value.statuses || [],
    contacts: value.contacts || [],
  };
}

export function getMessageText(msg: MetaMessage): string {
  switch (msg.type) {
    case 'text':
      return msg.text?.body || '';
    case 'image':
      return msg.image?.caption || '';
    case 'document':
      return msg.document?.caption || '';
    case 'video':
      return msg.video?.caption || '';
    default:
      return '';
  }
}

export function getMediaId(msg: MetaMessage): string | null {
  switch (msg.type) {
    case 'image':
      return msg.image?.id || null;
    case 'document':
      return msg.document?.id || null;
    case 'audio':
      return msg.audio?.id || null;
    case 'video':
      return msg.video?.id || null;
    default:
      return null;
  }
}

export function getMimeType(msg: MetaMessage): string | null {
  switch (msg.type) {
    case 'image':
      return msg.image?.mime_type || null;
    case 'document':
      return msg.document?.mime_type || null;
    case 'audio':
      return msg.audio?.mime_type || null;
    case 'video':
      return msg.video?.mime_type || null;
    default:
      return null;
  }
}

export function getFilename(msg: MetaMessage): string | null {
  if (msg.type === 'document') return msg.document?.filename || null;
  return null;
}
