# Stack Técnica — GymSite Intelligence

Catálogo de referência de tudo que roda no projeto: linguagens, bibliotecas, serviços, banco e infraestrutura. Escrito em português simples para consulta rápida antes de começar trabalho novo.

> **Como ler:** cada item tem nome, versão (quando dá pra saber pelo repo) e uma linha explicando pra que serve. Coisas que eu não consegui confirmar 100% pelos arquivos estão marcadas com **(a confirmar)**.

Em uma frase: é uma plataforma que gera **relatórios de viabilidade para academias**. O miolo é um **backend Python (FastAPI)** que roda uma **fila de agentes de IA (Google ADK, A0→A9)** cruzando dados de CNPJ, CNO, Google Maps e finanças; o resultado aparece num **site React** e vira **PDF**. Tudo guardado no **Supabase (Postgres)**; API + worker publicados em **Hetzner VPS (Docker + Cloudflare Tunnel)** e o front no **Cloudflare Pages**.

---

## Backend

Linguagem: **Python 3.11+** (`requires-python = ">=3.11"` no `pyproject.toml`; imagem Docker `python:3.11-slim`). O app entra por `api.py` (FastAPI) e um serviço "worker" que roda a fila de relatórios em background.

Dependências de `requirements.txt` / `pyproject.toml`:

| Pacote | Versão (mínima) | Pra que serve (em português) |
|---|---|---|
| `google-adk` | >=1.3.0 | Motor que orquestra os agentes de IA (a fila A0→A9). É o coração do pipeline. |
| `google-genai` | >=0.3.0 | Cliente direto do Gemini (usado por `tools/` fora do ADK). |
| `fastapi` | >=0.110.0 | Framework da API web (todos os endpoints `/api/...`). |
| `uvicorn[standard]` | >=0.27.0 | Servidor que segura a API no ar. |
| `starlette` | >=0.36.0 | Base do FastAPI; usado direto nos middlewares. |
| `pydantic[email]` | >=2.0.0 | Valida e tipa os dados de entrada/saída. O extra `[email]` é obrigatório pro campo de e-mail em leads. |
| `supabase` | >=2.0.0 | Cliente do banco/Supabase (grava relatórios, lê dados). |
| `httpx` | >=0.27.0 | Cliente HTTP assíncrono (chamadas a APIs externas). |
| `python-dotenv` | >=1.0.0 | Carrega variáveis de ambiente do `.env`. |
| `googlemaps` | >=4.10.0 | SDK oficial do Google Maps Platform. |
| `playwright` | >=1.40.0 | Navegador automatizado pra scraping de portais imobiliários (**legado**, fora do caminho crítico — ver Fontes de Dados). |
| `beautifulsoup4` | >=4.12.0 | Lê/parseia HTML (mapeamento de oferta de concorrentes). |
| `pandas` | >=2.0.0 | Processa tabelas/planilhas (ex.: índices FipeZap). |
| `openpyxl` | >=3.1.0 | Lê arquivos Excel (`.xlsx`). |
| `reportlab` | >=4.0.0 | Gera PDF do relatório (motor programático). |
| `weasyprint` | >=60.0 | Gera PDF a partir de HTML/CSS (motor de produção; exige libs de fonte no container). |
| `matplotlib` | >=3.8.0 | Desenha os gráficos que entram no relatório. |
| `jinja2` | >=3.1.0 | Monta os templates HTML do relatório. |
| `redis` | >=5.0.0 | Fila de jobs, cache e rate-limit (ver Redis em Infra). |
| `langcache` | >=0.12.0 | Cache semântico de respostas de LLM (economiza chamadas repetidas ao Gemini). |
| `google-cloud-bigquery` | >=3.0.0 | Lê dados públicos nacionais (rota Base dos Dados / CNO). |
| `google-cloud-discoveryengine` | >=0.13.0 | Vertex AI Search (Discovery Engine) — **legado, OFF** (`VERTEX_RAG_ENABLED=0`). RAG hoje = Eros (`knowledge-ask`) + corpus local. |
| `opentelemetry-api` / `opentelemetry-sdk` | >=1.25.0 | Telemetria/observabilidade (traces exportados, ex.: Grafana). |
| `packaging` | >=24.0 | Utilitário de versões. |
| `tinker` | (sem pin) | Inferência e fine-tuning de LLMs (Thinking Machines) — usado por `services/tinker_bot.py`, modelo base `Qwen/Qwen3-8B`. |

**Dev (opcional):** `pytest` (>=7.0.0) para testes; `pyrefly` (>=0.46) para checagem de tipos. No CI também aparecem `ruff` (lint) e `mypy` (tipos).

---

## Frontend

App React SPA em `frontend/`. Node **22** no build (imagem `node:22-alpine`), servido em produção por **nginx** (`nginxinc/nginx-unprivileged:1.27-alpine`).

**Núcleo e build:**

| Item | Versão | Pra que serve |
|---|---|---|
| `react` / `react-dom` | ^18.3.1 | Biblioteca de interface. |
| `typescript` | ~5.6.2 | Tipagem estática (o "lint" do front é `tsc --noEmit`). |
| `vite` | ^6.3.5 | Empacotador/servidor de desenvolvimento. |
| `@vitejs/plugin-react` | ^4.3.4 | Plugin do React no Vite. |

**Roteamento, dados e estado:**

| Item | Versão | Pra que serve |
|---|---|---|
| `@tanstack/react-router` | ^1.62.0 | Rotas/páginas do app. |
| `@tanstack/react-query` | ^5.59.0 | Busca de dados da API e cache (invalidação após mutações). |
| `@tanstack/react-table` | ^8.21.3 | Tabelas de dados (listas, oportunidades). |
| `zustand` | ^5.0.0 | Estado global leve. |
| `@supabase/supabase-js` | ^2.45.0 | Cliente do Supabase no navegador (auth + leitura filtrada por org). |
| `zod` | ^3.25.76 | Validação de dados no front (par do Pydantic no back). |
| `react-hook-form` + `@hookform/resolvers` | ^7.75 / ^3.10 | Formulários com validação (integra Zod). |

**UI / estilo:**

| Item | Versão | Pra que serve |
|---|---|---|
| `tailwindcss` + `@tailwindcss/vite` | ^4.3.0 | CSS utilitário (design system). |
| `radix-ui` + vários `@radix-ui/react-*` | ^1.x | Componentes acessíveis (dialog, dropdown, tooltip, collapsible). |
| `shadcn` | ^4.8.0 | Coleção de componentes prontos sobre Radix + Tailwind. |
| `lucide-react` | ^0.460.0 | Ícones. |
| `recharts` | ^3.8.0 | Gráficos na interface. |
| `sonner` | ^2.0.7 | Notificações/toasts (o projeto proíbe `alert()`). |
| `next-themes` | ^0.4.6 | Alternância de tema claro/escuro. |
| `@fontsource-variable/geist` | ^5.2.9 | Fonte Geist. |
| `class-variance-authority`, `clsx`, `tailwind-merge`, `tw-animate-css`, `tailwindcss-animate`, `vaul` | vários | Utilitários de estilo, variantes e animação. |
| `@dnd-kit/*` | ^6/^9/^10 | Arrastar-e-soltar (ordenar itens). |

**Mapas e geo (frontend):**

| Item | Versão | Pra que serve |
|---|---|---|
| `@googlemaps/js-api-loader` + `@types/google.maps` | ^1.16 / ^3.58 | Carrega o Google Maps JS (mapa e autocomplete). |
| `@deck.gl/core`, `@deck.gl/aggregation-layers`, `@deck.gl/google-maps` | ^9.3.3 | Camadas de visualização (heatmap/densidade sobre o mapa). |
| `pigeon-maps` | ^0.22.1 | Mapa alternativo via OpenStreetMap (fallback sem chave Google). |

**PDF / conteúdo (frontend):**

| Item | Versão | Pra que serve |
|---|---|---|
| `html2pdf.js` | ^0.14.0 | Exporta conteúdo da tela em PDF no navegador. |
| `react-markdown` + `remark-gfm` | ^10 / ^4 | Renderiza texto em Markdown (respostas do chat/consultor). |
| `qrcode` + `@types/qrcode` | ^1.5 | Gera QR Code (ex.: acesso a relatório). |

---

## Pipeline de Agentes

O pipeline é montado com o **Google ADK** em `gymsite_intelligence/agent.py`. Os agentes vivem em `agents/`. A fábrica canônica `tools/agent_factory.py` cria cada `LlmAgent` já com **retry no modelo** (429/503/500 retentam a chamada, não a pipeline inteira) e **telemetria de tokens**.

**Como é orquestrado:**
- `SequentialAgent GymSitePipeline`: A0 → A1 → (análise paralela) → A6 → A9.
- `ParallelAgent ParallelAnalysis`: roda A2 (demografia), o sub-pipeline competitivo (A3a→A3b) e A4 (financeiro) ao mesmo tempo.
- `SequentialAgent CompetitorPipeline`: A3a (busca) → A3b (análise + oferta).
- `root_agent GymSiteIntelligence` é o ponto de entrada do ADK, com o `pipeline` como sub-agente.

| Agente | Arquivo | Tipo | Pra que serve |
|---|---|---|---|
| **A0** ContextBuilder | `a0_context_builder.py` | LLM (`gemini-3.6-flash`) | Contexto de mercado via Deep Research + CNPJ/OSM. |
| **A1** GeoScout | `a1_geoscout.py` | Determinístico (sem LLM) | Localização e leitura geoespacial do ponto. |
| **A2** DemoAnalyst | `a2_demo_analyst.py` | Determinístico | Análise demográfica do bairro/entorno. |
| **A3a** CompetitorSearch | `a3a_competitor_search.py` | Determinístico | Busca concorrentes via SearchAPI (`engine=google_maps`). |
| **A3b** CompetitorAnalysis | `a3b_competitor_analysis.py` | Determinístico | Gaps/dores/score + mapeia oferta (site + Instagram). Absorveu o antigo A3c. |
| ~~A3~~ CompetitorIntel | `a3_competitor_intel.py` | LLM (`gemini-3.6-flash`) | **DEPRECATED** — monolítico substituído por A3a+A3b. |
| **A4** FinancialEstimator | `a4_financial_estimator.py` | Determinístico | Viabilidade financeira; aluguel vem do MRLR (não de listing raspado). |
| **A5** ContactHunter | `a5_contact_hunter.py` | Determinístico | Contato de decisores — **fora da viabilidade**, usado na rota de prospecção. |
| **A6** ReportConsolidator | `a6_report_consolidator.py` | LLM (`gemini-3.6-flash` / `flash`) | Consolida tudo no relatório final. |
| **A7** MarketResearch | `a7_market_research.py` | LLM (`gemini-3.6-flash`) | Pesquisa de mercado; importado como função dentro de A3a/A4. |
| **A8** Validator | `a8_validator.py` | Validação cruzada | Confere invariantes entre agentes (ex.: A4 × A9) após A6. Roda via `tools/a8_runner.py`. |
| **A9** PositioningStrategist | `a9_positioning_strategist.py` | LLM (`gemini-3.6-flash`) | Posicionamento estratégico (framework ERRC / oceano azul); usa LangCache. |

**Runner alternativo do site:** `agents_site/runner.py` roda `agents_site.root_agent` (5 especialistas) como motor da "degustação" da landing page, atrás da flag `SITE_AGENT_ENGINE=adk` (default `legacy`).

**Provedores de modelo:**

| Provedor / Modelo | Onde é usado | Observação |
|---|---|---|
| **Gemini** (`gemini-3.6-flash`) | Padrão de todo o pipeline ADK | `GOOGLE_GENAI_MODEL=gemini-3.6-flash`. `gemini-2.5-*` deprecado (alias → 3.6). |
| **Vertex AI** | Alternativa ao Gemini via chave | Ligado por `GOOGLE_GENAI_USE_VERTEXAI` (default `false`). |
| **Deep Research** (`deep-research-preview-04-2026`) | A0 / research | Fallback para `gemini-3.6-flash`. |
| **Kimi / Moonshot / Groq / Ollama** | `tools/kimi_research.py`, `openclaw_kimi_server.py` | Pesquisa web opcional do A0 (`A0_RESEARCH_PROVIDER=auto\|gemini\|kimi`). Ollama local roda `llama3.2:3b`. |
| **Tinker** (`Qwen/Qwen3-8B`) | `services/tinker_bot.py` | Inferência/fine-tuning; fallback `gemini-3.6-flash`. |
| **Qwen (metodologia)** | catálogos/`data/market_waves.csv` → `tier_qwen` | Hoje é **taxonomia/documentação**, não chamada de modelo ao vivo (a confirmar como fase futura). |

---

## Fontes de Dados / APIs Externas

| Fonte / API | Onde no repo | Pra que serve |
|---|---|---|
| **SearchAPI** (`SEARCHAPI_KEY`) | `listing_cascata.py`, tools de reviews/imóveis, A3a | Backend **primário** de concorrentes (Google Maps, ~4× mais barato que Places) e de imóveis/pontos comerciais. Preferir sempre sobre scraping. |
| **Google Maps Platform** | `tools/maps_*.py`, `googlemaps` SDK | Places (New), Geocoding, Street View, Distance Matrix; mapa/heatmap no front. Chaves server e browser separadas. |
| **MRLR determinístico** | `tools/mrlr_modelo.py`, `aluguel_*` | Fonte oficial do **aluguel** na viabilidade (A4 Tier 0), sobre espelhos BigQuery. |
| **Playwright (scraping OLX/ImovelWeb)** | `imobiliaria_scraper.py` | **Legado**, fora do caminho crítico (flag `LISTINGS_PLAYWRIGHT`, default off) — era o gargalo com timeouts/Cloudflare. Substituído pela cascata SearchAPI. |
| **Vertex AI Search (Discovery Engine)** | `tools/discovery_engine_tools.py` | **Legado OFF** (`VERTEX_RAG_ENABLED=0`); RAG qualitativo hoje = Eros (`knowledge-ask` / grupos `EROS_GROUP_ID_*`) + corpus local. |
| **BigQuery / Base dos Dados** | `tools/basedosdados_loader.py` | Dados públicos nacionais (CNO, censo, espelhos de aluguel). |
| **CNPJ / Receita Federal** | `tools/rfb_cnpj_fitness_loader.py`, `cnpj_enrichment.py` | Estabelecimentos fitness, QSA, enriquecimento de entrantes. |
| **CNO (obras RFB)** | `tools/rfb_cno_loader.py`, volume `CNO_DATA_DIR` | Obras em andamento (sinal de novas academias). |
| **CKAN** | `tools/ckan_client.py` | Portais de dados abertos (renda por bairro etc.). |
| **IBGE / Censo** | `tools/censo_setor_idade_sexo_loader.py`, `municipio_publico_sexo_loader.py` | Demografia por setor censitário. |
| **FipeZap** | `tools/fipezap_loader.py` / `fipezap_tools.py` | Índices imobiliários (Excel). |
| **CVM** | `tools/cvm_fetch.py`, `cvm_listed_metrics.py` | Métricas de empresas listadas (benchmarks financeiros). |
| **BCB / SINAPI** | `tools/bcb_imobiliario_olinda.py` | Indicadores imobiliários/construção. |
| **CNJ / ANTT** | `tools/cnj_justica_aberta.py`, `antt_tools.py` | Dados jurídicos e de transporte (a confirmar uso exato no relatório). |
| **Nominatim (OSM)** | `tools/nominatim_geocoder.py` | Geocodificação de fallback via OpenStreetMap. |
| **Apollo.io** (`APOLLO_API_KEY`) | `tools/apollo_client.py`, `apollo_enrichment.py` | Enriquecimento de contatos/decisores (People Search) na prospecção. |
| **OpenClaw / Kimi** | `openclaw_kimi_server.py`, `tools/kimi_research.py` | Webhook de prospecção e pesquisa web via Kimi/Moonshot/Groq/Ollama. |
| **Popular Times** | `tools/popular_times_tool.py` | Movimento por horário (tiers: SearchAPI → lib populartimes → Playwright). |
| **Turnstile (Cloudflare)** | `tools/turnstile.py` | Anti-bot do site-agent (`/conversar`, `/analise`). |
| **LangCache (Redis)** | `tools/langcache_client.py` | Cache semântico de respostas LLM. |

---

## Banco de Dados

**Supabase (PostgreSQL)**. Schema em `db/schema.sql` (v1.0), migrations em `db/migrations/*.sql` (~47 arquivos) e espelho em `supabase/migrations/`.

**Extensões Postgres:** `uuid-ossp`, `pgcrypto`, `vector` (pgvector, para busca semântica/RAG).

**Convenções (regras que mordem):**
- **Multi-tenant:** toda tabela tem `org_id`; RLS habilitado nas tabelas de dados de usuário. A `service_role` (usada pelo pipeline) faz bypass de RLS; o front usa `anon key` + Supabase Auth.
- **Dinheiro em centavos** (integer), nunca float.
- **Datas em `timestamptz`** (UTC).

**Tabelas/estruturas notáveis (amostra):**

| Área | Exemplos |
|---|---|
| Tenancy & acesso | `organizations`, `organization_members`, `user_projects` |
| Relatórios | `relatorios` (status enum `queued/running/done/failed/cancelled`, telemetria ADK: `adk_run_id`, `tokens_total`), soft-delete, access code, recuperação de "stale running" |
| Prospecção / CRM | `prospeccao_oportunidades`, sync Apollo, `pessoas_anexos`, RLS hardening |
| Inteligência de dados | `cnpj_fitness_estabelecimentos`, `obras_cno_*`, `entrantes_cnpj_outputs`, `fipezap_indices`, `censo_setor_idade_sexo`, `municipio_rf_ibge` |
| Mercado / Atlas | `market_store`, `market_atlas_view`, colunas `market_wave` / `market_tier_qwen` |
| Chat / consultor | `chat_sessions`, `chat_messages`, RLS de consolidação |
| Execução / RACI | schema de execução, `execucao_raci_aprovacao`, `criterio_verificacao`, `passo_granular` |
| Cache / custo | `cache_tables`, `competidor_intel_cache`, `api_cost_tracker`, `relatorio_custos_agentes` |

> Quando o Supabase não está configurado, o adapter faz no-op silencioso e o pipeline segue salvando JSON em `metrics/relatorios/`.

---

## Infra / DevOps

**Deploy principal: Hetzner VPS + Cloudflare Tunnel** (API + worker no mesmo `docker-compose.prod.yml` em `/opt/gymsite`; push `main` → GHCR → SSH pull via `.github/workflows/ci-cd.yml`). Cloud Run (GCP) DEPRECADO — billing off; ver `docs/PLAN_HETZNER_VPS_TUNNEL.md`.

**Containers (Docker):**
- **`Dockerfile` (backend):** base `python:3.11-slim`; instala Chromium (Playwright, via apt — `CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium`, sem bundle ms-playwright) e libs do WeasyPrint (Pango/cairo/gdk-pixbuf + fontes); sobe com `uvicorn api:app` na porta 8000. Roda como `USER app` (uid 1000, non-root).
- **`frontend/Dockerfile`:** build em `node:22-alpine` (Vite) → serve estático com `nginx-unprivileged:1.27-alpine` na porta 8080.

**Serviços (compose na VPS — `docker-compose.prod.yml`):**
- `api` — API/backend (`RUN_QUEUE_WORKER=0`, só enfileira).
- `worker` — **mesma imagem**, consome a fila e roda o pipeline A0–A9 (`RUN_QUEUE_WORKER=1`); sobe junto no compose (sem sync manual).
- `redis` (fila AOF) + `cloudflared` (túnel, única entrada; sem portas 80/443 abertas).
- Front app/landing = Cloudflare Pages (Wrangler), fora da VPS.

**Legado (ignorar):** `cloudbuild.frontend.yaml` + Actions `pages.yml` — deploy antigo de front por Cloud Build/Cloud Run; hoje front = Wrangler/Pages.

**Redis:** fila de jobs, cache e rate-limit (`tools/redis_*.py`). Prod = serviço `redis` na própria VPS (`redis://redis:6379/0`, AOF); mesmo endpoint local via compose.

**GitHub Actions** (`.github/workflows/`):

| Workflow | Pra que serve |
|---|---|
| `ci-cd.yml` | Build + lint (ruff) + tipos (mypy) + pytest + smoke em container; push GHCR e deploy (VPS/GCE). Inclui eval do golden dataset. |
| `frontend-ci.yml` | Checagem do front (tsc). |
| `docker-image.yml` | Build de imagem Docker. |
| `weekly-market-batch.yml` | Cron semanal (domingo 06:00 UTC): monta market bundles/snapshots → Supabase. |
| `monthly-receita-batch.yml` | Batch mensal de dados da Receita. |
| `benchmark-frete.yml` | Benchmark de frete. |
| `eval-positioning.yml` | Avaliação de qualidade do posicionamento (A9). |
| `gitleaks.yml` | Varredura de segredos vazados. |
| `pages.yml` | **Ignorar** — falha por billing (documentado no CLAUDE.md). |

**Observabilidade:** OpenTelemetry (`OTEL_*`), com export OTLP para Grafana Cloud (a confirmar como padrão em prod). Versão do código bakeada na imagem via `GIT_SHA` (exposta em `/api/version`).

**DNS / rede:** domínios sob `vectracargo.com.br` (`gymsite-api.`, `gymsite.`, `api.`) via Cloudflare Tunnel (a confirmar).

---

## Ferramentas de Dev & IA

**Testes e qualidade:**
- Backend: `.venv/Scripts/python.exe -m pytest` (Windows). No CI: `ruff` (lint), `mypy` (tipos), `pytest` + `pytest-asyncio`.
- Tipos (local): `pyrefly check .`.
- Frontend: `npx tsc --noEmit` (é o "lint"). **Nunca** usar `npm run dev`/`build` só pra testar.
- Segredos: `gitleaks` no CI.

**Config de IDEs / agentes:**
- **`.agent/`** é a fonte de verdade do projeto (compartilhada entre Antigravity/Cursor/VS Code/Gemini/Kimi):
  - `.agent/AGENTS.md` — identidade do agente + mapa de skills.
  - `.agent/rules/` — governança (`processo-mudanca.md` é a regra mestra; `workspace.md`).
  - `.agent/skills/` — 8 skills carregadas sob demanda: `gymsite-backend`, `gymsite-frontend`, `gymsite-pipeline`, `gymsite-intelligence`, `gymsite-reporting`, `gymsite-prospecting`, `gymsite-devops`, `gymsite-testing`.
  - `.agent/workflows/` — 8 procedimentos (`prospect`, `report`, `deploy`, `review`, `debug`, `test`, `migrate`, `backup`).
- `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/` — instruções específicas por ferramenta.

**MCP (Model Context Protocol):** `mcp-config.template.json` define 4 servidores (valores são placeholders no template): `supabase`, `github`, `playwright`, `gemini-api`. Além disso o projeto expõe um servidor próprio via `mcp_server.py` (protegido por `GYMSITE_API_KEY`).

**Scripts auxiliares (Qwen Code CLI):** `scripts/qwen-analyze.ps1`, `scripts/qwen-fix-lint.ps1` — usam o CLI `qwen` para análise/lint de Python (dev, não roda em prod).

---

## Outras Linguagens & Ferramentas

| Tecnologia | Onde | Pra que serve |
|---|---|---|
| **SQL (PostgreSQL)** | `db/schema.sql`, `db/migrations/`, `supabase/migrations/` | Esquema, migrations e views do banco. |
| **PowerShell** | `scripts/*.ps1` | Automação local no Windows (lint/análise Qwen). |
| **Shell / Bash** | `scripts/deploy*.sh`, passos do CI | Deploy e scripts de container/VPS. |
| **HTML/CSS + Jinja2** | `pdf/`, templates | Layout dos relatórios que viram PDF (WeasyPrint). |
| **Pipeline de PDF** | `pdf/` (ReportLab), WeasyPrint, matplotlib, `html2pdf.js` | Dois caminhos de PDF: server-side (produto) e client-side (export da tela). |
| **PDFs de marketing** | `docs/marketing/` | Brandbooks, calendários e relatórios de tendências (documentação, não código). |

---

## Variáveis de Ambiente (apenas nomes)

> Lista de **nomes** extraída dos `.env*.example`. **Nenhum valor/segredo** está incluído.

**Backend / raiz (`.env.production.example`):**
`GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_API_KEY`, `GOOGLE_GENAI_MODEL`, `TURNSTILE_SECRET`, `SITE_AGENT_CAP_IP_DIA`, `SITE_AGENT_CAP_GLOBAL_DIA`, `DEEP_RESEARCH_AGENT`, `DEEP_RESEARCH_TIMEOUT_SEC`, `DEEP_RESEARCH_POLL_SEC`, `DEEP_RESEARCH_FALLBACK_MODEL`, `GOOGLE_MAPS_API_KEY`, `GOOGLE_MAPS_BROWSER_KEY`, `MAPS_FALLBACK_ENABLED`, `CORS_ORIGINS`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_CLOUD_REGION`, `GOOGLE_APPLICATION_CREDENTIALS`, `SERVICE_ACCOUNT_EMAIL`, `IBGE_BIGQUERY_PROJECT`, `BIGQUERY_LOCATION`, `CLOUD_RUN_REGION`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_GYMSITE_ORG_ID`, `CNO_DATA_DIR_HOST`, `CNO_DATA_DIR`, `REDIS_URL`, `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_RESOURCE_ATTRIBUTES`, `CNPJ_ENRIQUECER_QSA`, `CNPJ_ENRIQUECER_MAX`, `APOLLO_ENRICH_ON_PIPELINE`, `APOLLO_API_KEY`, `APOLLO_REVEAL_PERSONAL_EMAILS`, `PIPELINE_MAX_WALL_SEC`, `PIPELINE_ORPHAN_MINUTES`, `LOG_LEVEL`, `GEMINI_API_KEY`, `TINKER_API_KEY`, `TINKER_FALLBACK_MODEL`, `A0_RESEARCH_PROVIDER`, `GYMSITE_API_KEY`, `ADMIN_EMAILS`, `CLAW_WEBHOOK_URL`, `CLAW_WEBHOOK_SECRET`, `OPENCLAW_URL`, `OPENCLAW_TOKEN`, `OPENCLAW_KIMI_SEARCH_PATH`, `SEARCHAPI_KEY`, `PLACES_API_KEY_LEGACY`, `GOOGLE_DISTANCE_MATRIX_API_KEY`, `LANGCACHE_SERVER_URL`, `LANGCACHE_CACHE_ID`, `LANGCACHE_API_KEY`, `REDIS_GENERATE_KEY`.

**Flags citadas no código (não no .env.example):** `LISTINGS_PLAYWRIGHT`, `SITE_AGENT_ENGINE`, `TINKER_BASE_MODEL`, `GIT_SHA`.

**OpenClaw/Kimi (`openclaw_kimi_server.env.example`):** `KIMI_BACKEND`, `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `KIMI_API_KEY`, `OPENCLAW_TOKEN`, `PORT`, `KIMI_TIMEOUT_SEC`.

**Frontend (`frontend/.env.example`):**
`VITE_USE_MOCKS`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE`, `VITE_API_URL`, `VITE_DEV_AS_ADMIN`, `GOOGLE_MAPS_API_KEY`, `GOOGLE_MAPS_MAP_ID`, `VITE_GOOGLE_MAPS_MAP_ID`, `VITE_MAP_PROVIDER`, `REDIS_MEMORY_API_BASE`, `REDIS_MEMORY_STORE_ID`, `REDIS_MEMORY_API_KEY`, `LANGCACHE_SERVER_URL`, `LANGCACHE_CACHE_ID`, `LANGCACHE_API_KEY`, `LANGCACHE_EMBEDDING_MODEL`, `LANGCACHE_SIMILARITY_THRESHOLD`.

**Banco (`db/.env.example`):** `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_GYMSITE_ORG_ID`.

**MCP (`mcp-config.template.json`):** `SUPABASE_ACCESS_TOKEN`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `GEMINI_API_KEY`.
