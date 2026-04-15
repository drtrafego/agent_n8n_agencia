-- ============================================================
-- Tabelas _es para versao espanhol do agente WhatsApp
-- Supabase project: cfjyxdqrathzremxdkoi
-- Executar no Supabase SQL Editor
-- ============================================================

-- 1. contacts_es (equivalente a contacts)
CREATE TABLE IF NOT EXISTS contacts_es (
  id bigserial PRIMARY KEY,
  telefone varchar(20) UNIQUE NOT NULL,
  nome varchar(255),
  email varchar(255),
  site varchar(500),
  segmento varchar(255),
  observacoes_sdr text,
  stage varchar(50) DEFAULT 'nuevo',
  stage_updated_at timestamptz,
  nicho varchar(255),
  source varchar(100) DEFAULT 'directo',
  followup_count integer DEFAULT 0,
  last_bot_msg_at timestamptz,
  last_lead_msg_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS contacts_es_telefone_idx ON contacts_es (telefone);
CREATE INDEX IF NOT EXISTS contacts_es_stage_idx ON contacts_es (stage);

DROP TRIGGER IF EXISTS contacts_es_updated_at ON contacts_es;
CREATE TRIGGER contacts_es_updated_at
  BEFORE UPDATE ON contacts_es
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- 2. n8n_chat_histories_es
CREATE TABLE IF NOT EXISTS n8n_chat_histories_es (
  id serial PRIMARY KEY,
  session_id varchar(255) NOT NULL,
  message jsonb NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS n8n_chat_histories_es_session_idx
  ON n8n_chat_histories_es (session_id);

-- 3. n8n_chat_auto_es
CREATE TABLE IF NOT EXISTS n8n_chat_auto_es (
  id serial PRIMARY KEY,
  session_id varchar(255) NOT NULL,
  message jsonb NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS n8n_chat_auto_es_session_idx
  ON n8n_chat_auto_es (session_id);

-- 4. n8n_chat_sdr_es
CREATE TABLE IF NOT EXISTS n8n_chat_sdr_es (
  id serial PRIMARY KEY,
  session_id varchar(255) NOT NULL,
  message jsonb NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS n8n_chat_sdr_es_session_idx
  ON n8n_chat_sdr_es (session_id);

-- 5. wa_contacts_es
CREATE TABLE IF NOT EXISTS wa_contacts_es (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  wa_id text UNIQUE NOT NULL,
  name text,
  phone text,
  avatar_url text,
  referral_source text,
  referral_ad_id text,
  referral_headline text,
  created_at timestamptz DEFAULT now() NOT NULL,
  updated_at timestamptz DEFAULT now() NOT NULL
);

-- 6. wa_conversations_es
CREATE TABLE IF NOT EXISTS wa_conversations_es (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid NOT NULL REFERENCES wa_contacts_es(id),
  status text NOT NULL DEFAULT 'open',
  bot_active boolean NOT NULL DEFAULT true,
  unread_count integer NOT NULL DEFAULT 0,
  last_message text,
  last_message_at timestamptz,
  created_at timestamptz DEFAULT now() NOT NULL,
  updated_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS wa_conversations_es_contact_idx
  ON wa_conversations_es (contact_id);

-- 7. wa_messages_es
CREATE TABLE IF NOT EXISTS wa_messages_es (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES wa_conversations_es(id),
  contact_id uuid REFERENCES wa_contacts_es(id),
  wa_message_id text UNIQUE,
  direction text NOT NULL,
  type text NOT NULL,
  body text,
  media_url text,
  media_mime_type text,
  media_filename text,
  status text NOT NULL DEFAULT 'received',
  sent_by text,
  created_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS wa_messages_es_conversation_idx
  ON wa_messages_es (conversation_id);
CREATE INDEX IF NOT EXISTS wa_messages_es_contact_idx
  ON wa_messages_es (contact_id);

-- 8. wa_media_files_es
CREATE TABLE IF NOT EXISTS wa_media_files_es (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL REFERENCES wa_messages_es(id),
  wa_media_id text,
  url text,
  mime_type text,
  filename text,
  size_bytes integer,
  created_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS wa_media_files_es_message_idx
  ON wa_media_files_es (message_id);

-- 9. wa_webhook_logs_es
CREATE TABLE IF NOT EXISTS wa_webhook_logs_es (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  payload jsonb,
  status text NOT NULL DEFAULT 'processed',
  error_msg text,
  created_at timestamptz DEFAULT now() NOT NULL
);

-- 10. wa_token_usage_logs_es
CREATE TABLE IF NOT EXISTS wa_token_usage_logs_es (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id text NOT NULL UNIQUE,
  workflow_id text NOT NULL,
  workflow_name text,
  prompt_tokens integer NOT NULL DEFAULT 0,
  completion_tokens integer NOT NULL DEFAULT 0,
  total_tokens integer NOT NULL DEFAULT 0,
  model text,
  estimated_cost_usd double precision,
  executed_at timestamptz NOT NULL,
  created_at timestamptz DEFAULT now() NOT NULL
);

-- 11. documents_es (RAG / Vector Store para espanhol)
CREATE TABLE IF NOT EXISTS documents_es (
  id bigserial PRIMARY KEY,
  content text,
  metadata jsonb,
  embedding vector(768)
);

CREATE INDEX IF NOT EXISTS documents_es_embedding_idx
  ON documents_es
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS documents_es_metadata_file_id_idx
  ON documents_es ((metadata->>'file_id'));

-- Funcao match_documents_es para busca por similaridade
CREATE OR REPLACE FUNCTION match_documents_es(
  query_embedding vector(768),
  match_count int DEFAULT 5,
  filter jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.content,
    d.metadata,
    1 - (d.embedding <=> query_embedding) AS similarity
  FROM documents_es d
  WHERE d.metadata @> filter
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================
-- PRONTO! 11 tabelas _es criadas:
--   1.  contacts_es           (stage default 'nuevo', source default 'directo')
--   2.  n8n_chat_histories_es
--   3.  n8n_chat_auto_es
--   4.  n8n_chat_sdr_es
--   5.  wa_contacts_es        (com referral_source, referral_ad_id, referral_headline)
--   6.  wa_conversations_es   (FK -> wa_contacts_es)
--   7.  wa_messages_es        (FK -> wa_conversations_es, wa_contacts_es)
--   8.  wa_media_files_es     (FK -> wa_messages_es)
--   9.  wa_webhook_logs_es
--   10. wa_token_usage_logs_es
--   11. documents_es          (vector 768, match_documents_es function)
-- ============================================================
