-- Migration: chat_sessions — estado de conversas do GymSite Assistant
-- Objetivo: persistir slots, intenção e histórico de conversas para slot-filling

CREATE TABLE IF NOT EXISTS chat_sessions (
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

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_relatorio ON chat_sessions(relatorio_id);

COMMENT ON TABLE chat_sessions IS 'Estado de conversas do GymSite Assistant (slot-filling conversacional).';
