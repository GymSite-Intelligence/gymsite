-- Migration: sessions + messages — persistência completa de conversas

-- Renomeia chat_sessions para sessions (se existir) ou cria nova
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_sessions') THEN
    ALTER TABLE chat_sessions RENAME TO sessions;
  ELSE
    CREATE TABLE sessions (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
      intencao TEXT,
      slots JSONB DEFAULT '{}',
      relatorio_id UUID REFERENCES relatorios(id),
      status TEXT DEFAULT 'coletando_slots'
        CHECK (status IN ('coletando_slots', 'pipeline_rodando', 'respondendo', 'encerrado')),
      messages JSONB DEFAULT '[]',
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW()
    );
  END IF;
END $$;

-- Tabela de mensagens persistentes
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  attachments JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_relatorio ON sessions(relatorio_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp DESC);

COMMENT ON TABLE sessions IS 'Sessões conversacionais do GymSite Agent.';
COMMENT ON TABLE messages IS 'Mensagens persistentes do chat do GymSite Agent.';
