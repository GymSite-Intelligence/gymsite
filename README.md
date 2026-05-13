# GymSite Intelligence

Pipeline multi-agente que avalia viabilidade comercial de pontos para academias no Brasil. Cruza dados de mercado, demografia (IBGE), concorrência (Google Maps), horários de pico e cenário financeiro num único relatório executivo — gerado em ~5 min por ~R$ 4,45 de custo de API.

> **Status:** produto end-to-end pronto pra demos com testers externos.
> Pipeline **A0 → A6** rodando em Vertex AI (`us-central1`), frontend Vite em `:5174`, dashboard `/custos` por org, multi-tenant via Supabase RLS.

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
│ A0 ContextBuilder      → Deep Research (Search Grounding)   │
│ A1 GeoScout            → Places API + Distance Matrix +     │
│                          listings OLX & ImovelWeb           │
│ A2 DemoAnalyst         → IBGE Censo 2022 (BigQuery)         │
│ A3a CompetitorSearch   → Places (Search Nearby)             │
│ A3b CompetitorAnalysis → LLM extrai dores das reviews ≤ 1a  │
│ A3c CompetitorMapper   → Top 10 balanceado + horários pico  │
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

Cada agente é um `LlmAgent` do Google ADK com **macro-tools consolidadas** (A1, A3a/b/c, A4, A5) que eliminam respostas MALFORMED. Estado do pipeline persiste em `state_diagnostics.jsonl` pra debug.

---

## Stack

| Camada      | Tech                                                          |
|-------------|---------------------------------------------------------------|
| LLM         | Gemini 2.5 Flash (default) + Gemini 2.5 Pro (consolidação)    |
| Orquestração | Google ADK (`google-adk>=1.3.0`)                              |
| Compute LLM | Vertex AI `us-central1` (cobrança em `gen-lang-client-0662901510`) |
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
│   ├── a3c_competitor_mapper.py
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
│   ├── deep_research_tool.py    Search Grounding (A0)
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
- Acesso ao projeto Supabase `cargo-flow-navigator` (schema GymSite vive lá)
- Service Account com role `Vertex AI User` no projeto `gen-lang-client-0662901510`

### Backend

```powershell
# 1. .env (a partir de .env.example) — preencher:
#    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_GYMSITE_ORG_ID
#    GOOGLE_API_KEY / GOOGLE_GENAI_USE_VERTEXAI=true
#    GOOGLE_APPLICATION_CREDENTIALS=C:\Users\...\gymsite-sa.json
#    MAPS_API_KEY ou GOOGLE_MAPS_API_KEY (ambos aceitos)
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
| Concorrentes            | Google Places API (New) — Search Nearby + Reviews       | API REST              | `tools/competitor_tools.py`            |
| Listings comerciais      | OLX (Lojas/Salas + Galpões) + ImovelWeb (Comerciais)    | Playwright Chromium headless (`page.evaluate`) | `tools/listing_tools.py` + `tools/imobiliaria_scraper.py` — ver [docs/listing_sources.md](docs/listing_sources.md) |
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

- **78%** em `ReportConsolidator` + `FinancialEstimator` (Gemini 2.5 Pro)
- Restante diluído em A0–A5 (Gemini 2.5 Flash) + Places API + Distance Matrix

Custos persistidos em `relatorios.custo_brl/tokens_total` e detalhados por agente em `relatorio_custos_agentes`. Dashboard `/custos` (visível a owner/admin) tem filtro por período, drill-down inline e (futuro) breakdown por org quando >1 tenant ativo.

---

## Roadmap

**Entregue (Run 22 + sessão maratona 2026-05-12):**
- Pipeline A0–A6 estável, sem MALFORMED, custo R$ 4,45
- Frontend completo: listagem, novo relatório, viewer, comparador, mapa, custos, perfil
- Auth email+senha + OTP, multi-tenant via RLS
- Vertex AI us-central1 + retry 30s/60s/120s em 429
- Horários de pico via SearchAPI (9/9 cobertura em testes)
- Delete de relatórios `failed` direto da UI

**Próximas issues (Linear VEC):**
- `#120` Dockerfile + deploy Cloud Run do backend
- `#121` Suíte pytest cobrindo agentes
- `#122` OrgDropdown (depende de **VEC-417** super-admin cross-org)
- `#125` Backend validar JWT no POST
- `#126` `run_id` ContextVar (multi-worker)
- **VEC-421** RAG fornecedores de equipamentos + frete real ANTT
- **VEC-424** Outscraper como Tier 1 quando free tier SearchAPI estourar

---

## Segurança

- API Keys e credenciais nunca em código — `.env` + Service Account JSON em `C:\Users\marce\.gcp\gymsite-sa.json` (gitignored)
- RLS por organização (`user_org_ids()`) em todas as tabelas
- Trigger `enforce_company_domain` no Supabase CFN aceita só domínio Vectra ou `app_metadata.origem='gymsite'`
- Backend usa `service_role` apenas pra escrita do pipeline; leituras do frontend passam por JWT do usuário
- Bucket `avatars` no Storage com RLS por folder (`{user_id}/...`)

---

## Licença

Proprietária — © 2026 Vectra Cargo / Navi Vectra. Todos os direitos reservados.

## Autor

Marcelo Rosas · `marcelo.rosas@vectracargo.com.br`
