-- Migration: 20260620_add_user_projects.sql
-- GymSite V2: tabelas do Consultor Jarvis
--
-- Contexto: não toca em sessions/messages (V1 continua funcionando).
-- Toda query filtra por auth.uid() via RLS.

-- ── 1. user_projects ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_projects (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id       UUID REFERENCES organizations(id),

    status TEXT NOT NULL DEFAULT 'EM_CONVERSA'
        CHECK (status IN (
            'EM_CONVERSA',
            'PESQUISANDO',
            'CONSOLIDANDO',
            'RELATORIO_GERADO',
            'ARQUIVADO'
        )),

    intencao_principal TEXT,

    -- Contexto acumulativo (cada campo atualizado pela tool correspondente)
    localizacao    JSONB NOT NULL DEFAULT '{}',
    modelo_negocio JSONB NOT NULL DEFAULT '{}',
    concorrencia   JSONB NOT NULL DEFAULT '{}',
    mercado        JSONB NOT NULL DEFAULT '{}',
    candidatos     JSONB NOT NULL DEFAULT '{}',
    financeiro     JSONB NOT NULL DEFAULT '{}',
    posicionamento JSONB NOT NULL DEFAULT '{}',
    anexos         JSONB NOT NULL DEFAULT '[]',
    acoes          JSONB NOT NULL DEFAULT '[]',

    -- Checklist de pesquisas realizadas
    pesquisas_realizadas JSONB NOT NULL DEFAULT '{
        "mercado": false,
        "concorrentes": false,
        "reviews": false,
        "oferta_concorrentes": false,
        "demografia": false,
        "pontos_comerciais": false,
        "investimento": false
    }',

    custo_brl_ate_agora NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    relatorio_id UUID REFERENCES relatorios(id),

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ  -- soft delete (nunca DELETE físico)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_user_projects_user_id
    ON user_projects(user_id, updated_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_user_projects_status
    ON user_projects(status)
    WHERE deleted_at IS NULL;

-- Trigger: atualiza updated_at automaticamente
CREATE OR REPLACE FUNCTION _set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_projects_updated_at ON user_projects;
CREATE TRIGGER trg_user_projects_updated_at
    BEFORE UPDATE ON user_projects
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();

-- RLS
ALTER TABLE user_projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_projects"
    ON user_projects FOR ALL
    USING (auth.uid() = user_id);

-- ── 1b. RPC: merge atômico de pesquisas_realizadas ───────────────────────────
-- Evita lost-update: as tools de um turno rodam em paralelo (asyncio.gather) e
-- cada uma marca sua flag. Read-modify-write no app perderia escritas; aqui o
-- merge `|| jsonb_build_object` é um único UPDATE atômico no Postgres.
-- p_user_id NULL = sem filtro de dono (back-compat); o engine sempre passa o dono.

CREATE OR REPLACE FUNCTION marcar_pesquisa(
    p_projeto_id UUID,
    p_pesquisa   TEXT,
    p_user_id    UUID DEFAULT NULL
)
RETURNS VOID
LANGUAGE sql
AS $$
    UPDATE user_projects
       SET pesquisas_realizadas = pesquisas_realizadas || jsonb_build_object(p_pesquisa, true),
           updated_at = now()
     WHERE id = p_projeto_id
       AND (p_user_id IS NULL OR user_id = p_user_id)
       AND deleted_at IS NULL;
$$;

-- ── 2. project_messages ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id  UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,

    -- Metadados de function calling (para auditoria e telemetria)
    tool_calls   JSONB,   -- [{ferramenta, status, resumo}]
    tool_results JSONB,   -- resultados resumidos (não o payload completo)

    tokens_entrada INT,
    tokens_saida   INT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_project_messages_projeto_id
    ON project_messages(projeto_id, created_at DESC);

-- RLS: usuário acessa mensagens dos seus próprios projetos
ALTER TABLE project_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_project_messages"
    ON project_messages FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM user_projects p
            WHERE p.id = project_messages.projeto_id
              AND p.user_id = auth.uid()
              AND p.deleted_at IS NULL
        )
    );

-- ── 3. Comentários de documentação ───────────────────────────────────────────

COMMENT ON TABLE user_projects IS
    'GymSite V2: projetos de viabilidade com contexto acumulativo por conversa. '
    'Cada projeto é criado na primeira mensagem e atualizado a cada ferramenta executada.';

COMMENT ON TABLE project_messages IS
    'GymSite V2: histórico de mensagens por projeto (user/assistant/tool). '
    'Separado de sessions/messages (V1) — coexistem sem conflito.';

COMMENT ON COLUMN user_projects.pesquisas_realizadas IS
    'Checklist das 7 pesquisas disponíveis. Cada campo é setado para true '
    'quando a tool correspondente retorna com sucesso.';

COMMENT ON COLUMN user_projects.custo_brl_ate_agora IS
    'Custo acumulado em BRL das tools executadas neste projeto. '
    'Estimativa baseada em _CUSTO_BRL_POR_TOOL no consultor_engine.py.';

COMMENT ON COLUMN user_projects.deleted_at IS
    'Soft delete: nunca deletar fisicamente. Projetos arquivados ficam '
    'visíveis em deleted_at IS NOT NULL para auditoria.';
