-- ============================================================================
-- Módulo de Prospecção CNPJ × CNO → Claw
-- Schema v1.0
-- ============================================================================

-- Tabela de oportunidades qualificadas (CNPJ entrante + CNO cruzado)
CREATE TABLE IF NOT EXISTS oportunidades_prospeccao (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id),

  -- Origem
  cnpj TEXT NOT NULL,
  cno TEXT,
  municipio_codigo TEXT,
  cidade TEXT,
  uf TEXT,

  -- Dados do CNPJ
  razao_social TEXT,
  nome_fantasia TEXT,
  segmento_operacao TEXT,
  data_inicio_atividade DATE,
  situacao_cadastral INTEGER,
  endereco_cnpj JSONB DEFAULT '{}'::jsonb,
  contato_cnpj JSONB DEFAULT '{}'::jsonb,

  -- Dados do CNO
  nome_obra TEXT,
  situacao_obra TEXT CHECK (situacao_obra IN ('em_curso', 'encerrada', 'paralisada', 'outra')),
  area_total_m2 NUMERIC(10,2),
  data_inicio_obra DATE,
  data_situacao_obra DATE,
  endereco_cno JSONB DEFAULT '{}'::jsonb,

  -- Match
  score_match NUMERIC(3,2) CHECK (score_match >= 0 AND score_match <= 1),
  motivo_match TEXT,

  -- Pipeline
  status TEXT NOT NULL DEFAULT 'novo'
    CHECK (status IN ('novo', 'qualificado', 'webhook_enviado', 'engajado', 'fechado', 'descartado')),
  prioridade TEXT NOT NULL DEFAULT 'media'
    CHECK (prioridade IN ('baixa', 'media', 'alta', 'critica')),

  -- Webhook
  webhook_url TEXT,
  webhook_payload JSONB DEFAULT '{}'::jsonb,
  webhook_enviado_at TIMESTAMPTZ,
  webhook_resposta_http INTEGER,
  webhook_tentativas INTEGER NOT NULL DEFAULT 0,

  -- Auditoria
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_oportunidades_status ON oportunidades_prospeccao(status);
CREATE INDEX IF NOT EXISTS idx_oportunidades_cidade ON oportunidades_prospeccao(cidade);
CREATE INDEX IF NOT EXISTS idx_oportunidades_match ON oportunidades_prospeccao(score_match DESC);
CREATE INDEX IF NOT EXISTS idx_oportunidades_cnpj ON oportunidades_prospeccao(cnpj);
CREATE INDEX IF NOT EXISTS idx_oportunidades_cno ON oportunidades_prospeccao(cno);
CREATE INDEX IF NOT EXISTS idx_oportunidades_created_at ON oportunidades_prospeccao(created_at DESC);

COMMENT ON TABLE oportunidades_prospeccao IS
  'Oportunidades de prospecção cruzando CNPJ fitness (≤90 dias) com CNO (obras em andamento/finalizadas).';

-- Tabela de log de webhooks (idempotência + debug)
CREATE TABLE IF NOT EXISTS webhook_claw_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  oportunidade_id UUID REFERENCES oportunidades_prospeccao(id) ON DELETE CASCADE,
  evento TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  http_status INTEGER,
  resposta TEXT,
  duracao_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_log_oportunidade ON webhook_claw_log(oportunidade_id);
CREATE INDEX IF NOT EXISTS idx_webhook_log_evento ON webhook_claw_log(evento);

COMMENT ON TABLE webhook_claw_log IS
  'Log de todos os webhooks disparados para o Claw/Vectra.';

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_oportunidades_updated_at ON oportunidades_prospeccao;
CREATE TRIGGER trg_oportunidades_updated_at
  BEFORE UPDATE ON oportunidades_prospeccao
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
