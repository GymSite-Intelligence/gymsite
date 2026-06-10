# Agente Consultor Fitness Conversacional

## Contexto do Projeto

**Nome:** GymSite Intelligence — Módulo Consultor Conversacional

**Objetivo:** Transformar a experiência de geração de relatórios de viabilidade de um formulário estático em uma conversa natural com um consultor fitness experiente de IA. O empreendedor deve poder explorar o mercado de forma gradual — concorrentes, demografia, pontos comerciais, investimento — sem precisar preencher todos os campos de uma só vez. Quando tiver confiança, pede o relatório formal.

**Personas alvo:**
- **A-001 Empreendedor Iniciante:** Nunca abriu academia. Não conhece jargões. Precisa de orientação passo a passo. Acesso principalmente pelo celular.
- **A-002 Franqueado em Expansão:** Já tem operação, quer validar novos bairros/cidades. Precisa de dados rápidos para decisões. Acesso desktop e mobile.
- **A-003 Investidor/Consultor:** Analisa múltiplas oportunidades. Precisa comparar cenários e exportar pareceres técnicos.
- **A-004 Gestor de Rede:** Acompanha múltiplos projetos da equipe. Precisa de visão consolidada.

**Documentos fonte de verdade:**
- Este documento
- `docs/arquitetura/` — decisões arquiteturais do pipeline A0-A9
- `db/schema.sql` — schema Supabase atual
- `frontend/src/routes/AssistentePage.tsx` — chat conversacional legado

---

## Stack do Projeto

| Categoria | Tecnologia |
|-----------|------------|
| Frontend | React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Roteamento | TanStack Router |
| Estado Cliente | React Query (TanStack Query), Zustand (store local) |
| Forms | React Hook Form + Zod |
| Backend | Python 3.12, FastAPI |
| Orquestração de Agentes | Google ADK (Agents SDK) |
| LLM | Gemini 2.5 Flash (router/respostas), Gemini 2.5 Pro (análises profundas) |
| Banco de Dados | Supabase PostgreSQL |
| Cache | Redis (competitor_cache, market_bundles) |
| Filas | RedisQueue (pipeline pesado) |
| Armazenamento de Anexos | Supabase Storage |
| Extração de Anexos | Gemini Vision (imagens/PDF), pandas (planilhas) |

---

## Glossário do Domínio

### Termos que o usuário USA (use na UI)
- **Consultor / Analista:** a própria IA. "Vou consultar os dados para você."
- **Projeto:** o que o empreendedor está montando. "Seu projeto no Cabo Branco."
- **Pesquisa / Análise:** ação de buscar dados. "Pesquisei 12 academias por lá."
- **Concorrentes:** academias e boxes já em operação no bairro.
- **Reviews / Avaliações:** opiniões de clientes no Google Maps.
- **Reclamações / Dores:** problemas recorrentes mencionados nos reviews.
- **Investimento Inicial / Quanto custa:** CAPEX + OPEX + payback.
- **Ponto Comercial / Imóvel:** candidatos a endereço físico.
- **Relatório Formal:** documento consolidado com veredito, scores e cenários.
- **Anexo / Documento:** PDF, foto ou planilha enviada pelo usuário.

### Termos PROIBIDOS na UI
"slot", "pipeline", "stub", "output_key", "session.state", "token", "payload", "entidade", "registro", "submeter", "tenant", "async", "worker", "queue".

---

## Padrões Arquiteturais

### P0 — Projeto com Contexto Acumulativo (Rascunho Inteligente)

O usuário constrói seu projeto de forma gradual via conversa. Não há botão "Salvar". Cada mensagem, pesquisa e anexo persiste automaticamente no **UserProject**.

**Estados do Projeto:**
- `EM_CONVERSA` — coletando contexto, respondendo perguntas pontuais
- `PESQUISANDO` — ferramentas de mercado/concorrência em execução
- `CONSOLIDANDO` — gerando relatório formal (A6+A9)
- `RELATORIO_GERADO` — relatório disponível para visualização
- `ARQUIVADO` — projeto encerrado pelo usuário

**Regras:**
- Auto-save a cada interação (sem botão explícito).
- O usuário nunca precisa "preencher o formulário" — o consultor extrai informações da conversa.
- Decisão consciente única: **Gerar Relatório Formal** ou **Descartar Projeto**.

### P1 — Capabilities Sob Demanda

Cada "pergunta" do usuário dispara 0-N **ferramentas** independentes. O consultor (LLM com Function Calling) decide quais chamar.

**Cascatas:** quando uma ferramenta depende de outra (ex: `analisar_reviews` depende de `pesquisar_concorrentes`), o router executa em sequência, mas sempre dentro do mesmo ciclo de resposta.

### P2 — Dados Coletados são Append-Only

Resultados de pesquisas não são sobrescritos — são versionados por timestamp. O consultor sempre vê a coleta mais recente, mas o histórico preserva evolução (ex: concorrentes encontrados ontem vs. hoje).

### P3 — Resposta Conversacional com Fontes

Toda afirmação de dados deve citar a fonte (Google Maps, CNPJ/RFB, OSM, etc.). A resposta é linguagem natural — nunca JSON cru exposto ao usuário.

---

## Estrutura de Pastas e Arquivos (Proposta)

```
backend/
 services/
    consultor/
       __init__.py
       consultor_engine.py          # Router / Planner (Function Calling)
       project_state.py             # CRUD de UserProject no Supabase
       project_messages.py          # CRUD de mensagens do projeto
       anexo_processor.py           # Extração de PDF/foto/planilha
    tools/
       mercado.py                   # A0 isolado: pesquisar_contexto_mercado
       pontos_comerciais.py         # A1 isolado: buscar_pontos_comerciais
       demografia.py                # A2 isolado: analisar_demografia
       competicao.py                # A3a+A3b+A3c isolados
       financeiro.py                # A4 isolado: estimar_investimento
       consolidador.py              # A6+A9: gerar_relatorio_formal
    tinker/
       tinker_bot.py                # Mantido para Q&A legado
       tinker_context.py            # Mantido para Q&A legado
 api.py                             # Endpoints FastAPI (adicionar /consultor/*)

db/
 migrations/
    20250610_add_user_projects.sql   # Nova tabela + project_messages

frontend/src/
 hooks/
    useConsultorChat.ts             # Substitui useConversationalChat
    useProjeto.ts                   # Gerencia estado do UserProject
    useProjetoAcoes.ts              # Polling de ações em execução
 components/
    chat/
       ChatInterface.tsx            # Reutilizar existente (adaptar props)
       ChatInput.tsx                # Reutilizar (já suporta anexos)
       ChatMessage.tsx              # Reutilizar (markdown + syntax highlight)
       SuggestedActions.tsx         # NOVO: botões de próximos passos
       ProjetoStatusCard.tsx        # NOVO: o que já foi pesquisado
 routes/
    AssistentePage.tsx             # Adaptar para novo hook
    ProjetoDetailPage.tsx          # NOVO: tela de status do projeto
```

---

## Modelo de Dados (Supabase)

### Tabela `user_projects`

```sql
CREATE TABLE user_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    org_id UUID REFERENCES orgs(id),

    status TEXT NOT NULL DEFAULT 'EM_CONVERSA'
        CHECK (status IN ('EM_CONVERSA','PESQUISANDO','CONSOLIDANDO','RELATORIO_GERADO','ARQUIVADO')),

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
    acoes JSONB DEFAULT '[]',

    relatorio_id UUID REFERENCES relatorios(id),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ  -- soft delete (P-007)
);

ALTER TABLE user_projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_projects" ON user_projects
    FOR ALL USING (auth.uid() = user_id);

CREATE INDEX idx_user_projects_user_id ON user_projects(user_id);
CREATE INDEX idx_user_projects_status ON user_projects(status);
```

### Tabela `project_messages`

```sql
CREATE TABLE project_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,       -- function calling metadata
    tool_results JSONB,     -- resultados das ferramentas
    tokens_entrada INT,
    tokens_saida INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_project_messages_projeto_id ON project_messages(projeto_id);
```

---

## Endpoints da API

### Conversação Principal

```http
POST /api/consultor/conversar
Authorization: Bearer <jwt>
Content-Type: application/json
```

**Request:**
```json
{
  "mensagem": "Quero abrir uma academia em João Pessoa no Bairro Cabo Branco...",
  "projeto_id": "550e8400-e29b-41d4-a716-446655440000",
  "anexos": ["projetos/user-123/anexo-456.pdf"]
}
```

**Response (200 OK):**
```json
{
  "projeto_id": "550e8400-e29b-41d4-a716-446655440000",
  "mensagem": "Encontrei 12 academias no Cabo Branco. A principal reclamação dos alunos é lotação no horário de pico (78% dos reviews negativos). Quer que eu mapeie os serviços e preços de cada uma?",
  "status": "EM_CONVERSA",
  "acoes_executadas": [
    { "ferramenta": "pesquisar_concorrentes", "status": "sucesso", "resumo": "12 concorrentes" },
    { "ferramenta": "analisar_reviews_e_dores", "status": "sucesso", "resumo": "342 reviews" }
  ],
  "sugestoes": [
    "Mapear serviços e preços dos concorrentes",
    "Analisar demografia do bairro",
    "Buscar pontos comerciais disponíveis"
  ],
  "pode_gerar_relatorio": false,
  "dados_faltantes": ["area", "modelo_negocio"]
}
```

### Gerenciamento de Projeto

```http
GET    /api/consultor/projetos
GET    /api/consultor/projetos/{projeto_id}
PATCH  /api/consultor/projetos/{projeto_id}/arquivar
```

### Execução Manual de Ferramenta

```http
POST /api/consultor/projetos/{projeto_id}/acao

{
  "acao": "pesquisar_concorrentes",
  "parametros": { "raio_metros": 5000 }
}
```

### Consolidação para Relatório Formal

```http
POST /api/consultor/projetos/{projeto_id}/relatorio

{
  "incluir_secoes": ["concorrencia", "financeiro", "demografia"]
}
```

**Response:**
```json
{
  "relatorio_id": "rel-789",
  "status": "CONSOLIDANDO",
  "mensagem": "Estou montando seu Relatório Formal de Viabilidade. Assim que estiver pronto, te aviso aqui.",
  "link_acompanhamento": "/relatorios/rel-789"
}
```

### Upload e Extração de Anexos

```http
POST /api/consultor/anexos
Content-Type: multipart/form-data

-- file: <binary>
-- projeto_id: <uuid>
```

**Response:**
```json
{
  "anexo_id": "anx-999",
  "nome": "projeto_arquitetonico.pdf",
  "conteudo_extraido": "Área construída: 450m²...",
  "resumo_ia": "Projeto de academia com 450m², musculação e 2 salas de aula.",
  "entidades_extraidas": { "area_m2": 450, "salas_de_aula": 2 }
}
```

---

## Ferramentas/Capabilities (Function Calling)

O `consultor_engine.py` expõe estas funções ao LLM:

| Função | Agente Original | Quando é chamada |
|--------|----------------|------------------|
| `pesquisar_contexto_mercado(cidade, bairro, uf, tipo_negocio)` | A0 | "Como está o mercado lá?" / "Qual a renda do bairro?" |
| `buscar_pontos_comerciais(cidade, bairro, area_min, area_max, estacionamento)` | A1 | "Tem imóvel disponível?" / "Quanto custa alugar lá?" |
| `analisar_demografia(cidade, bairro, uf)` | A2 | "Quem mora no bairro?" / "Qual a idade média?" |
| `pesquisar_concorrentes(cidade, bairro, raio_metros, tipo_negocio)` | A3a | "Quem são os concorrentes?" |
| `analisar_reviews_e_dores(concorrentes, profundidade)` | A3b | "Qual a reclamação dos alunos?" / "O que falam no Google?" |
| `mapear_oferta_e_servicos(concorrentes, top_n)` | A3c | "Quais serviços eles oferecem?" / "Quanto cobram?" |
| `estimar_investimento(cidade, bairro, tipo_negocio, area_m2, tamanho_preset, publico_alvo)` | A4 | "Quanto custa abrir?" / "Qual o payback?" |
| `gerar_relatorio_formal(projeto_id, secoes)` | A6+A9 | "Gera o relatório completo" |
| `processar_anexo(storage_path, projeto_id)` | — | Usuário envia PDF/foto/planilha |

**Regras do Router:**
- Se o usuário pedir algo que já está no `UserProject`, o consultor **responde direto** sem chamar ferramenta.
- Se faltar dado obrigatório para a ferramenta (ex: não sabemos o bairro), o consultor pergunta antes de executar.
- Ferramentas dependentes são encadeadas automaticamente (ex: `analisar_reviews` recebe a lista do `pesquisar_concorrentes` do próprio projeto).

---

## Fluxos de Exemplo

### Fluxo 1: João Pessoa / Cabo Branco (Concorrência)

| Turno | Usuário | Ação do Consultor | Ferramentas |
|-------|---------|-------------------|-------------|
| 1 | *"Quero abrir uma academia em João Pessoa, bairro Cabo Branco. Não sei o modelo. Quero analisar concorrentes, serviços e reviews."* | Cria **Projeto** (cidade, bairro, uf=PB). Intenção: `analise_concorrencia`. | — |
| 2 | | *"Ótima escolha! O Cabo Branco é um bairro com alta renda per capita em João Pessoa. Vou pesquisar os concorrentes para você."* | `pesquisar_concorrentes()` |
| 3 | | *"Encontrei 12 academias na região. As principais redes são Smart Fit (3 unidades), Bio Ritmo (1) e 8 academias locais. A principal reclamação dos alunos é lotação no horário de pico (78% dos reviews negativos). Falta de estacionamento aparece em 45%. Quer que eu mapeie os serviços e preços de cada uma?"* | `analisar_reviews_e_dores()` |
| 4 | *"Sim, e quanto custa abrir lá?"* | *"Vou mapear a oferta dos concorrentes e calcular o investimento inicial. Como você ainda não definiu o tamanho, vou usar uma estimativa padrão de 800m² — depois ajustamos."* | `mapear_oferta_e_servicos()` + `estimar_investimento()` |
| 5 | *"Agora mostra pontos comerciais disponíveis"* | *"Encontrei 4 imóveis comerciais no Cabo Branco que se encaixam no perfil. O melhor scored é na Av. Cabo Branco, 450m², aluguel estimado R$ 12.000. Quer ver no mapa?"* | `buscar_pontos_comerciais()` |
| 6 | *"Gera o relatório completo"* | *"Vou consolidar tudo em um Relatório Formal de Viabilidade. Assim que estiver pronto, te aviso."* | `gerar_relatorio_formal()` → cria `relatorios` row → retorna link |

### Fluxo 2: Usuário com Anexo (PDF de Projeto Arquitetônico)

| Turno | Usuário | Ação do Consultor | Ferramentas |
|-------|---------|-------------------|-------------|
| 1 | Envia PDF + *"Meu projeto é para Recife"* | `processar_anexo()` extrai: 450m², 2 salas, vestiários. Cria **Projeto** com `area=450`, `tipo_negocio=academia`. | `processar_anexo()` |
| 2 | | *"Analisei seu projeto: 450m² com 2 salas de aula — é um ótimo tamanho para uma academia de bairro. Em Recife, o investimento inicial para esse porte gira em torno de R$ 850 mil a 1,2 milhão. Quer que eu pesquise em qual bairro de Recife?"* | — |
| 3 | *"Quero no Boa Viagem"* | Atualiza `localizacao`. Oferece pesquisas. | — |

---

## Regras de Implementação

### Backend (Python / FastAPI)

- **Validação:** todo request passa por schema Pydantic. Regras de negócio re-validadas no backend (P-005).
- **Ferramentas independentes:** cada função em `tools/*.py` deve ser testável isoladamente, sem depender do ADK `session.state`. Elas recebem parâmetros explícitos e retornam `dict` serializável.
- **Cascatas:** quando uma ferramenta depende de outra, o `consultor_engine.py` orquestra a sequência. Nunca expor dependência crua ao LLM.
- **Rate limiting:** endpoints de conversação e execução de ferramenta devem ter rate limit por `user_id`.
- **Observabilidade:** cada ferramenta loga tempo de execução, tokens consumidos e custo estimado em `project_messages` ou tabela de telemetria.

### Frontend (React / TypeScript)

- **Mobile-first:** o chat é a tela principal. A lista de projetos e o status de pesquisa devem ser acessíveis e legíveis em tela de 375px.
- **Estado refletido na URL (P-006):** `?projeto=550e-...` quando o usuário está vendo um projeto específico. F5 mantém contexto.
- **Anexos:** `ChatInput.tsx` já suporta upload visual. Adaptar para chamar `/api/consultor/anexos` e injetar `anexo_id` no próximo `conversar`.
- **Sugestões:** após cada resposta do consultor, renderizar botões clicáveis com as `sugestoes` — isso reduz fricção em mobile.
- **Polling de ações:** enquanto `status === 'PESQUISANDO'`, o frontend faz polling em `GET /api/consultor/projetos/{id}` a cada 3s, mostrando skeleton/card de "Pesquisando concorrentes...".

### Banco de Dados

- **Soft delete:** `user_projects.deleted_at` marca projeto arquivado. Nunca `DELETE` físico.
- **RLS:** toda query filtra por `auth.uid() = user_id`.
- **JSONB auditável:** `acoes` e `anexos` guardam timestamp de cada operação para reconstruir histórico.

---

## Decisões de Produto (DP)

| Código | Decisão | Justificativa |
|--------|---------|---------------|
| **DP-001** | Não exigir `modelo_negocio` completo para pesquisar concorrentes | O usuário inicinate não sabe o modelo ainda. A pesquisa de concorrência ajuda ele a decidir. |
| **DP-002** | Relatório formal é opcional, não obrigatório | O valor está na conversa e nas pesquisas pontuais. O relatório é um "upgrade" para quem precisa de documento. |
| **DP-003** | Ferramentas usam cache por bairro (7 dias) | Evita custo de API repetido. Se outro usuário pesquisou Cabo Branco ontem, reusamos. |
| **DP-004** | Anexos extraem entidades automaticamente | Se o usuário manda PDF com área=450m², o sistema pré-preenche o projeto sem perguntar. |
| **DP-005** | Respostas sempre com fonte citada | "78% dos reviews negativos" deve linkar ou mencionar "dados do Google Maps, coletados em 10/06/2026". |

---

## Pendências Críticas

- **Pend-1** — Escolha entre polling (3s) ou SSE/WebSocket para status de pesquisa. Recomendo **SSE** para melhor UX, mas polling é mais rápido de implementar na Fase 1.
- **Pend-2** — Política de cache: quanto tempo guardamos dados de concorrentes por bairro? Proposta: 7 dias para dados voláteis (reviews), 30 dias para dados estruturais (CNPJ, demografia).
- **Pend-3** — Limite de anexos por projeto: quanto armazenamento? Proposta: 50MB por projeto, 5 anexos no máximo.
- **Pend-4** — Modelo para extração de anexos: usar Gemini Vision direto ou pipeline OCR (Tesseract/pypdf) + LLM? Recomendo Gemini Vision para imagens/PDFs e pandas para planilhas.

---

## Plano de Implementação

### Fase 1 — Foundation (1-2 semanas)
1. Criar tabelas `user_projects` e `project_messages` (migration Supabase).
2. Criar `services/consultor/project_state.py` e `project_messages.py`.
3. Desacoplar A3a+A3b em `tools/competicao.py` (funções independentes).
4. Criar `services/consultor/consultor_engine.py` com router básico (sem Function Calling ainda — hardcoded por intenção).
5. Endpoint `POST /api/consultor/conversar` (mínimo viável: apenas pesquisa de concorrentes).
6. Adaptar frontend: `useConsultorChat.ts` + ajustes em `ChatInterface.tsx`.

### Fase 2 — Capabilities (2-3 semanas)
1. Desacoplar A0, A2, A1, A4 em `tools/*.py`.
2. Implementar Function Calling no `consultor_engine.py` (Gemini tools).
3. Endpoint `/api/consultor/anexos` com extração.
4. Componente `SuggestedActions.tsx` no frontend.
5. Tela `ProjetoDetailPage.tsx` (status do projeto).

### Fase 3 — Relatório (1-2 semanas)
1. Adaptar A6+A9 para consumir `UserProject` em vez de `session.state`.
2. Endpoint `POST /api/consultor/projetos/{id}/relatorio`.
3. Integrar com tela de acompanhamento `/relatorios/{id}/aguardando`.

### Fase 4 — Polish (1 semana)
1. Streaming SSE para atualizações em tempo real.
2. Cache inteligente por bairro (Redis).
3. Métricas: custo por projeto, tempo médio por ferramenta, taxa de conversão para relatório.
