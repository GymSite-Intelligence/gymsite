-- Migration: Execução e Gestão de Projeto (Playbook de Abertura)
-- Cria: user_projects, project_messages, playbooks, tarefas, dependencias, checklist, okrs, timeline, comentarios, projeto_membros
-- Data: 2026-06-10

-- =============================================================================
-- 1. USER_PROJECTS (Container central — revisado para unificação)
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    org_id UUID REFERENCES organizations(id),

    status TEXT NOT NULL DEFAULT 'EM_CONVERSA'
        CHECK (status IN ('EM_CONVERSA','PESQUISANDO','CONSOLIDANDO','RELATORIO_GERADO','ARQUIVADO')),

    nome TEXT,
    intencao_principal TEXT,

    -- Contexto acumulativo (JSONB flexível)
    localizacao JSONB DEFAULT '{}',
    modelo_negocio JSONB DEFAULT '{}',
    concorrencia JSONB DEFAULT '{}',
    mercado JSONB DEFAULT '{}',
    candidatos JSONB DEFAULT '{}',
    financeiro JSONB DEFAULT '{}',
    posicionamento JSONB DEFAULT '{}',
    anexos JSONB DEFAULT '[]',

    relatorio_id UUID REFERENCES relatorios(id),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

-- RLS
ALTER TABLE user_projects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_own_projects" ON user_projects;
CREATE POLICY "users_own_projects" ON user_projects
    FOR ALL USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_projects_user_id ON user_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_status ON user_projects(status);
CREATE INDEX IF NOT EXISTS idx_user_projects_relatorio ON user_projects(relatorio_id);

-- =============================================================================
-- 2. PROJECT_MESSAGES (Histórico de conversa)
-- =============================================================================

CREATE TABLE IF NOT EXISTS project_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_results JSONB,
    tokens_entrada INT,
    tokens_saida INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_project_messages_projeto_id ON project_messages(projeto_id);
CREATE INDEX IF NOT EXISTS idx_project_messages_created ON project_messages(created_at);

-- =============================================================================
-- 3. PLAYBOOKS
-- =============================================================================

CREATE TABLE IF NOT EXISTS playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    relatorio_id UUID REFERENCES relatorios(id),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    org_id UUID REFERENCES organizations(id),

    nome TEXT NOT NULL DEFAULT 'Plano de Abertura',
    descricao TEXT,

    status TEXT NOT NULL DEFAULT 'ATIVO'
        CHECK (status IN ('ATIVO','CONCLUIDO','ARQUIVADO','CANCELADO')),

    data_inicio DATE,
    data_prevista_conclusao DATE,
    data_conclusao DATE,

    -- Valores monetários SEMPRE em centavos (BIGINT) — regra P-007/processo-mudanca
    custo_planejado_total BIGINT,
    custo_real_total BIGINT,

    percentual_concluido DECIMAL(5,2) DEFAULT 0,
    total_tarefas INT DEFAULT 0,
    tarefas_concluidas INT DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_playbooks_projeto ON playbooks(projeto_id);
CREATE INDEX IF NOT EXISTS idx_playbooks_user ON playbooks(user_id);
CREATE INDEX IF NOT EXISTS idx_playbooks_status ON playbooks(status);

-- =============================================================================
-- 4. TAREFAS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tarefas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    tarefa_pai_id UUID REFERENCES tarefas(id),

    titulo TEXT NOT NULL,
    descricao TEXT,
    categoria TEXT NOT NULL
        CHECK (categoria IN (
            'IMOBILIARIO','LEGAL','OBRAS','EQUIPAMENTOS',
            'TECNOLOGIA','RH','MARKETING','FINANCEIRO','OPERACIONAL','OUTRO'
        )),

    status TEXT NOT NULL DEFAULT 'A_FAZER'
        CHECK (status IN ('A_FAZER','EM_ANDAMENTO','CONCLUIDA','BLOQUEADA','CANCELADA')),

    prioridade TEXT NOT NULL DEFAULT 'MEDIA'
        CHECK (prioridade IN ('BAIXA','MEDIA','ALTA','CRITICA')),

    data_inicio DATE,
    data_prevista_conclusao DATE,
    data_conclusao DATE,

    -- Centavos (BIGINT)
    custo_planejado BIGINT,
    custo_real BIGINT,

    responsavel_nome TEXT,
    responsavel_email TEXT,
    responsavel_telefone TEXT,

    origem_relatorio_secao TEXT,
    origem_relatorio_insight TEXT,

    okr_id UUID REFERENCES okrs(id),

    ordem INT DEFAULT 0,

    sugerida_pela_ia BOOLEAN DEFAULT false,
    aceita_pelo_usuario BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tarefas_playbook ON tarefas(playbook_id);
CREATE INDEX IF NOT EXISTS idx_tarefas_status ON tarefas(status);
CREATE INDEX IF NOT EXISTS idx_tarefas_categoria ON tarefas(categoria);
CREATE INDEX IF NOT EXISTS idx_tarefas_projeto ON tarefas(projeto_id);

-- =============================================================================
-- 5. TAREFA_DEPENDENCIAS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tarefa_dependencias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    depende_de_tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL DEFAULT 'TERMINA_PARA_COMECAR'
        CHECK (tipo IN ('TERMINA_PARA_COMECAR','COMECA_JUNTO','TERMINA_JUNTO')),
    UNIQUE(tarefa_id, depende_de_tarefa_id)
);

CREATE INDEX IF NOT EXISTS idx_tarefa_deps_tarefa ON tarefa_dependencias(tarefa_id);
CREATE INDEX IF NOT EXISTS idx_tarefa_deps_depende ON tarefa_dependencias(depende_de_tarefa_id);

-- =============================================================================
-- 6. TAREFA_CHECKLIST
-- =============================================================================

CREATE TABLE IF NOT EXISTS tarefa_checklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    concluido BOOLEAN DEFAULT false,
    ordem INT DEFAULT 0,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_checklist_tarefa ON tarefa_checklist(tarefa_id);

-- =============================================================================
-- 7. OKRS
-- =============================================================================

CREATE TABLE IF NOT EXISTS okrs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    objetivo TEXT NOT NULL,
    descricao TEXT,

    kr1_descricao TEXT,
    kr1_target DECIMAL(12,2),
    kr1_atual DECIMAL(12,2),

    kr2_descricao TEXT,
    kr2_target DECIMAL(12,2),
    kr2_atual DECIMAL(12,2),

    kr3_descricao TEXT,
    kr3_target DECIMAL(12,2),
    kr3_atual DECIMAL(12,2),

    status TEXT NOT NULL DEFAULT 'ATIVO'
        CHECK (status IN ('ATIVO','CONCLUIDO','ARQUIVADO')),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_okrs_playbook ON okrs(playbook_id);
CREATE INDEX IF NOT EXISTS idx_okrs_projeto ON okrs(projeto_id);

-- =============================================================================
-- 8. TIMELINE_EVENTOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS timeline_eventos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,

    titulo TEXT NOT NULL,
    descricao TEXT,
    data DATE NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'MARCO'
        CHECK (tipo IN ('MARCO','DEADLINE','REUNIAO','INSPECAO')),
    cor TEXT DEFAULT '#3B82F6',

    created_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_timeline_playbook ON timeline_eventos(playbook_id);
CREATE INDEX IF NOT EXISTS idx_timeline_data ON timeline_eventos(data);

-- =============================================================================
-- 9. TAREFA_COMENTARIOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tarefa_comentarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    conteudo TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_comentarios_tarefa ON tarefa_comentarios(tarefa_id);

-- =============================================================================
-- 10. PROJETO_MEMBROS (Compartilhamento)
-- =============================================================================

CREATE TABLE IF NOT EXISTS projeto_membros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    email TEXT NOT NULL,
    papel TEXT NOT NULL CHECK (papel IN ('OWNER','EDITOR','VIEWER','EXECUTOR')),
    status TEXT NOT NULL DEFAULT 'PENDENTE' CHECK (status IN ('PENDENTE','ACEITO','RECUSADO','REMOVIDO')),
    convidado_por UUID REFERENCES auth.users(id),
    convite_token TEXT UNIQUE,
    convite_expira_em TIMESTAMPTZ,
    aceitado_em TIMESTAMPTZ,
    removido_em TIMESTAMPTZ,
    removido_por UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_proj_membros_proj_user ON projeto_membros(projeto_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_proj_membros_proj_email ON projeto_membros(projeto_id, email);
CREATE INDEX IF NOT EXISTS idx_proj_membros_token ON projeto_membros(convite_token);

-- =============================================================================
-- 11. PARCEIROS (Fornecedores curados)
-- =============================================================================

CREATE TABLE IF NOT EXISTS parceiros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome TEXT NOT NULL,
    descricao TEXT,
    logo_url TEXT,
    site_url TEXT,
    telefone TEXT,
    email TEXT,

    -- Categorias atendidas (mesmas do playbook)
    categorias TEXT[] NOT NULL DEFAULT '{}',

    -- Estados/cidades de atuação
    ufs_atuacao TEXT[] DEFAULT '{}',
    cidades_atuacao TEXT[] DEFAULT '{}',

    -- Tipo de parceria
    tipo_parceria TEXT NOT NULL DEFAULT 'LEAD_GENERATION'
        CHECK (tipo_parceria IN ('LEAD_GENERATION', 'AFILIADO', 'SPONSORED', 'WHITE_LABEL')),

    -- Lead generation (valor em centavos)
    lead_valor BIGINT,
    lead_maximo_mes INT,

    -- Afiliado
    comissao_percentual DECIMAL(5,2),

    -- Sponsored (centavos)
    valor_mensalidade BIGINT,

    -- Desconto para usuário
    desconto_oferecido TEXT,
    desconto_codigo TEXT,

    -- Diferenciais (array de badges)
    diferenciais TEXT[] DEFAULT '{}',

    -- Status
    status TEXT NOT NULL DEFAULT 'PENDENTE'
        CHECK (status IN ('PENDENTE', 'ATIVO', 'PAUSADO', 'CANCELADO', 'REPROVADO')),

    -- Curadoria
    curadoria_nota INT CHECK (curadoria_nota >= 1 AND curadoria_nota <= 5),
    curadoria_observacao TEXT,
    curadoria_por UUID REFERENCES auth.users(id),
    curadoria_em TIMESTAMPTZ,

    -- Métricas
    leads_gerados INT DEFAULT 0,
    leads_convertidos INT DEFAULT 0,
    rating_medio DECIMAL(3,2) DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_parceiros_status ON parceiros(status);
CREATE INDEX IF NOT EXISTS idx_parceiros_categorias ON parceiros USING GIN(categorias);
CREATE INDEX IF NOT EXISTS idx_parceiros_ufs ON parceiros USING GIN(ufs_atuacao);

-- =============================================================================
-- 12. PARCEIRO_LEADS
-- =============================================================================

CREATE TABLE IF NOT EXISTS parceiro_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parceiro_id UUID NOT NULL REFERENCES parceiros(id),
    projeto_id UUID NOT NULL REFERENCES user_projects(id),
    tarefa_id UUID REFERENCES tarefas(id),

    solicitante_nome TEXT,
    solicitante_email TEXT,
    solicitante_telefone TEXT,

    dados_projeto JSONB DEFAULT '{}',

    status TEXT NOT NULL DEFAULT 'NOVO'
        CHECK (status IN ('NOVO', 'CONTATADO', 'ORCAMENTO_ENVIADO', 'CONVERTIDO', 'DESCARTADO')),

    -- Centavos (BIGINT)
    valor_fechado BIGINT,
    comissao_gerada BIGINT,

    notas_parceiro TEXT,
    notas_internas TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_parceiro_leads_parceiro ON parceiro_leads(parceiro_id);
CREATE INDEX IF NOT EXISTS idx_parceiro_leads_projeto ON parceiro_leads(projeto_id);
CREATE INDEX IF NOT EXISTS idx_parceiro_leads_status ON parceiro_leads(status);

-- =============================================================================
-- 13. RLS POLICIES PARA NOVAS TABELAS
-- =============================================================================

-- project_messages
ALTER TABLE project_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "project_messages_user" ON project_messages;
CREATE POLICY "project_messages_user" ON project_messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_projects up
            WHERE up.id = project_messages.projeto_id
            AND up.user_id = auth.uid()
        )
    );

-- playbooks
ALTER TABLE playbooks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "playbooks_user" ON playbooks;
CREATE POLICY "playbooks_user" ON playbooks
    FOR ALL USING (auth.uid() = user_id);

-- tarefas
ALTER TABLE tarefas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tarefas_user" ON tarefas;
CREATE POLICY "tarefas_user" ON tarefas
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_projects up
            WHERE up.id = tarefas.projeto_id
            AND up.user_id = auth.uid()
        )
    );

-- tarefa_dependencias (via tarefas)
ALTER TABLE tarefa_dependencias ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tarefa_deps_user" ON tarefa_dependencias;
CREATE POLICY "tarefa_deps_user" ON tarefa_dependencias
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM tarefas t
            JOIN user_projects up ON up.id = t.projeto_id
            WHERE t.id = tarefa_dependencias.tarefa_id
            AND up.user_id = auth.uid()
        )
    );

-- tarefa_checklist
ALTER TABLE tarefa_checklist ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "checklist_user" ON tarefa_checklist;
CREATE POLICY "checklist_user" ON tarefa_checklist
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM tarefas t
            JOIN user_projects up ON up.id = t.projeto_id
            WHERE t.id = tarefa_checklist.tarefa_id
            AND up.user_id = auth.uid()
        )
    );

-- okrs
ALTER TABLE okrs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "okrs_user" ON okrs;
CREATE POLICY "okrs_user" ON okrs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_projects up
            WHERE up.id = okrs.projeto_id
            AND up.user_id = auth.uid()
        )
    );

-- timeline_eventos
ALTER TABLE timeline_eventos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "timeline_user" ON timeline_eventos;
CREATE POLICY "timeline_user" ON timeline_eventos
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM playbooks pb
            JOIN user_projects up ON up.id = pb.projeto_id
            WHERE pb.id = timeline_eventos.playbook_id
            AND up.user_id = auth.uid()
        )
    );

-- tarefa_comentarios
ALTER TABLE tarefa_comentarios ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "comentarios_user" ON tarefa_comentarios;
CREATE POLICY "comentarios_user" ON tarefa_comentarios
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM tarefas t
            JOIN user_projects up ON up.id = t.projeto_id
            WHERE t.id = tarefa_comentarios.tarefa_id
            AND up.user_id = auth.uid()
        )
    );

-- projeto_membros
ALTER TABLE projeto_membros ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "proj_membros_owner" ON projeto_membros;
CREATE POLICY "proj_membros_owner" ON projeto_membros
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_projects up
            WHERE up.id = projeto_membros.projeto_id
            AND up.user_id = auth.uid()
        )
    );

-- parceiros: leitura pública apenas de ativos; escrita somente via service role
-- (endpoints admin usam SUPABASE_SERVICE_ROLE_KEY, que ignora RLS)
ALTER TABLE parceiros ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "parceiros_read_ativos" ON parceiros;
CREATE POLICY "parceiros_read_ativos" ON parceiros
    FOR SELECT USING (status = 'ATIVO' AND deleted_at IS NULL);

-- parceiro_leads: contém PII do solicitante. Dono do projeto vê e cria os
-- próprios leads; parceiro e admin acessam via service role no backend.
ALTER TABLE parceiro_leads ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "parceiro_leads_owner_select" ON parceiro_leads;
CREATE POLICY "parceiro_leads_owner_select" ON parceiro_leads
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_projects up
            WHERE up.id = parceiro_leads.projeto_id
            AND up.user_id = auth.uid()
        )
    );
DROP POLICY IF EXISTS "parceiro_leads_owner_insert" ON parceiro_leads;
CREATE POLICY "parceiro_leads_owner_insert" ON parceiro_leads
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM user_projects up
            WHERE up.id = parceiro_leads.projeto_id
            AND up.user_id = auth.uid()
        )
    );

-- =============================================================================
-- 14. AUDITORIA_EVENTOS (append-only — P-007)
-- =============================================================================

CREATE TABLE IF NOT EXISTS auditoria_eventos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    projeto_id UUID REFERENCES user_projects(id),
    entidade TEXT NOT NULL,        -- 'tarefa', 'playbook', 'okr', 'parceiro_lead', 'projeto_membro'
    entidade_id UUID,
    evento TEXT NOT NULL,          -- 'CONCLUIR_TAREFA', 'GERAR_PLAYBOOK', 'ACEITAR_SUGESTAO_IA',
                                   -- 'CONVITE_ENVIADO', 'LEAD_ENVIADO', 'CUSTO_REGISTRADO'
    snapshot_antes JSONB,
    snapshot_depois JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auditoria_projeto ON auditoria_eventos(projeto_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_entidade ON auditoria_eventos(entidade, entidade_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_created ON auditoria_eventos(created_at);

-- Append-only: usuário lê os próprios eventos; INSERT/UPDATE/DELETE só via
-- service role (sem policies de escrita — RLS bloqueia tudo para anon/auth).
ALTER TABLE auditoria_eventos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "auditoria_select_own" ON auditoria_eventos;
CREATE POLICY "auditoria_select_own" ON auditoria_eventos
    FOR SELECT USING (auth.uid() = user_id);
