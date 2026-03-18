-- ============================================================
-- agent-n8n-agencia: Setup completo do banco de dados
-- Executar no Supabase SQL Editor
-- ============================================================

-- 1. Extensão pgvector para embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Tabela de documentos para RAG (treinamento do bot via Google Drive)
CREATE TABLE IF NOT EXISTS documents (
  id bigserial PRIMARY KEY,
  content text,
  metadata jsonb,
  embedding vector(768)  -- Google Gemini embeddings = 768 dimensões
);

-- Índice para busca por similaridade
CREATE INDEX IF NOT EXISTS documents_embedding_idx
  ON documents USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Índice para filtro por file_id (usado no delete antes de re-ingestão)
CREATE INDEX IF NOT EXISTS documents_metadata_file_id_idx
  ON documents ((metadata->>'file_id'));

-- 3. Função de match para o vector store do n8n/Supabase
CREATE OR REPLACE FUNCTION match_documents(
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
  FROM documents d
  WHERE d.metadata @> filter
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 4. Tabela de contatos (substitui Google Sheets)
CREATE TABLE IF NOT EXISTS contacts (
  id bigserial PRIMARY KEY,
  telefone varchar(20) UNIQUE NOT NULL,
  nome varchar(255),
  email varchar(255),
  site varchar(500),
  segmento varchar(255),
  observacoes_sdr text,
  status varchar(50) DEFAULT 'novo',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Índice para busca por telefone (usado antes de chamar o agente)
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

-- 5. Tabela de histórico de chat (n8n cria automaticamente, mas garantimos a estrutura)
CREATE TABLE IF NOT EXISTS n8n_chat_histories (
  id serial PRIMARY KEY,
  session_id varchar(255) NOT NULL,
  message jsonb NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_histories_session_idx
  ON n8n_chat_histories (session_id);

-- 6. RLS (Row Level Security) - opcional mas recomendado no Supabase
-- Descomente se quiser habilitar
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE n8n_chat_histories ENABLE ROW LEVEL SECURITY;

-- Pronto! Tabelas criadas:
-- documents        → RAG/vector store (treinamento via Drive)
-- contacts         → Dados dos contatos (substitui Google Sheets)
-- n8n_chat_histories → Memória de chat do agente
