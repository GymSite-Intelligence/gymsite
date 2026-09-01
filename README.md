# GymSite Intelligence

Pipeline multi-agente que avalia viabilidade comercial de pontos para academias no Brasil. Cruza dados de mercado, demografia (IBGE), concorrência (Google Maps), horários de pico e cenário financeiro num único relatório executivo — gerado em ~5 min por ~R$ 4,45 de custo de API.

> **Status:** produto end-to-end pronto pra demos com testers externos.
> Pipeline **A0 → A6** via **Gemini Developer API** (`GOOGLE_GENAI_USE_VERTEXAI=false`) — Deep Research no A0; frontend Vite em `:5174`, dashboard `/custos` por org, multi-tenant via Supabase RLS.
> Vertex está **OFF** (`GOOGLE_GENAI_USE_VERTEXAI=false`, `VERTEX_RAG_ENABLED=0`); pipeline usa Gemini API / NVIDIA e RAG via Eros + corpus local. Histórico: [docs/VERTEX_SETUP.md](docs/VERTEX_SETUP.md).

---

## O problema

Decidir onde abrir uma academia leva semanas e custa centenas de milhares de reais se errado. Quem expande hoje mistura intuição com planilhas, sem base estatística do bairro nem mapeamento real da concorrência. O GymSite Intelligence faz esse trabalho em minutos com saída estruturada e auditável (JSON canônico + Markdown + Supabase).

## O que entrega

Pra uma combinação `(cidade, bairro, área m², público alvo, tipo de negócio)`, o pipeline produz:

- **Top 3 candidatos** rankeados por score composto (físico, demográfico, competitivo, financeiro)
- **Dossiê demográfico** do bairro: faixa etária e densidade via IBGE Censo 2022 (REST estruturada); renda municipal calibrada com PNAD Contínua / Atlas Brasil via Search Grounding ao vivo (não fica preso ao snapshot do Censo)
- **Top 10 concorrentes** balanceados (≤ 4 redes A0 + ≥ 6 independentes) com avaliações, dores extraídas via LLM e curva de horários de pico
- **Cenário financeiro** com aluguel mediano, CAPEX por kit de equipamentos, break-even, payback e sensibilidade
- **Bairros alternativos** ranqueados quando o alvo não é ideal
- **Decisor** identificado e script de abordagem
- **Veredito final** (`APROVADO` / `COM RESSALVAS` / `INVESTIGAR MAIS` / `REPROVADO`)

---

## Arquitetura

```
Frontend (Vite/React :5174)
        │ JWT Supabase
        ▼
Backend FastAPI (api.py :8000)
        │ ADK Runner (background task)
        ▼
┌─────────────────────────────────────────────────────────────┐
│ A0 ContextBuilder      → Deep Research (Interactions API)   │
│ A1 GeoScout            → Places API + Distance Matrix +     │
│                          listings OLX & ImovelWeb           │
│ A2 DemoAnalyst         → IBGE Censo 2022 (BigQuery)         │
│ A3a CompetitorSearch   → Places textSearch (âncora bairro)  │
│ A3b CompetitorAnalysis → Dores/gaps/score + oferta (det.)   │
│ A4 FinancialEstimator  → Aluguel mediano + CAPEX + payback  │
│ A5 ContactHunter       → Decisor + script SPIN              │
│ A6 ReportConsolidator  → Veredito + persist Supabase        │
│ A7 MarketResearch      → Tendências macro (opcional)        │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
Supabase Postgres (RLS multi-tenant)
  relatorios · inputs · outputs · candidatos · competidores
  cenarios_financeiros · sensibilidade · bairros_alternativos
```

Cada agente é um `LlmAgent` do Google ADK com **macro-tools consolidadas** (A1, A3b/c, A4, A5) que eliminam respostas MALFORMED — exceção é o **A3a, hoje um `BaseAgent` determinístico (sem LLM)** que roda a macro direto. Estado do pipeline persiste em `state_diagnostics.jsonl` pra debug.

---

## Agentes do Pipeline (A0 – A7)

O pipeline é orquestrado por `root_agent` → `SequentialAgent("GymSitePipeline")` → sub-agentes especializados. A fase 2 (A2/A3/A4) roda em paralelo via `ParallelAgent`.

### A0 — ContextBuilder
**Arquivo:** `agents/a0_context_builder.py`  
**Modelo:** Gemini 3.6 Flash (thinking_budget=1024)  
**Input:** cidade, bairro, tipo_negocio, público alvo  
**Output:** `contexto_mercado` (JSON), `insights_deep_research`, `benchmarks_setor`

- Executa **Deep Research** qualitativo via `rodar_deep_research` (Gemini Interactions API) sobre o bairro/cidade.
- Cruza com dados quantitativos do parque ativo CNPJ/CNO via `dados_parque_cnpj_para_a0`.
- Não emite interpretação própria além dos dados retornados pelas tools.
- Introduzido na v0.4 como primeiro agente do pipe — substitui o "cold start" do A1.

### A1 — GeoScout
**Arquivo:** `agents/a1_geoscout.py`  
**Modelo:** Gemini 3.6 Flash  
**Input:** parâmetros de localização + contexto do A0  
**Output:** `candidatos` (top 3 imóveis), `score_ancoragem`, `polos_geradores`

- Refatorado em 2026-05-09 (VEC-379): 10 tools individuais foram consolidadas em **1 macro-tool** `analisar_pontos_comerciais_completo`.
- Motivo do refator: MALFORMED_FUNCTION_CALL quando o LLM reenviava lista de 30+ polos como argumento de `calcular_score_ancoragem`.
- Usa Google Maps (Places New, Geocoding, Street View), listings OLX/ImovelWeb via Playwright, e distance matrix.

### A2 — DemoAnalyst
**Arquivo:** `agents/a2_demo_analyst.py`  
**Modelo:** Gemini 3.6 Flash  
**Input:** cidade, bairro  
**Output:** `analise_demografica` (JSON)

- Refatorado em 2026-05-09: 5 tools sequenciais (buscar_municipio, buscar_populacao, estimar_faixa_etaria, buscar_renda, calcular_score_demografico) → **1 macro-tool** `analise_demografica_completa`.
- Reduz round-trips LLM de ~6 para 2 por run. Economia observada: ~165k tokens/run.
- Dados: IBGE Censo 2022 (`servicodados.ibge.gov.br`) + PNAD Contínua / Atlas Brasil via Search Grounding ao vivo.

### A3a — CompetitorSearch
**Arquivo:** `agents/a3a_competitor_search.py`  
**Modelo:** nenhum — **`BaseAgent` determinístico (sem LLM)** desde 2026-06-14  
**Input:** coordenadas do bairro + tipo_negocio  
**Output:** `concorrentes_brutos` (lista de academias)

- Sub-agente da fase competitiva (ex-A3 monolítico). Separação evita estouro do AFC=10 do Gemini.
- **BaseAgent determinístico:** roda a macro `analisar_concorrentes_a3a_completo` direto e grava `concorrentes_brutos` no state via `state_delta`. Substitui o antigo `LlmAgent` que só ecoava o JSON da macro de volta pelo `output_key` (economia ~83k tokens/relatório, medida em `metrics/tokens_pipeline.csv`).
- Responsável **APENAS** por buscar academias concorrentes, processar reviews e fazer enrichment via Google Knowledge Panel + Search Grounding.
- **Descoberta ancorada no BAIRRO** (atrás da flag `CONCORRENTES_SOURCE=parque`, função `_descobrir_concorrentes_bairro`): Places **textSearch** com query `"{tipo_negocio} {bairro} {cidade} {uf}"` + filtro de `types` fitness (`gym`/`fitness_center`) + filtro de bairro no endereço. Motivo: a antiga Places Search Nearby (raio 3km) ancorava errado e puxava academias de bairros adjacentes. A **Nearby 3km virou fallback** (e contexto de densidade regional); o **parque CNPJ virou só CROSS de contato** (cnpj/telefone), não mais base de descoberta.
- NÃO faz análise agregada — isso é do A3b.
- Macro-tool: `analisar_concorrentes_a3a_completo` (consolida busca + reviews + enrichment).

### A3b — CompetitorAnalysis
**Arquivo:** `agents/a3b_competitor_analysis.py`  
**Modelo:** nenhum — **`BaseAgent` determinístico (sem LLM)** desde 2026-06  
**Input:** `concorrentes_brutos` do A3a (via session state)  
**Output:** `inteligencia_competitiva`, `oferta_concorrentes`, `score_concorrencia`, `posicionamento_recomendado`, `estrategia_counter_programming`

- Recebe os dados brutos do A3a e produz:
  - Gaps competitivos, dores nominadas e oportunidades
  - Estratégia de counter-programming (picos/vales de horário)
  - Score numérico de saturação
  - Posicionamento recomendado para o novo negócio
- **Absorveu o antigo A3c (jun/2026):** no mesmo passo determinístico mapeia a oferta de cada concorrente — **site oficial via httpx + Instagram via SearchAPI `engine=instagram_profile`** (sem Playwright/Outscraper) — e **mescla as modalidades em `servicos_oferecidos` por concorrente**, gravando `oferta_concorrentes` no state. Isso evita gap falso na ERRC do A9 (recomendar "criar" algo que o concorrente já oferece).
- **BaseAgent determinístico:** roda as macros direto e grava via `state_delta`. Substitui o `LlmAgent`-eco que crashava com `MALFORMED_FUNCTION_CALL` e dropava campos.
- NÃO faz busca — consome apenas o state do A3a.

### A4 — FinancialEstimator
**Arquivo:** `agents/a4_financial_estimator.py`  
**Modelo:** Gemini 3.6 Flash  
**Input:** candidatos, demografia, contexto de mercado  
**Output:** `cenarios_financeiros` (3 cenários: low/mid/premium), `aluguel_estimado`, `payback`, `viabilidade`

- Refatorado em Run 20 (Task #56): substituídas 2 tools por **1 macro-tool** `analise_financeira_a4_completo`.
- Resolveu MALFORMED_FUNCTION_CALL no cenário Pro (Run 20 / 5d7d92c738d8).
- Calcula CAPEX por kit de equipamentos (`tools/kits_equipamentos.py`), frete ANTT (`tools/antt_tools.py`), aluguel mediano via Search Grounding, e payback em 3 cenários.

### A5 — ContactHunter
**Arquivo:** `agents/a5_contact_hunter.py`  
**Modelo:** Gemini 3.6 Flash  
**Input:** top candidato + contexto do negócio  
**Output:** `contato_decisor`, `script_abordagem`, `tipo_ponto`

- Refatorado (Task #57): 4 tools → **1 macro-tool** `gerar_contato_decisor_completo`.
- Reduz custo de ~112k tokens (27% do custo total) para ~30k tokens.
- Identifica tipo de ponto (imobiliária, proprietário direto, shopping), busca CNPJ relacionado, gera script de abordagem no formato SPIN, e formata contato para WhatsApp.
- Fix 2026-05-12: `after_agent_callback` detecta state vazio (LLM emitia 0 tokens após tool call) e previne `contato_decisor: {}` na DB.

### A6 — ReportConsolidator
**Arquivo:** `agents/a6_report_consolidator.py`  
**Modelo:** Gemini 3.6 Flash (thinking alto)  
**Input:** outputs de A0–A5 via session state  
**Output:** `relatorio_executivo` (markdown), `veredito`, `bairros_alternativos`, `alertas`

- Sintetiza outputs de 5 agentes anteriores, decide bairros alternativos quando `score_geral < 6`, escolhe o veredito final e renderiza tabelas complexas com regras condicionais.
- Persiste no Supabase via `UPDATE` (relatório stub já criado pelo `api.py` antes do pipeline iniciar).
- Suporta **Modo Crowdsource**: se o usuário informar bairros indicados por terceiros, renderiza seção especial "📣 Demanda Social Detectada".
- Telemetria: registra tokens reais por agente em `metrics/tokens_pipeline.csv`.

### A7 — MarketResearch
**Arquivo:** `agents/a7_market_research.py`  
**Modelo:** Gemini 3.6 Flash  
**Input:** pergunta livre do usuário sobre tendências macro  
**Output:** resposta com fontes (Search Grounding)

- Agente isolado — **não pode ter outras tools além de `google_search`** (limitação ADK/Gemini).
- Acionado pelo root_agent quando o usuário pede pesquisa de mercado em tempo real OU quando o Playwright scraper falha em capturar horários de pico do Knowledge Panel.
- Não faz parte do pipeline sequencial padrão (A0→A6). É chamado on-demand.

---

## Stack

| Camada      | Tech                                                          |
|-------------|---------------------------------------------------------------|
| LLM         | Gemini 3.6 Flash (default) + Gemini 3.6 Flash (consolidação)    |
| Orquestração | Google ADK (`google-adk>=1.3.0`)                              |
| Compute LLM | Gemini Developer API (`GOOGLE_API_KEY`) / NVIDIA (`PIPELINE_LLM_PROVIDER=nvidia`); Vertex OFF (`GOOGLE_GENAI_USE_VERTEXAI=false`) |
| Backend     | FastAPI + Uvicorn, Python 3.12                                |
| Banco       | Supabase Postgres (mesmo cluster do CFN), RLS multi-org       |
| Dados ext.  | Google Maps Platform (Places, Distance Matrix, Street View) · IBGE Censo 2022 (REST `servicodados`) · PNAD/Atlas via Search Grounding · SearchAPI Tier 0 (horários de pico) · **OLX + ImovelWeb** (listings comerciais via Playwright headless — ver [docs/listing_sources.md](docs/listing_sources.md)) |
| Frontend    | Vite 6 + React 18 + TypeScript + Tailwind + shadcn/ui + TanStack Router/Query |
| Mapas UI    | `pigeon-maps` (OSM tiles, sem chave)                          |
| Forms       | React Hook Form + Zod                                         |

---

## Estrutura do repo

```
gymsite_intelligence/
├── api.py                       FastAPI :8000
├── gymsite_intelligence/        package root (orchestrator ADK)
│   └── agent.py
├── agents/                      A0..A7 LlmAgents
│   ├── a0_context_builder.py
│   ├── a1_geoscout.py
│   ├── a2_demo_analyst.py
│   ├── a3a_competitor_search.py
│   ├── a3b_competitor_analysis.py
│   ├── a4_financial_estimator.py
│   ├── a5_contact_hunter.py
│   ├── a6_report_consolidator.py
│   └── a7_market_research.py
├── tools/                       Wrappers de APIs externas + utilitários
│   ├── _genai_client.py         centraliza Vertex/API key
│   ├── maps_tools.py            Places, Geocoding, Street View
│   ├── distance_matrix_tools.py
│   ├── competitor_tools.py
│   ├── ibge_tools.py            BigQuery IBGE 2022
│   ├── financial_tools.py
│   ├── popular_times_tool.py    cascata SearchAPI → lib → Playwright
│   ├── deep_research_tool.py    Interactions API Deep Research + fallback (A0)
│   ├── benchmarks_tool.py
│   ├── kits_equipamentos.py     CAPEX por kit
│   ├── pricing.py               tabela Gemini + Maps SKUs + câmbio
│   └── state_diagnostics.py     dump JSONL por agente
├── db/
│   ├── schema.sql               9 tabelas + RLS + views
│   ├── seed.sql
│   └── supabase_writer.py       adapter A6 → Supabase
├── frontend/                    Vite/React :5174 (app independente)
│   └── src/{routes,components,hooks,lib,types,mocks}
├── tests/                       pytest (smoke + integração)
├── docs/                        VERTEX_SETUP.md + prompts/
└── .env.example
```

---

## Como rodar

### Pré-requisitos

- Python 3.12+
- Node.js 20+ (pnpm/npm)
- Acesso ao projeto Supabase `<SUPABASE_PROJECT>` (schema GymSite vive lá)
- `GOOGLE_API_KEY` (Gemini Developer API — padrão atual)
- (Opcional, Vertex) Service Account com role `Vertex AI User` — ver [docs/VERTEX_SETUP.md](docs/VERTEX_SETUP.md)

### Backend

```powershell
# 1. .env (a partir de .env.example) — preencher:
#    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_GYMSITE_ORG_ID
#    GOOGLE_API_KEY=...  e  GOOGLE_GENAI_USE_VERTEXAI=false  (padrão — Deep Research no A0)
#    (Vertex, opcional) GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_APPLICATION_CREDENTIALS=...
#    GOOGLE_MAPS_API_KEY (Places New, Geocoding, pipeline; ver .env.example)
#    SEARCHAPI_KEY (horários de pico, free tier)

# 2. Instalar deps
pip install -r requirements.txt

# 3. Subir o servidor
python -m uvicorn api:app --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev   # :5174
```

`.env` do frontend precisa de `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` + `VITE_API_BASE=http://localhost:8000`.

### Login

Email + senha (default) ou OTP código no email. Trigger CFN aceita usuários com `app_metadata.origem = 'gymsite'` mesmo fora de `@vectracargo.com.br`. Convidar tester via:

```powershell
python tools/admin_invite_tester.py --email novo@empresa.com --role admin
```

---

## Modelo de banco

9 tabelas em Postgres com `on delete cascade` no `relatorios.id`:

| Tabela                     | Cardinalidade | Conteúdo                              |
|----------------------------|---------------|---------------------------------------|
| `organizations`            | -             | Multi-tenant root                     |
| `organization_members`     | N:N (user×org) | Roles: owner/admin/member             |
| `relatorios`               | 1 por análise | Header (status, custo_brl, tokens)    |
| `relatorio_inputs`         | 1:1           | Formulário (cidade, área, público)    |
| `relatorio_outputs`        | 1:1           | Veredito, markdown_completo, scores   |
| `candidatos`               | N:1           | Top 3 imóveis com lat/lon             |
| `competidores`             | N:1           | Top 10 academias do raio              |
| `cenarios_financeiros`     | N:1           | Conservador/base/otimista             |
| `sensibilidade_cenarios`   | N:1           | Stress tests (-20% receita etc.)      |
| `bairros_alternativos`     | N:1           | Ranking de bairros melhores           |

RLS via função `user_org_ids()` → todas as filhas usam policy `"X follow relatorio"` que herda do header. View `v_relatorios_resumo` é flat (uma linha por relatório) e usa `security_invoker=true`.

---

## Modelo de score

Cada candidato recebe 4 sub-scores (0–10) e um composto:

| Dimensão      | Peso | O que mede                                                 |
|---------------|------|-------------------------------------------------------------|
| Físico        | 20%  | Térreo, área disponível, estacionamento, fachada            |
| Demográfico   | 30%  | % 18–45 anos, renda per capita, densidade, crescimento      |
| Competitivo   | 25%  | Saturação, gap de mercado, dores dos concorrentes           |
| Financeiro    | 25%  | Aluguel/m², CAPEX kit, payback, break-even                  |

Veredito final por faixa do composto: `≥8 APROVADO`, `≥6 COM RESSALVAS`, `≥4 INVESTIGAR MAIS`, `<4 REPROVADO`.

---

## Fontes de dados — em uso vs roadmap

Cada agente combina dados estruturados (APIs com schema fixo) com **Search Grounding dinâmico** (Gemini consulta fontes ao vivo) pra evitar valores hardcoded que envelhecem rápido. O quadro abaixo é o estado real:

### Já em uso

| Dimensão               | Fonte                                                 | Tipo                  | Onde no código                         |
|------------------------|-------------------------------------------------------|-----------------------|----------------------------------------|
| Demografia              | IBGE Censo 2022 via `servicodados.ibge.gov.br`         | API REST estruturada  | `tools/ibge_tools.py`                  |
| Renda município         | PNAD Contínua / IBGE Cidades / Atlas Brasil            | Search Grounding (LLM) | `tools/ibge_tools.py:252-341`          |
| Benchmarks setoriais    | Panorama ACAD / IHRSA / SEBRAE                          | Search Grounding (LLM) | `tools/benchmarks_tool.py`             |
| Aluguel mediano         | Anúncios e portais imobiliários ao vivo                 | 3 queries Search Grounding paralelas | A4 `financial_estimator`          |
| Concorrentes            | Google Places API (New) — **textSearch âncora bairro** + Reviews (Nearby 3km = fallback) | API REST              | `tools/competitor_tools.py`            |
| Listings comerciais      | OLX (Lojas/Salas + Galpões) + ImovelWeb (Comerciais)    | Playwright Chromium headless (`page.evaluate`) | `tools/listing_tools.py` + `tools/imobiliaria_scraper.py` — ver [docs/listing_sources.md](docs/listing_sources.md) |
| Investigação de imóvel   | Gemini grounded (o que opera no endereço)               | A1 pós-listings, até 5/disparo                 | [INVESTIGACAO_IMOVEL.md](docs/INVESTIGACAO_IMOVEL.md) |
| Enriquecimento (PRD)     | CNJ Justiça Aberta (CNS) + portais comerciais           | Roadmap — ver PRD                              | [PRD-ENRIQUECIMENTO-IMOVEIS.md](docs/PRD-ENRIQUECIMENTO-IMOVEIS.md) |
| Horários de pico        | SearchAPI free tier (Tier 0) → lib → Playwright         | Cascata               | `tools/popular_times_tool.py`          |
| CAPEX equipamentos       | `tools/kits_totais.json` (catálogo estático)            | JSON local            | `tools/kits_equipamentos.py`           |
| Frete equipamentos       | ANTT Resolução 6.034 com origem heurística              | Tabela local          | `tools/antt_tools.py`                  |
| Distâncias/rotas         | Google Distance Matrix API                              | API REST              | `tools/distance_matrix_tools.py`       |
| Decisor do imóvel        | Search Grounding + Receita Federal                      | LLM + API             | `tools/contact_tools.py`               |

### Limitações conhecidas e roadmap

| Limitação atual                                       | Fonte sugerida                  | Status                                              |
|------------------------------------------------------|---------------------------------|-----------------------------------------------------|
| CAPEX usa mediana sem catálogo real do fornecedor    | RAG fornecedores via pgvector   | [VEC-421](https://linear.app/vectra-cargo/issue/VEC-421) — backlog |
| Frete ANTT usa origem heurística (default SP)        | Origem real do fornecedor       | [VEC-421](https://linear.app/vectra-cargo/issue/VEC-421) — backlog |
| Aluguel via texto livre Search Grounding              | **FipeZap** (índice mensal por bairro) | proposto como extensão da [VEC-421](https://linear.app/vectra-cargo/issue/VEC-421) |
| Sem variáveis macro no cálculo financeiro             | **BCB/SGS** (Selic, IPCA mensal) | proposto como extensão da [VEC-421](https://linear.app/vectra-cargo/issue/VEC-421) |
| Vitalidade econômica regional não considerada         | **PIB municipal SIDRA 2023**     | proposto como extensão da [VEC-421](https://linear.app/vectra-cargo/issue/VEC-421) |
| Concorrentes mapeados só via Places (caro em rajada)  | **CEMPRE/CNAE 9313-1/00** (SIDRA) pré-triagem | proposto como extensão da [VEC-378](https://linear.app/vectra-cargo/issue/VEC-378) |
| POIs/rotas só via Google (custo recorrente)           | **OpenStreetMap / Overpass API** | proposto como extensão da [VEC-378](https://linear.app/vectra-cargo/issue/VEC-378) |
| Sem validação de zoneamento do candidato              | **Plano Diretor municipal** (geosampa, pcrj, mapas fortaleza, ippuc) | proposto como extensão da [VEC-378](https://linear.app/vectra-cargo/issue/VEC-378) |
| Score regional sem panorama socioeconômico amplo       | **Portal Cidades@ IBGE** + **Atlas Desenvolvimento Humano** | proposto como extensão da [VEC-421](https://linear.app/vectra-cargo/issue/VEC-421) |
| Vitalidade comercial regional não captada              | **PAC 2023** (Pesquisa Anual Comércio) + **PAS 2023** (Serviços) — SIDRA | proposto como extensão da [VEC-421](https://linear.app/vectra-cargo/issue/VEC-421) |
| Censo 2022 por setor censitário publicação progressiva | Tabelas SIDRA saindo escalonadas (Trabalho/Rendimento out/2025, Favelas dez/2025, Etnias 2025) — A2 consulta API REST que reflete o publicado | limitação intrínseca (não há mitigação) |
| "Crescimento do bairro" sem fonte projetiva           | Estimativas IBGE 2025 + Censo 2010↔2022 diff | sem VEC ativa                          |
| `score_acessibilidade` heurístico                     | GTFS municipal (SPTrans, BNTU)   | sem VEC ativa                                       |
| A5 ContactHunter sem sócios formais                   | JUCESP/JUCERJ + **CNPJ.ws** (fallback Receita) | sem VEC ativa                              |
| A5 ContactHunter sem histórico de propriedade          | **Registro de Imóveis / CNJ** (`registrodeimoveis.org.br`) | sem VEC ativa                                  |

Pra granularidade por setor censitário do Censo 2022, a publicação SIDRA está progressiva: Trabalho e Rendimento saiu out/2025; Favelas e Comunidades dez/2025; Etnias 2025. O A2 (DemoAnalyst) consulta a API REST do IBGE que reflete o que estiver publicado no momento.

## Custos

Pipeline atual gasta em média **R$ 4,45 por relatório** (10 concorrentes + horários de pico via SearchAPI free):

- **78%** em `ReportConsolidator` + `FinancialEstimator` (Gemini 3.6 Flash)
- Restante diluído em A0–A5 (Gemini 3.6 Flash) + Places API + Distance Matrix

Custos persistidos em `relatorios.custo_brl/tokens_total` e detalhados por agente em `relatorio_custos_agentes`. Dashboard `/custos` (visível a owner/admin) tem filtro por período, drill-down inline e (futuro) breakdown por org quando >1 tenant ativo.

---

## Roadmap

**Entregue (Run 22 + sessão maratona 2026-05-12):**
- Pipeline A0–A6 estável, sem MALFORMED, custo R$ 4,45
- Frontend completo: listagem, novo relatório, viewer, comparador, mapa, custos, perfil
- Auth email+senha + OTP, multi-tenant via RLS
- Deep Research A0 via Interactions API; retry 30s/60s/120s em 429 no `api.py`
- Vertex AI = legado OFF; `VERTEX_SETUP.md` é histórico (não é o padrão)
- Horários de pico via SearchAPI (9/9 cobertura em testes)
- Delete de relatórios `failed` direto da UI
- A3 ancorado no bairro + A3a determinístico (2026-06-15)

**Próximas issues (Linear VEC):**
- `#120` Dockerfile + deploy do backend (hoje Hetzner VPS; Cloud Run deprecado)
- `#121` Suíte pytest cobrindo agentes
- `#122` OrgDropdown (depende de **VEC-417** super-admin cross-org)
- `#125` Backend validar JWT no POST
- `#126` `run_id` ContextVar (multi-worker)
- **VEC-421** RAG fornecedores de equipamentos + frete real ANTT
- **VEC-424** Outscraper como Tier 1 quando free tier SearchAPI estourar

---

## Segurança

- API Keys e credenciais nunca em código — `.env` + Service Account JSON em `<PATH_TO_SA_JSON>` (gitignored)
- RLS por organização (`user_org_ids()`) em todas as tabelas
- Trigger `enforce_company_domain` no Supabase CFN aceita só domínio Vectra ou `app_metadata.origem='gymsite'`
- Backend usa `service_role` apenas pra escrita do pipeline; leituras do frontend passam por JWT do usuário
- Bucket `avatars` no Storage com RLS por folder (`{user_id}/...`)

---

## Licença

Proprietária — © 2026 Vectra Cargo / Navi Vectra. Todos os direitos reservados.

## Autor

Marcelo Rosas · `<CONTACT_EMAIL>`
