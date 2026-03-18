-- ============================================
-- SQL SETUP - agent_n8n_agencia
-- Rodar no Supabase SQL Editor
-- ============================================

-- 1. Habilitar extensao pgvector (para embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Tabela de documentos (RAG / Vector Store)
-- Usada pelo Supabase Vector Store para treinamento do bot via Google Drive
CREATE TABLE IF NOT EXISTS documents (
  id bigserial PRIMARY KEY,
  content text,
  metadata jsonb,
  embedding vector(768)  -- 768 dimensoes para Google Gemini embeddings
);

-- Index para busca vetorial rapida
CREATE INDEX IF NOT EXISTS documents_embedding_idx
  ON documents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- 3. Funcao de busca por similaridade (match_documents)
-- Necessaria para o Supabase Vector Store do n8n
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(768),
  match_count int DEFAULT 5,
  filter jsonb DEFAULT '{}'
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
  FROM documents d
  WHERE d.metadata @> filter
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 4. Tabela de contatos
-- Usada por "Buscar Contato" e "observacoes_sdr"
CREATE TABLE IF NOT EXISTS contacts (
  id bigserial PRIMARY KEY,
  telefone text UNIQUE NOT NULL,
  nome text,
  email text,
  observacoes_sdr text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Index para busca rapida por telefone
CREATE INDEX IF NOT EXISTS contacts_telefone_idx ON contacts (telefone);

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS contacts_updated_at ON contacts;
CREATE TRIGGER contacts_updated_at
  BEFORE UPDATE ON contacts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- 5. Tabela de chat memory (n8n Postgres Chat Memory)
-- O n8n cria automaticamente, mas criamos para garantir
CREATE TABLE IF NOT EXISTS n8n_chat_histories (
  id serial PRIMARY KEY,
  session_id text NOT NULL,
  message jsonb NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS n8n_chat_histories_session_idx
  ON n8n_chat_histories (session_id);

-- ============================================
-- PRONTO! Tabelas criadas:
--   1. documents     -> RAG/Vector Store (treinamento via Drive)
--   2. contacts      -> Dados dos contatos
--   3. n8n_chat_histories -> Memoria de conversa do agente
-- ============================================
