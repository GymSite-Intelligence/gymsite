-- ============================================================================
-- Apollo CRM Sync — Extensão da tabela oportunidades_prospeccao
-- Adiciona rastreamento de sync com Apollo.io para enriquecimento de leads
-- ============================================================================

-- Campos de controle de sync Apollo
ALTER TABLE oportunidades_prospeccao
  ADD COLUMN IF NOT EXISTS apollo_sync_status TEXT DEFAULT 'pending'
    CHECK (apollo_sync_status IN ('pending', 'synced', 'failed', 'skipped')),
  ADD COLUMN IF NOT EXISTS apollo_person_id TEXT,
  ADD COLUMN IF NOT EXISTS apollo_account_id TEXT,
  ADD COLUMN IF NOT EXISTS apollo_synced_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS apollo_sync_error TEXT,
  ADD COLUMN IF NOT EXISTS apollo_enrichment_log JSONB DEFAULT '[]'::jsonb;

-- Índice para busca rápida de oportunidades pendentes de sync
CREATE INDEX IF NOT EXISTS idx_oportunidades_apollo_sync 
  ON oportunidades_prospeccao(apollo_sync_status, updated_at DESC);

-- Índice para busca por person_id (evita duplicidade no Apollo)
CREATE INDEX IF NOT EXISTS idx_oportunidades_apollo_person 
  ON oportunidades_prospeccao(apollo_person_id)
  WHERE apollo_person_id IS NOT NULL;

COMMENT ON COLUMN oportunidades_prospeccao.apollo_sync_status IS 
  'Status do sync com Apollo.io: pending, synced, failed, skipped';
COMMENT ON COLUMN oportunidades_prospeccao.apollo_person_id IS 
  'ID da pessoa no Apollo.io (para rastreamento e deduplicação)';
COMMENT ON COLUMN oportunidades_prospeccao.apollo_account_id IS 
  'ID da conta/empresa no Apollo.io';
COMMENT ON COLUMN oportunidades_prospeccao.apollo_synced_at IS 
  'Timestamp do último sync bem-sucedido com Apollo';
COMMENT ON COLUMN oportunidades_prospeccao.apollo_sync_error IS 
  'Mensagem de erro do último sync com Apollo (se falhou)';
COMMENT ON COLUMN oportunidades_prospeccao.apollo_enrichment_log IS 
  'Log JSONB do enriquecimento Apollo (campos encontrados, timestamps)';
