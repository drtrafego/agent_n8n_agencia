import { NextRequest, NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { waDb } from '@/lib/db/whatsapp';
import { mediaFiles } from '@/lib/db/whatsapp-schema';
import { downloadMedia } from '@/lib/meta/client';
import { put } from '@vercel/blob';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ mediaId: string }> }
) {
  try {
    const { mediaId } = await params;

    // Verificar se já temos a URL no banco
    const [existing] = await waDb
      .select()
      .from(mediaFiles)
      .where(eq(mediaFiles.waMediaId, mediaId))
      .limit(1);

    if (existing?.url) {
      return NextResponse.redirect(existing.url);
    }

    // Baixar da Meta e salvar no Vercel Blob
    const buffer = await downloadMedia(mediaId);
    if (!buffer) {
      return new Response('Mídia não encontrada', { status: 404 });
    }

    const blob = await put(`whatsapp/${mediaId}/media`, buffer, {
      access: 'public',
    });

    return NextResponse.redirect(blob.url);
  } catch (err) {
    console.error('Erro ao servir mídia:', err);
    return new Response('Erro interno', { status: 500 });
  }
}
