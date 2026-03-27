const GRAPH_API_VERSION = 'v21.0';

function getBaseUrl() {
  return `https://graph.facebook.com/${GRAPH_API_VERSION}/${process.env.META_PHONE_NUMBER_ID}`;
}

function getHeaders() {
  return {
    Authorization: `Bearer ${process.env.META_WHATSAPP_TOKEN}`,
    'Content-Type': 'application/json',
  };
}

type MetaResponse<T = unknown> = {
  success: boolean;
  data?: T;
  error?: string;
};

async function metaFetch<T>(
  url: string,
  options: RequestInit
): Promise<MetaResponse<T>> {
  try {
    const res = await fetch(url, options);
    const json = await res.json();
    if (!res.ok) {
      return { success: false, error: json.error?.message || 'Meta API error' };
    }
    return { success: true, data: json };
  } catch (err) {
    return { success: false, error: String(err) };
  }
}

export async function sendTextMessage(to: string, text: string) {
  return metaFetch(`${getBaseUrl()}/messages`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
      messaging_product: 'whatsapp',
      to,
      type: 'text',
      text: { body: text },
    }),
  });
}

export async function sendImageMessage(
  to: string,
  imageUrl: string,
  caption?: string
) {
  return metaFetch(`${getBaseUrl()}/messages`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
      messaging_product: 'whatsapp',
      to,
      type: 'image',
      image: { link: imageUrl, caption },
    }),
  });
}

export async function sendDocumentMessage(
  to: string,
  docUrl: string,
  filename: string
) {
  return metaFetch(`${getBaseUrl()}/messages`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
      messaging_product: 'whatsapp',
      to,
      type: 'document',
      document: { link: docUrl, filename },
    }),
  });
}

export async function downloadMedia(mediaId: string): Promise<Buffer | null> {
  try {
    // 1. Buscar URL da mídia
    const urlRes = await fetch(
      `https://graph.facebook.com/${GRAPH_API_VERSION}/${mediaId}`,
      {
        headers: {
          Authorization: `Bearer ${process.env.META_WHATSAPP_TOKEN}`,
        },
      }
    );
    if (!urlRes.ok) return null;
    const { url } = await urlRes.json();

    // 2. Baixar binário
    const mediaRes = await fetch(url, {
      headers: {
        Authorization: `Bearer ${process.env.META_WHATSAPP_TOKEN}`,
      },
    });
    if (!mediaRes.ok) return null;
    return Buffer.from(await mediaRes.arrayBuffer());
  } catch {
    return null;
  }
}

export async function markAsRead(waMessageId: string) {
  return metaFetch(`${getBaseUrl()}/messages`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
      messaging_product: 'whatsapp',
      status: 'read',
      message_id: waMessageId,
    }),
  });
}
