import { NextRequest, NextResponse } from 'next/server';
import { getDownloadUrl } from '@vercel/blob';

export async function GET(req: NextRequest) {
  const blobUrl = req.nextUrl.searchParams.get('url');
  if (!blobUrl || !blobUrl.includes('blob.vercel-storage.com')) {
    return NextResponse.json({ error: 'URL inválida' }, { status: 400 });
  }

  try {
    const signedUrl = await getDownloadUrl(blobUrl);
    return NextResponse.redirect(signedUrl);
  } catch {
    return NextResponse.json({ error: 'Falha ao gerar URL' }, { status: 500 });
  }
}
