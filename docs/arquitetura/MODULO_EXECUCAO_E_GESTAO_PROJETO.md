# Módulo Execução e Gestão de Projeto (Playbook de Abertura)

## Contexto do Projeto

**Nome:** GymSite Execução — Playbook Inteligente de Abertura de Unidade

**Objetivo:** Uma vez que o empreendedor define o local (cidade, bairro, possivelmente o imóvel) e tem o Relatório de Viabilidade em mãos, ele precisa **executar**. Este módulo transforma o relatório em um projeto estruturado com tarefas, prazos, responsáveis, custos e acompanhamento de progresso. A IA atua como gestor de projetos, criando tarefas automaticamente a partir dos achados do relatório, preenchendo campos com contexto e sugerindo próximos passos baseados em projetos anteriores semelhantes.

**Personas alvo:**
- **A-001 Empreendedor Iniciante:** Nunca abriu academia. Precisa de um "passo a passo" completo. Não sabe o que precisa fazer depois de "escolher o bairro". Acompanha pelo celular.
- **A-002 Franqueado em Expansão:** Sabe o processo, mas quer otimizar prazos e custos. Usa para delegar tarefas à equipe e acompanhar KPIs.
- **A-003 Gestor de Rede:** Acompanha dezenas de projetos de abertura simultâneos. Precisa de dashboard consolidado e alertas de atraso.
- **A-004 Consultor/Parceiro:** Acompanha projetos de múltiplos clientes. Precisa de relatórios de progresso para apresentar.

**Documentos fonte de verdade:**
- `docs/arquitetura/AGENTE_CONSULTOR_CONVERSACIONAL.md` — UserProject como container
- Relatório de Viabilidade (saída A6) — fonte de dados para geração automática de tarefas
- `docs/metodologia/POSITIONING_FRAMEWORK.md` — estratégia de posicionamento vira tarefas de branding/marketing

---

## Stack do Projeto

| Categoria | Tecnologia |
|-----------|------------|
| Frontend | React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Gráficos | Recharts (dashboards), react-big-calendar ou fullcalendar (timeline/Gantt) |
| Kanban | @dnd-kit/core ou @hello-pangea/dnd (drag-and-drop) |
| Estado | Zustand (estado local do projeto), React Query (servidor) |
| Backend | Python 3.12, FastAPI |
| LLM | Gemini 2.5 Flash (geração de tarefas, resumos, sugestões) |
| Banco | Supabase PostgreSQL |
| Notificações | Supabase Realtime (atualizações em tempo real) + push/WhatsApp (futuro) |

---

## Glossário do Domínio

### Termos que o usuário USA (use na UI)
- **Playbook / Plano de Ação:** o conjunto de tarefas gerado para abrir a unidade.
- **Tarefa / Etapa:** cada coisa que precisa ser feita. "Regularizar no Corpo de Bombeiros."
- **Prazo / Data Limite:** quando a tarefa precisa estar pronta.
- **Responsável:** quem vai fazer a tarefa (pode ser o próprio empreendedor, um sócio, um prestador).
- **Marco / Checkpoint:** datas importantes do projeto. "Dia da inauguração", "Entrega da obra civil."
- **Custo Planejado vs. Real:** quanto se esperava gastar vs. quanto se gastou de fato.
- **Progresso:** "Você completou 35% do playbook."
- **Risco / Atenção:** tarefas que estão atrasadas, com custo estourado ou com dependências bloqueadas.
- **Sugestão da IA:** "Com base em projetos similares em Recife, sugiro adicionar uma tarefa de..."

### Termos PROIBIDOS na UI
"stub", "pipeline", "queue", "worker", "entity", "record", "transaction", "async", "commit", "deploy", "schema", "trigger", "cron".

---

## Padrões Arquiteturais

### P0 — Playbook com Contexto do Relatório

O playbook é gerado automaticamente a partir do Relatório de Viabilidade. Ele não é uma lista genérica — é **contextualizado**:
- Se o relatório identificou falta de estacionamento → tarefa "Negociar convênio de estacionamento com edifício vizinho".
- Se o relatório indicou investimento de R$ 1,2M em cenário premium → tarefa "Levantar financiamento" com custo estimado vinculado.
- Se A3c mapeou que concorrentes não oferecem pilates → tarefa "Contratar instrutora de pilates" vinculada à estratégia de diferenciação.

### P1 — Tarefas com Dependências e Cascatas

Tarefas têm dependências ("Não posso comprar equipamentos antes de definir o layout"). A conclusão de uma tarefa pode disparar a liberação de outras. Atrasos propagam para dependentes.

### P2 — Custos Planejados vs. Reais (Lançamentos)

Cada tarefa pode ter custos. O empreendedor registra o valor real gasto. O sistema calcula desvio em tempo real. Não há "saldo armazenado" — é calculado a partir dos lançamentos (tarefas concluídas com custo real informado).

### P3 — Dashboards de Acompanhamento

Visões analíticas: progresso geral, custo acumulado vs. orçamento, tarefas atrasadas, riscos, comparação com projetos similares. Atualizados em runtime a cada mudança de status.

---

## Estrutura de Pastas e Arquivos (Proposta)

```
backend/
 services/
    execucao/
       __init__.py
       playbook_engine.py           # Gera playbook a partir do relatório (LLM + templates)
       tarefa_service.py            # CRUD de tarefas, dependências, status
       okr_service.py               # CRUD de OKRs e link com tarefas
       custo_service.py             # Registro e consolidação de custos
       sugestao_ia_service.py       # Sugere novas tarefas com base em contexto + histórico
    tools/
       playbook_templates.py        # Templates de playbook por tipo de negócio (academia, box, studio)
       playbook_generator.py        # LLM prompt + parser para gerar tarefas estruturadas
 api.py                             # Endpoints /api/execucao/*

db/
 migrations/
    20250610_add_execucao_schema.sql   # tarefas, okrs, timeline, custos

frontend/src/
 routes/
    ProjetoExecucaoPage.tsx        # Tela principal do playbook (Kanban + Gantt + Lista)
    ProjetoDashboardPage.tsx       # Dashboard de progresso, custos, riscos
 components/
    execucao/
       PlaybookKanban.tsx           # Kanban drag-and-drop (A Fazer | Em Andamento | Concluído | Bloqueado)
       PlaybookGantt.tsx            # Timeline visual com prazos e dependências
       PlaybookLista.tsx            # Lista detalhada com filtros e ordenação
       TarefaCard.tsx               # Card de tarefa com custo, responsável, prazo, indicadores
       TarefaDrawer.tsx             # Detalhe da tarefa (descrição, checklist, custos, anexos, comentários)
       SugestaoIaCard.tsx           # Card flutuante: "A IA sugere adicionar: [X]"
       ProgressoPlaybook.tsx        # Barra de progresso geral com milestones
       CustoPlanejadoVsReal.tsx     # Gráfico de comparação de custos
       OkrLinker.tsx                # Componente para vincular tarefa a OKR
 hooks/
    usePlaybook.ts                 # Estado do playbook (tarefas, filtros, progresso)
    useTarefas.ts                  # CRUD de tarefas via React Query
    useSugestoesIa.ts              # Polling de sugestões da IA
```

---

## Modelo de Dados (Supabase)

### Tabela `playbooks`

Um playbook é a "instância de execução" de um projeto.

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

    -- Resumo financeiro (calculado em runtime, mas cacheado)
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
```

### Tabela `tarefas`

```sql
CREATE TABLE tarefas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    -- Hierarquia
    tarefa_pai_id UUID REFERENCES tarefas(id),   -- para subtarefas / checklist

    -- Identificação
    titulo TEXT NOT NULL,
    descricao TEXT,
    categoria TEXT NOT NULL
        CHECK (categoria IN (
            'IMOBILIARIO','LEGAL','OBRAS','EQUIPAMENTOS',
            'RH','MARKETING','TECNOLOGIA','FINANCEIRO','OPERACIONAL','OUTRO'
        )),

    -- Status
    status TEXT NOT NULL DEFAULT 'A_FAZER'
        CHECK (status IN ('A_FAZER','EM_ANDAMENTO','CONCLUIDA','BLOQUEADA','CANCELADA')),

    -- Prioridade
    prioridade TEXT NOT NULL DEFAULT 'MEDIA'
        CHECK (prioridade IN ('BAIXA','MEDIA','ALTA','CRITICA')),

    -- Prazos
    data_inicio DATE,
    data_prevista_conclusao DATE,
    data_conclusao DATE,

    -- Custo
    custo_planejado DECIMAL(12,2),
    custo_real DECIMAL(12,2),

    -- Responsável
    responsavel_nome TEXT,
    responsavel_email TEXT,
    responsavel_telefone TEXT,

    -- Link com relatório (se originada do relatório)
    origem_relatorio_secao TEXT,   -- ex: "concorrencia", "financeiro"
    origem_relatorio_insight TEXT, -- texto do insight que gerou a tarefa

    -- Link com OKR
    okr_id UUID REFERENCES okrs(id),

    -- Ordenação
    ordem INT DEFAULT 0,

    -- IA
    sugerida_pela_ia BOOLEAN DEFAULT false,
    aceita_pelo_usuario BOOLEAN DEFAULT true,  -- false = sugestão pendente

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_tarefas_playbook ON tarefas(playbook_id);
CREATE INDEX idx_tarefas_status ON tarefas(status);
CREATE INDEX idx_tarefas_categoria ON tarefas(categoria);
```

### Tabela `tarefa_dependencias`

```sql
CREATE TABLE tarefa_dependencias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    depende_de_tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL DEFAULT 'TERMINA_PARA_COMECAR'
        CHECK (tipo IN ('TERMINA_PARA_COMECAR','COMECA_JUNTO','TERMINA_JUNTO')),
    UNIQUE(tarefa_id, depende_de_tarefa_id)
);
```

### Tabela `tarefa_checklist`

Sub-itens de uma tarefa.

```sql
CREATE TABLE tarefa_checklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    concluido BOOLEAN DEFAULT false,
    ordem INT DEFAULT 0
);
```

### Tabela `okrs`

```sql
CREATE TABLE okrs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,

    objetivo TEXT NOT NULL,           -- "Abrir unidade em 90 dias"
    descricao TEXT,

    -- Key Results
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
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Tabela `timeline_eventos` (Marcos)

```sql
CREATE TABLE timeline_eventos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,

    titulo TEXT NOT NULL,
    descricao TEXT,
    data DATE NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'MARCO'
        CHECK (tipo IN ('MARCO','DEADLINE','REUNIAO','INSPECAO')),
    cor TEXT DEFAULT '#3B82F6',  -- hex para badge

    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Tabela `tarefa_comentarios`

```sql
CREATE TABLE tarefa_comentarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    conteudo TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Integração com o Ecossistema GymSite

### Geração Automática a partir do Relatório

Quando o usuário pede "Gerar Playbook" após ter o Relatório de Viabilidade:

```
Relatório (JSON flat) ──► playbook_generator.py (LLM + templates)
                              │
                              ├──► Extrai insights de cada seção
                              ├──► Mapeia para tarefas do template base
                              ├──► Personaliza com dados do relatório
                              │
                              ▼
                         Playbook estruturado
                              │
                              ├──► Tarefas de Imobiliário (A1 + FIPEZAP)
                              ├──► Tarefas Legais (CNO, Corpo de Bombeiros, Alvará)
                              ├──► Tarefas de Obras (projeto, execução, entrega)
                              ├──► Tarefas de Equipamentos (kit baseado em A4)
                              ├──► Tarefas de RH (contratação por perfil A2)
                              ├──► Tarefas de Marketing (posicionamento A9)
                              ├──► Tarefas Financeiras (baseadas em cenários A4)
                              └──► OKRs derivados do veredito
```

**Exemplos de mapeamento Relatório → Tarefas:**

| Seção do Relatório | Insight | Tarefa Gerada | Categoria |
|-------------------|---------|--------------|-----------|
| A3b — Concorrência | 78% de reviews negativos citam "lotação no pico" | Criar estratégia de horários flexíveis e pré-agendamento | OPERACIONAL |
| A3c — Oferta | Nenhum concorrente oferece pilates | Contratar instrutor de pilates e montar sala | RH + EQUIPAMENTOS |
| A1 — GeoScout | Top candidato: Av. Cabo Branco, 450m² | Agendar visita ao imóvel + negociar contrato | IMOBILIARIO |
| A4 — Financeiro | CAPEX estimado: R$ 1.200.000 | Abrir linha de crédito / buscar investidor | FINANCEIRO |
| A9 — Posicionamento | Estratégia ERRC: "Eliminar filas, Reduzir preço entrada" | Criar campanha de pré-lançamento com preço early-bird | MARKETING |
| A0 — Mercado | Novos CNPJ: 4 academias abriram nos últimos 90 dias | Acelerar cronograma — mercado está aquecido | OPERACIONAL |

### Integração com o Consultor Conversacional

O consultor não para no relatório. Ele continua acompanhando o playbook:
- "Você concluiu a tarefa 'Agendar visita ao imóvel'. Parabéns! Quer que eu pesquise mais opções de backup?"
- "Sua tarefa 'Regularizar no Corpo de Bombeiros' está atrasada há 5 dias. Posso te ajudar a entender o que falta?"
- "Com base no custo real informado, você já gastou 60% do orçamento de equipamentos. Quer que eu revise o kit?"

---

## Endpoints da API

### Playbook

```http
POST   /api/execucao/playbooks                    # Criar playbook a partir de projeto/relatório
GET    /api/execucao/playbooks                    # Listar playbooks do usuário
GET    /api/execucao/playbooks/{id}               # Detalhe do playbook (com tarefas, OKRs, timeline)
PATCH  /api/execucao/playbooks/{id}               # Atualizar metadados
POST   /api/execucao/playbooks/{id}/gerar         # (Re)gerar tarefas a partir do relatório
```

### Tarefas

```http
GET    /api/execucao/playbooks/{id}/tarefas
POST   /api/execucao/tarefas                      # Criar tarefa manual
PATCH  /api/execucao/tarefas/{tarefa_id}          # Atualizar status, prazo, custo, responsável
DELETE /api/execucao/tarefas/{tarefa_id}          # Soft delete
POST   /api/execucao/tarefas/{id}/concluir        # Marcar concluída + registrar custo real
POST   /api/execucao/tarefas/{id}/bloquear        # Marcar bloqueada + motivo
```

### OKRs

```http
GET    /api/execucao/playbooks/{id}/okrs
POST   /api/execucao/okrs
PATCH  /api/execucao/okrs/{okr_id}
```

### Timeline / Marcos

```http
GET    /api/execucao/playbooks/{id}/timeline
POST   /api/execucao/timeline-eventos
PATCH  /api/execucao/timeline-eventos/{id}
```

### Sugestões da IA

```http
GET    /api/execucao/playbooks/{id}/sugestoes     # Lista sugestões pendentes
POST   /api/execucao/sugestoes/{id}/aceitar       # Aceitar sugestão (vira tarefa)
POST   /api/execucao/sugestoes/{id}/rejeitar      # Rejeitar sugestão
```

**Request de geração de playbook:**
```json
{
  "projeto_id": "550e8400-...",
  "relatorio_id": "rel-789",
  "nome": "Abertura Academia Cabo Branco"
}
```

**Response:**
```json
{
  "playbook_id": "pb-001",
  "nome": "Abertura Academia Cabo Branco",
  "tarefas_geradas": 24,
  "tarefas_por_categoria": {
    "IMOBILIARIO": 3,
    "LEGAL": 4,
    "OBRAS": 5,
    "EQUIPAMENTOS": 3,
    "RH": 4,
    "MARKETING": 3,
    "FINANCEIRO": 1,
    "OPERACIONAL": 1
  },
  "custo_planejado_total": 1250000.00,
  "data_prevista_conclusao": "2026-09-15",
  "mensagem": "Playbook gerado com 24 tarefas a partir do seu Relatório de Viabilidade. O investimento planejado é de R$ 1.250.000 com previsão de conclusão em 90 dias."
}
```

---

## Fluxos de Exemplo

### Fluxo 1: Geração Automática do Playbook

| Etapa | Sistema | Ação |
|-------|---------|------|
| 1 | Usuário | "Gera meu plano de abertura" (na tela do relatório) |
| 2 | Backend | `POST /api/execucao/playbooks` — cria playbook vinculado ao `projeto_id` + `relatorio_id` |
| 3 | Backend | `playbook_generator.py` lê o relatório JSON e aplica template base + LLM para personalizar |
| 4 | Backend | Insere tarefas em batch no Supabase |
| 5 | Backend | Gera OKRs automaticamente ("Abrir em 90 dias", "Investimento abaixo de R$ 1,25M", "Capturar 200 alunos nos primeiros 3 meses") |
| 6 | Frontend | Redireciona para `/execucao/pb-001` com Kanban aberto |
| 7 | Frontend | Exibe `SugestaoIaCard`: "Sua análise de concorrência indicou falta de pilates. Adicionar tarefa de contratação?" |

### Fluxo 2: Acompanhamento e Atualização

| Etapa | Usuário | Sistema |
|-------|---------|---------|
| 1 | Marca tarefa "Assinar contrato do imóvel" como CONCLUIDA | Atualiza status. Libera tarefas dependentes ("Iniciar obra civil", "Contratar projeto de arquitetura"). Recalcula progresso (42% → 48%). |
| 2 | Informa custo real de R$ 15.000 (planejado era R$ 12.000) | Atualiza `custo_real`. Calcula desvio de +25%. Se desvio > 20%, exibe alerta: "Custo do imóvel 25% acima do planejado. Quer que eu revise as demais etapas?" |
| 3 | Pergunta "Estou atrasado, o que posso fazer?" | Consultor analisa tarefas BLOQUEADAS e ATRASADAS. Sugere: "Você pode paralelizar 'Compra de equipamentos' com 'Obras' se adiantar o layout. Posso ajustar seu playbook?" |

### Fluxo 3: Sugestão Proativa da IA

| Gatilho | Ação da IA |
|---------|-----------|
| Usuário conclui tarefa "Contratar instrutores de musculação" | IA sugere: "Adicionar tarefa de treinamento de equipe? 85% dos projetos similares incluem essa etapa." |
| Custo acumulado passa de 80% do orçamento | IA sugere: "Revisão financeira: você já usou 80% do orçamento planejado, mas faltam 40% das tarefas. Quer que eu analise onde enxugar?" |
| Data de um marco se aproxima (7 dias) | Notificação: "Faltam 7 dias para o prazo de 'Entrega da obra civil'. 3 tarefas dependentes estão pendentes." |
| Novo concorrente abre no bairro (detectado via polling A3a) | IA sugere: "Uma nova academia abriu a 500m do seu ponto. Adicionar tarefa de 'Revisar estratégia de preços'?" |

---

## Regras de Implementação

### Backend

- **Geração de tarefas é idempotente:** rodar `gerar` duas vezes no mesmo relatório produz o mesmo playbook (ou atualiza tarefas pendentes sem perder dados de tarefas concluídas).
- **Cálculo de progresso em runtime:** `percentual_concluido = concluidas / total * 100`. Nunca armazenar denormalizado sem trigger de atualização.
- **Dependências verificadas no backend:** antes de marcar uma tarefa como CONCLUIDA, validar se todas as predecessoras estão CONCLUIDAS. Se não, retornar erro com lista do que falta.
- **Sugestões da IA são soft:** sempre exigir aceite do usuário. Nunca criar tarefas automaticamente sem consentimento.
- **Templates por tipo de negócio:** academia tradicional, crossfit box, studio de pilates e studio funcional têm playbooks base diferentes (ex: box não precisa de "montar sala de RPM", studio não precisa de "contratar 8 instrutores").

### Frontend

- **Mobile-first:** Kanban funciona em mobile com swipe entre colunas. Gantt é read-only em mobile (apenas visualização simplificada).
- **Drag-and-drop:** Kanban com @dnd-kit. Reordenar tarefas dentro da coluna atualiza `ordem`.
- **Estado em URL (P-006):** filtro de categoria, status e visualização ativa (kanban/gantt/lista) persistem em query params.
- **Real-time:** usar Supabase Realtime para atualizar o Kanban quando outro usuário (ex: sócio) move uma tarefa.
- **Cores por categoria:** IMOBILIARIO (azul), LEGAL (vermelho), OBRAS (laranja), EQUIPAMENTOS (roxo), RH (verde), MARKETING (rosa), FINANCEIRO (amarelo), OPERACIONAL (cinza).

### UX

- **Progresso visível sempre:** barra fixa no topo mostrando "% concluído" e "dias restantes até inauguração".
- **Celebração:** quando uma tarefa CRITICA é concluída, micro-interação de confete ou badge.
- **Empty states com ação:** se uma categoria não tem tarefas, mostrar "Adicionar primeira tarefa de [categoria]" ou "Solicitar sugestão da IA".

---

## Decisões de Produto (DP)

| Código | Decisão | Justificativa |
|--------|---------|---------------|
| **DP-001** | Playbook é gerado uma única vez a partir do relatório, mas editável depois | O relatório é a "foto" do momento. O mundo muda — o empreendedor precisa adaptar. |
| **DP-002** | Sugestões da IA sempre requerem aceite do usuário | Autonomia do empreendedor. A IA é assessora, não gestora. |
| **DP-003** | Tarefas podem ser criadas manualmente além das geradas | Cada projeto tem particularidades que o relatório não previu. |
| **DP-004** | Custo real é opcional por tarefa, mas obrigatório para tarefas de grande valor (> R$ 10.000) | Evita micromanagement em tarefas pequenas, mas exige controle nas grandes. |
| **DP-005** | Playbook pode ser "clonado" para projetos similares | Franqueado abrindo a 3ª unidade no mesmo estado pode reaproveitar 70% do playbook. |
| **DP-006** | OKRs são gerados automaticamente, mas editáveis | O relatório define objetivos realistas baseados em dados. O usuário ajusta conforme ambição. |

---

## Pendências Críticas

- **Pend-1** — Notificações: push no navegador, email ou WhatsApp? Recomendo começar com email + badge no app. WhatsApp é Fase 2.
- **Pend-2** — Compartilhamento: o empreendedor pode convidar sócio/arquiteto para ver o playbook? Se sim, precisamos de permissões por convite (read-only vs. editor).
- **Pend-3** — Integração com calendário externo (Google Calendar / Outlook) para marcos e prazos? Recomendo Fase 2.
- **Pend-4** — Template de playbook: quantos templates base teremos? Proposta: 4 (academia tradicional, crossfit box, studio pilates, studio funcional).
- **Pend-5** — Preço/saas: este módulo é grátis, freemium ou pago? Isso afeta limites (ex: número de tarefas, sugestões IA/mês).

---

## Roadmap de Implementação

### Fase 1 — Playbook Base (2 semanas)
1. Schema: `playbooks`, `tarefas`, `tarefa_dependencias`, `tarefa_checklist`.
2. `playbook_templates.py` com templates base por tipo de negócio.
3. `playbook_generator.py`: LLM que lê relatório e gera tarefas estruturadas.
4. Endpoint `POST /api/execucao/playbooks/{id}/gerar`.
5. Frontend: `PlaybookKanban.tsx` + `TarefaCard.tsx` + `TarefaDrawer.tsx`.

### Fase 2 — Gestão Completa (2 semanas)
1. CRUD completo de tarefas (arrastar entre colunas, editar, excluir).
2. Dependências: validação no backend + visualização no frontend (setas entre cards).
3. Custos: input de custo real ao concluir + gráfico de evolução.
4. Timeline: `PlaybookGantt.tsx` com marcos.

### Fase 3 — OKRs e Dashboards (1-2 semanas)
1. Tabela `okrs` + CRUD.
2. `OkrLinker.tsx` para vincular tarefas a OKRs.
3. `ProjetoDashboardPage.tsx`: progresso, custo acumulado, tarefas atrasadas, comparação com baseline.

### Fase 4 — IA Proativa (2 semanas)
1. `sugestao_ia_service.py`: analisa contexto do projeto e sugere tarefas.
2. `SugestaoIaCard.tsx` no frontend.
3. Notificações de prazo (email/push).
4. Detecção de novos concorrentes no bairro → sugestão de tarefa defensiva.

---

## Conexão com o Consultor Conversacional

O Consultor e o Playbook são **dois lados da mesma moeda**:

| Modo | Quando o usuário está... | O que vê |
|------|-------------------------|----------|
| **Consultor** | Descobrindo, pesquisando, decidindo | Chat com respostas e pesquisas |
| **Playbook** | Executando, acompanhando, operando | Kanban, Gantt, dashboards, custos |

**Transições naturais:**
1. "Gostei dos dados, gera meu playbook" → Consultor chama `gerar_playbook()` → abre tela de execução.
2. "Estou atrasado na obra, o que faço?" → No Playbook, usuário pede ajuda → Consultor analisa tarefas bloqueadas → responde no chat lateral.
3. "Uma nova academia abriu do lado!" → Playbook detecta via A3a polling → Consultor sugere tarefa de reposicionamento.

O `UserProject` é o **container único** que une os dois mundos.
