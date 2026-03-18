import postgres from 'postgres';
import { config } from 'dotenv';

config({ path: '.env.local' });

const sql = postgres(
  process.env.WHATSAPP_DATABASE_URL || process.env.POSTGRES_URL || '',
  { max: 1 }
);

async function createTables() {
  console.log('Criando tabelas WhatsApp...');

  await sql`
    CREATE TABLE IF NOT EXISTS wa_contacts (
      id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      wa_id       TEXT UNIQUE NOT NULL,
      name        TEXT,
      phone       TEXT,
      avatar_url  TEXT,
      created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
      updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
    )
  `;
  console.log('✓ wa_contacts');

  await sql`
    CREATE TABLE IF NOT EXISTS wa_conversations (
      id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      contact_id       UUID NOT NULL REFERENCES wa_contacts(id),
      status           TEXT NOT NULL DEFAULT 'open',
      bot_active       BOOLEAN NOT NULL DEFAULT TRUE,
      unread_count     INTEGER NOT NULL DEFAULT 0,
      last_message     TEXT,
      last_message_at  TIMESTAMP,
      created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
      updated_at       TIMESTAMP NOT NULL DEFAULT NOW()
    )
  `;
  console.log('✓ wa_conversations');

  await sql`
    CREATE TABLE IF NOT EXISTS wa_messages (
      id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      conversation_id   UUID NOT NULL REFERENCES wa_conversations(id),
      contact_id        UUID REFERENCES wa_contacts(id),
      wa_message_id     TEXT UNIQUE,
      direction         TEXT NOT NULL,
      type              TEXT NOT NULL,
      body              TEXT,
      media_url         TEXT,
      media_mime_type   TEXT,
      media_filename    TEXT,
      status            TEXT NOT NULL DEFAULT 'received',
      sent_by           TEXT,
      created_at        TIMESTAMP NOT NULL DEFAULT NOW()
    )
  `;
  console.log('✓ wa_messages');

  await sql`
    CREATE TABLE IF NOT EXISTS wa_media_files (
      id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      message_id  UUID NOT NULL REFERENCES wa_messages(id),
      wa_media_id TEXT,
      url         TEXT,
      mime_type   TEXT,
      filename    TEXT,
      size_bytes  INTEGER,
      created_at  TIMESTAMP NOT NULL DEFAULT NOW()
    )
  `;
  console.log('✓ wa_media_files');

  await sql`
    CREATE TABLE IF NOT EXISTS wa_webhook_logs (
      id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      payload    JSONB,
      status     TEXT NOT NULL DEFAULT 'processed',
      error_msg  TEXT,
      created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
  `;
  console.log('✓ wa_webhook_logs');

  console.log('\nTodas as tabelas criadas com sucesso!');
  await sql.end();
}

createTables().catch((err) => {
  console.error('Erro:', err);
  process.exit(1);
});
