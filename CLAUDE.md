# GymSite Intelligence

Plataforma de inteligência de mercado para academias: relatórios de viabilidade cruzando CNPJ, CNO, Google Maps e análise financeira (pipeline de agentes Google ADK A0–A9). Backend Python/FastAPI + Supabase; frontend React/Vite; deploy Cloud Run.

## Fonte de verdade: `.agent/`

O cérebro do projeto vive em `.agent/` (compartilhado com Antigravity/Cursor/VS Code/Gemini). Ler sob demanda — nunca tudo de uma vez:

- `.agent/rules/processo-mudanca.md` — **regra mestra** (P-001..P-010, padrões P0–P3, banco). Ler ANTES de qualquer mudança de código/schema/UX.
- `.agent/rules/workspace.md` — governança (qualidade, naming, git).
- `.agent/AGENTS.md` — identidade do agente + mapa de skills.
- `.agent/skills/<nome>/SKILL.md` — carregar SÓ a relevante: `gymsite-backend` (FastAPI/Pydantic/Supabase), `gymsite-frontend` (React/rotas), `gymsite-pipeline` (agentes ADK/runner), `gymsite-intelligence` (CNPJ/CNO/Maps), `gymsite-reporting` (PDF/gráficos), `gymsite-prospecting` (lead-gen/webhooks), `gymsite-devops` (deploy/env), `gymsite-testing`.
- `.agent/workflows/*.md` — procedimentos salvos (prospect, report, deploy, review, debug, test, migrate, backup).

## Fontes de dados do pipeline

- **SearchAPI** (`SEARCHAPI_KEY`) — Google Maps/Search via API paga. Backend PRIMÁRIO de concorrentes (A3a, `engine=google_maps`, ~4× mais barato que Places) E de imóveis/pontos comerciais (cascata `listing_cascata.py`, bairro-scoped). Preferir sempre sobre scraping.
- **MRLR determinístico** (`aluguel_mrlr.py`) — fonte do ALUGUEL na viabilidade (A4 Tier 0), sobre espelhos BQ. O aluguel NÃO vem de listing raspado.
- **Playwright** (`imobiliaria_scraper.py`, OLX/ImovelWeb) — legado, FORA do caminho crítico (flag `LISTINGS_PLAYWRIGHT`, default off): era o gargalo que estourava o pipeline (timeouts 45s + Cloudflare). A cascata SearchAPI o substitui.
- **Vertex AI Search** — RAG qualitativo (base de conhecimento, catálogos de equipamento/regulatório).

## Regras que mais mordem

- Testes: backend `.venv/Scripts/python.exe -m pytest`; frontend `npx tsc --noEmit`. NUNCA `npm run dev`/`build` pra testar.
- Dinheiro em centavos (integer) no banco; datas `timestamptz` UTC.
- NUNCA comentários no código.
- `gymsite-worker` compartilha a imagem da api e NÃO auto-deploya — após rebuild da api: `gcloud run services update gymsite-worker --image <api_image>`.
- Front sobe via trigger Cloud Build `gymsite-frontend-main` (publishable via build-arg em `cloudbuild.frontend.yaml`); Actions `pages.yml` falha por billing — ignorar.
