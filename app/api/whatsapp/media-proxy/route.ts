import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const blobUrl = req.nextUrl.searchParams.get('url');
  if (!blobUrl || !blobUrl.includes('blob.vercel-storage.com')) {
    return NextResponse.json({ error: 'URL inválida' }, { status: 400 });
  }

  try {
    const token = process.env.BLOB_READ_WRITE_TOKEN;
    if (!token) {
      return NextResponse.json(
        { error: 'BLOB_READ_WRITE_TOKEN não configurado' },
        { status: 500 }
      );
    }

    // Fetch the private blob using the token
    const res = await fetch(blobUrl, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Blob retornou ${res.status}` },
        { status: res.status }
      );
    }

    const contentType =
      res.headers.get('content-type') || 'application/octet-stream';
    const body = res.body;

    return new NextResponse(body, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400, immutable',
      },
    });
  } catch {
    return NextResponse.json({ error: 'Falha ao buscar mídia' }, { status: 500 });
  }
}
