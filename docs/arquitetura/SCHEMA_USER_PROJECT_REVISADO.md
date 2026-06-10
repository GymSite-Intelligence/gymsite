# Schema Revisado — UserProject como Fonte Única de Verdade

> Este documento define o schema unificado que permite ao `UserProject` ser o container central tanto para o Consultor Conversacional quanto para o Playbook de Execução.

---

## 1. Visão Geral do Modelo

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER_PROJECT                                │
│                    (Fonte Única de Verdade)                         │
├─────────────────────────────────────────────────────────────────────┤
│  Contexto acumulativo:                                              │
│  ├── localizacao (JSONB)         → cidade, bairro, uf, geo          │
│  ├── modelo_negocio (JSONB)      → tipo, tamanho, público-alvo      │
│  ├── concorrencia (JSONB)        → resultados A3a+A3b+A3c           │
│  ├── mercado (JSONB)             → resultados A0+A2                 │
│  ├── candidatos (JSONB)          → resultados A1                    │
│  ├── financeiro (JSONB)          → resultados A4                    │
│  ├── posicionamento (JSONB)      → resultados A9                    │
│  └── anexos (JSONB)              → arquivos enviados pelo usuário   │
├─────────────────────────────────────────────────────────────────────┤
│  Relacionamentos:                                                   │
│  ├── 1:N project_messages        → histórico de conversa            │
│  ├── 1:1 relatorio_id            → relatório formal gerado          │
│  ├── 1:N playbooks               → playbooks de execução            │
│  └── 1:N projeto_membros         → membros convidados               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tabela `user_projects` (Revisada)

```sql
CREATE TABLE user_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    org_id UUID REFERENCES orgs(id),

    -- Status do projeto
    status TEXT NOT NULL DEFAULT 'EM_CONVERSA'
        CHECK (status IN ('EM_CONVERSA','PESQUISANDO','CONSOLIDANDO','RELATORIO_GERADO','ARQUIVADO')),

    -- Identificação
    nome TEXT,                           -- nome opcional dado pelo usuário
    intencao_principal TEXT,             -- "abrir_academia", "franquear", "reformar"

    -- Contexto acumulativo (enriquecido pelo Consultor)
    localizacao JSONB DEFAULT '{}',
    modelo_negocio JSONB DEFAULT '{}',
    concorrencia JSONB DEFAULT '{}',
    mercado JSONB DEFAULT '{}',
    candidatos JSONB DEFAULT '{}',
    financeiro JSONB DEFAULT '{}',
    posicionamento JSONB DEFAULT '{}',
    anexos JSONB DEFAULT '[]',

    -- Links
    relatorio_id UUID REFERENCES relatorios(id),

    -- Metadados
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ             -- soft delete (P-007)
);

-- RLS
ALTER TABLE user_projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_projects" ON user_projects
    FOR ALL USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX idx_user_projects_user_id ON user_projects(user_id);
CREATE INDEX idx_user_projects_status ON user_projects(status);
CREATE INDEX idx_user_projects_relatorio ON user_projects(relatorio_id);
```

### 2.1. JSONB Schemas (contrato de dados)

#### `localizacao`
```json
{
  "cidade": "João Pessoa",
  "uf": "PB",
  "bairro": "Cabo Branco",
  "bairros_alternativos": ["Manaira", "Tambaú"],
  "geo": { "lat": -7.15, "lng": -34.8 },
  "endereco_referencia": "Av. Cabo Branco, 123"
}
```

#### `modelo_negocio`
```json
{
  "tipo_negocio": "academia",
  "tamanho_preset": "m",
  "area_m2_min": 800,
  "area_m2_max": 1500,
  "publico_alvo": "25-40",
  "genero_alvo": "misto",
  "estacionamento_obrigatorio": true
}
```

#### `concorrencia`
```json
{
  "concorrentes": [...],           // saída bruta A3a
  "inteligencia_competitiva": {...}, // saída A3b
  "oferta_mapeada": {...},          // saída A3c
  "resumo_conversacional": "12 academias...",
  "data_pesquisa": "2026-06-10T10:00:00Z"
}
```

#### `mercado`
```json
{
  "market_context": {...},          // saída A0
  "analise_demografica": {...},     // saída A2
  "entrantes_recentes": {...},      // CNPJ 90d
  "obras_cno": {...},
  "data_pesquisa": "2026-06-10T10:00:00Z"
}
```

#### `candidatos`
```json
{
  "pontos_comerciais": [...],       // saída A1
  "top_candidato": {...},
  "data_pesquisa": "2026-06-10T10:00:00Z"
}
```

#### `financeiro`
```json
{
  "analise_financeira": {...},      // saída A4
  "cenarios": [...],
  "data_pesquisa": "2026-06-10T10:00:00Z"
}
```

#### `posicionamento`
```json
{
  "estrategia_errc": {...},         // saída A9
  "oceano_azul": {...},
  "data_pesquisa": "2026-06-10T10:00:00Z"
}
```

#### `anexos`
```json
[
  {
    "id": "anx-001",
    "storage_path": "projetos/user-123/anexo-456.pdf",
    "nome": "projeto_arquitetonico.pdf",
    "tipo_mime": "application/pdf",
    "tamanho_bytes": 2048000,
    "conteudo_extraido": "Área: 450m²...",
    "resumo_ia": "Projeto de academia com 450m²...",
    "entidades_extraidas": { "area_m2": 450 },
    "created_at": "2026-06-10T10:00:00Z"
  }
]
```

---

## 3. Tabela `project_messages`

```sql
CREATE TABLE project_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,        -- function calling metadata
    tool_results JSONB,      -- resultados das ferramentas
    tokens_entrada INT,
    tokens_saida INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_project_messages_projeto_id ON project_messages(projeto_id);
CREATE INDEX idx_project_messages_created ON project_messages(created_at);
```

---

## 4. Tabela `playbooks` (Linkada ao Projeto)

```sql
CREATE TABLE playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    relatorio_id UUID REFERENCES relatorios(id),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    org_id UUID REFERENCES orgs(id),

    nome TEXT NOT NULL DEFAULT 'Plano de Abertura',
    descricao TEXT,

    status TEXT NOT NULL DEFAULT 'ATIVO'
        CHECK (status IN ('ATIVO','CONCLUIDO','ARQUIVADO','CANCELADO')),

    data_inicio DATE,
    data_prevista_conclusao DATE,
    data_conclusao DATE,

    -- Resumo financeiro (calculado em runtime, cacheado)
    custo_planejado_total DECIMAL(12,2),
    custo_real_total DECIMAL(12,2),

    -- Progresso (calculado em runtime)
    percentual_concluido DECIMAL(5,2) DEFAULT 0,
    total_tarefas INT DEFAULT 0,
    tarefas_concluidas INT DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_playbooks_projeto ON playbooks(projeto_id);
CREATE INDEX idx_playbooks_user ON playbooks(user_id);
CREATE INDEX idx_playbooks_status ON playbooks(status);
```

---

## 5. Tabela `tarefas`

```sql
CREATE TABLE tarefas (
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

    custo_planejado DECIMAL(12,2),
    custo_real DECIMAL(12,2),

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

CREATE INDEX idx_tarefas_playbook ON tarefas(playbook_id);
CREATE INDEX idx_tarefas_status ON tarefas(status);
CREATE INDEX idx_tarefas_categoria ON tarefas(categoria);
CREATE INDEX idx_tarefas_projeto ON tarefas(projeto_id);
```

---

## 6. Tabela `tarefa_dependencias`

```sql
CREATE TABLE tarefa_dependencias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    depende_de_tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL DEFAULT 'TERMINA_PARA_COMECAR'
        CHECK (tipo IN ('TERMINA_PARA_COMECAR','COMECA_JUNTO','TERMINA_JUNTO')),
    UNIQUE(tarefa_id, depende_de_tarefa_id)
);

CREATE INDEX idx_tarefa_deps_tarefa ON tarefa_dependencias(tarefa_id);
CREATE INDEX idx_tarefa_deps_depende ON tarefa_dependencias(depende_de_tarefa_id);
```

---

## 7. Tabelas Auxiliares

### `tarefa_checklist`
```sql
CREATE TABLE tarefa_checklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    concluido BOOLEAN DEFAULT false,
    ordem INT DEFAULT 0
);
```

### `okrs`
```sql
CREATE TABLE okrs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    objetivo TEXT NOT NULL,
    descricao TEXT,
    kr1_descricao TEXT, kr1_target DECIMAL(12,2), kr1_atual DECIMAL(12,2),
    kr2_descricao TEXT, kr2_target DECIMAL(12,2), kr2_atual DECIMAL(12,2),
    kr3_descricao TEXT, kr3_target DECIMAL(12,2), kr3_atual DECIMAL(12,2),
    status TEXT NOT NULL DEFAULT 'ATIVO',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### `timeline_eventos`
```sql
CREATE TABLE timeline_eventos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    descricao TEXT,
    data DATE NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'MARCO',
    cor TEXT DEFAULT '#3B82F6',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### `tarefa_comentarios`
```sql
CREATE TABLE tarefa_comentarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    conteudo TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### `projeto_membros` (para compartilhamento)
```sql
CREATE TABLE projeto_membros (
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

CREATE UNIQUE INDEX idx_proj_membros_proj_user ON projeto_membros(projeto_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX idx_proj_membros_proj_email ON projeto_membros(projeto_id, email);
```

---

## 8. Migration SQL Completa

Arquivo: `db/migrations/20250610_add_execucao_schema.sql`

Vide arquivo real em `db/migrations/`.

---

## 9. Decisões de Schema

| Código | Decisão |
|--------|---------|
| **SCH-001** | `user_projects` usa JSONB para dados de pesquisa (A0-A4). Permite evolução sem migration. Índices GIN se necessário para queries específicas. |
| **SCH-002** | `playbooks` sempre vinculado a `user_projects` (1:N). Um projeto pode ter múltiplos playbooks (ex: cenário otimista vs. pessimista), mas só 1 ativo. |
| **SCH-003** | `tarefas` duplica `projeto_id` para evitar JOIN excessivo na listagem do Kanban. Mantém integridade via FK. |
| **SCH-004** | Soft delete em todas as tabelas de domínio (`deleted_at`). Nunca DELETE físico. |
| **SCH-005** | RLS em todas as tabelas. Query base sempre filtra por `auth.uid() = user_id` ou membros do projeto. |

---

## 10. Checklist T1.5

- [x] `user_projects` revisado com JSONB fields completos
- [x] `project_messages` separada (não polui o projeto)
- [x] `playbooks` vinculado ao projeto
- [x] `tarefas` com categoria, custo, responsável, origem do relatório
- [x] `tarefa_dependencias` modelada
- [x] `tarefa_checklist`, `okrs`, `timeline_eventos`, `tarefa_comentarios`
- [x] `projeto_membros` para compartilhamento
- [x] RLS policies definidas
- [x] Indexes estratégicos definidos
