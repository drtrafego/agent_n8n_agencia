import { NextRequest, NextResponse } from 'next/server';
import { put } from '@vercel/blob';

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get('file') as File | null;

    if (!file) {
      return NextResponse.json({ error: 'Arquivo não encontrado' }, { status: 400 });
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const filename = file.name || `upload-${Date.now()}`;

    const blob = await put(`whatsapp/uploads/${Date.now()}-${filename}`, buffer, {
      access: 'public',
      contentType: file.type || 'application/octet-stream',
    });

    return NextResponse.json({ url: blob.url, filename });
  } catch (err) {
    console.error('Erro no upload:', err);
    return NextResponse.json({ error: 'Erro ao fazer upload' }, { status: 500 });
  }
}
