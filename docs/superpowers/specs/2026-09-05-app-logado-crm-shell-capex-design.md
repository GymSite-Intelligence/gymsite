# Design: App logado — nav CRM, shell Consultor, CAPEX sem kit, E2E

**Date:** 2026-09-05  
**Status:** draft — awaiting user review before implementation plans  
**Delivery:** serial PRs (approach 2)

## Goal

Simplificar o app logado: menu enxuto, CRM usável com UI opaca canônica, Consultor visualmente idêntico à Degustação, relatório sem Equipamentos/Consórcio na conta exibida, E2E cobrindo o que mudou, e estudo (só doc) de tarefas regulatórias determinísticas para o CRM.

## Non-goals (this wave)

- Remover código das rotas ocultas (só somem do menu; URL ainda abre).
- Seed de templates legais no banco / gerar-plano.
- Refatorar pipeline A4 CAPEX no worker (ajuste na camada de apresentação + helper único nesta onda).
- Tema opaco em **todo** o app logado (só CRM cards nesta fatia).
- Mudar RLS / multi-tenant (tenant já vê só dados da org).

## Decisions locked

| Topic | Choice |
|---|---|
| Hex CARTO / Obras CNO | Permanecem no menu |
| Rotas mortas | Só ocultar no menu: `/mapa`, `/market-atlas`, `/assistente`, `/admin/llm` |
| Admin extra | Só `/custos` (Provedor IA fora do menu para todos) |
| CRM | Label CRM; URL canônica `/crm` + `/crm/$playbookId`; redirect `/execucao` → `/crm` |
| CRM visual | Cards/tarefas opacos, tokens canônicos (`bg-card`, `border-border`, sem glass) |
| Consultor | Shell compartilhada com Degustação (`variant` public vs app) |
| Equipamentos | Some web + PDF; **subtrai** do CAPEX total (payback/TIR usam total sem kit) |
| Consórcio | Some web + PDF; fora da conta |
| CAPEX legacy reports | Helper de apresentação `capexSemEquipamentos` — sem re-run pipeline |
| Leis → tasks | Só estudo/spec (matriz); zero seed |
| E2E | Playwright: smoke + fluxos críticos + asserts menu/CAPEX/shell |
| Delivery | PRs seriais 1→6 |

## Architecture

### PR1 — Nav + CRM routes

**Files (expected):**

- `frontend/src/lib/nav-items.ts` — filter hidden; rename Planos → CRM; admin = + custos only
- `frontend/src/router.tsx` — add `/crm`, `/crm/$playbookId`; redirects from `/execucao*`
- Call sites: `GerarPlanoButton`, `PlanosListPage`, any `to: '/execucao…'`

**Behavior:**

- Tenant menu: Dashboard, Relatórios, CRM, Explorar, Comparar, Prospecção, Captação, Consultor, Obras CNO, Hex CARTO
- Hidden from nav (routes remain registered): Mapa, Market Atlas, Assistente, Provedor IA
- Owner/admin: tenant menu + Custos only

### PR2 — CRM opaque cards

**Files (expected):**

- `frontend/src/components/execucao/PlaybookKanban.tsx`
- `frontend/src/components/execucao/PlaybookLista.tsx`
- `frontend/src/components/execucao/TarefaModal.tsx`
- `frontend/src/routes/PlanosListPage.tsx` (list cards)
- Related execucao surfaces that use translucent hover/pastel badges

**Rules:**

- Task card: solid `bg-card` + `border-border`
- No glass (`bg-*/10..50` as card fill), no pastel light-mode-only pills for status — use semantic tokens
- Keep category solid badge + accent dot
- No kanban/dnd behavior change

### PR3 — Shared especialistas shell

**Files (expected):**

- Extract or extend: `frontend/src/components/site/DegustacaoRouteShell.tsx` → shared `EspecialistasChatShell`
- `frontend/src/routes/ConsultorPage.tsx` — `variant="app"` + `useConsultorChat`
- `frontend/src/routes/DegustacaoPage.tsx` — keep public/sandbox variants
- Deprecate duplicate chrome in `ConsultorAppShell` after parity
- Shared `data-testid="especialistas-shell"` for E2E

**Rules:**

- Same layout: agent grid, welcome, thread, composer
- Auth/billing stay separate (degustação credits vs logged consultor API)

### PR4 — CAPEX without equipment kit + hide Consórcio

**Files (expected):**

- New helper e.g. `frontend/src/lib/capex-display.ts` — `capexSemEquipamentos(cenario)` / strip frete equipamentos if part of kit total
- `useRelatorioDetail` / financial tables / `CenarioFinanceiroTable` / `CapexBreakdownChart` / `ConsorcioCard` mount sites
- PDF templates / `ParecerPdfExport` / Weasy paths that list equipamentos or consórcio

**Rules:**

- Do not render equipment line or Consórcio block on web or PDF
- Displayed CAPEX / payback / TIR inputs use total **minus** equipment kit (and coupled equipment freight if currently inside CAPEX)
- Consórcio never enters totals
- Pipeline/A4 kits remain in repo; presentation layer enforces product rule this wave

### PR5 — Playwright E2E

**Files (expected):**

- `frontend/playwright.config.ts`, `frontend/e2e/**`
- Secrets: test user + admin (CI `workflow_dispatch` first if flaky)

**Cases:**

1. Login
2. Tenant nav: no Mapa/Atlas/Assistente/Provedor IA; has CRM, Hex CARTO, Obras CNO
3. Admin nav: + Custos; no Provedor IA
4. `/crm` list + detail load
5. CRM card solid background assert
6. Report fixture: no Consórcio copy; no Equipamentos line; CAPEX = known total − kit
7. Consultor shares `especialistas-shell` with degustação
8. `/mapa` still HTTP 200 (hidden only from nav)

### PR6 — Regulatory task matrix (doc only)

**Deliverable:** companion doc under `docs/produto/crm/` or extension of this spec:

| Role | Trigger | Canonical docs/acts | CRM task title + checklist | Category |
|---|---|---|---|---|
| Vigilância Sanitária | academia ± lanchonete | alvará, POPs, RDC aplicável, pragas, água, resíduos… | e.g. Montar dossiê VS | LEGAL |
| Arquiteto | obra/adaptação | ART/RRT, acessibilidade, planta, inputs AVCB… | … | OBRAS/LEGAL |
| Engenheiro | estrutura/MEP/AVCB | projetos, laudos, ART… | … | OBRAS |

**Rules:**

- Deterministic if/else on flags (`precisa_lanchonete`, `precisa_obra`) — no LLM invention
- National baseline + note that município/UF may add requirements
- No DB seed this wave; next wave imports matrix into gerar-plano templates

## Error handling

- Redirect `/execucao` preserves search params where possible
- CAPEX helper: null/missing equipment → treat as 0 subtraction (no NaN)
- E2E auth failure → fail fast with clear message (no silent skip of asserts)

## Testing strategy

- Unit: `capexSemEquipamentos` (table-driven)
- Unit/component: nav item lists for tenant vs admin
- E2E: PR5 cases above
- Manual: visual CRM cards dark theme; consultor vs degustação side-by-side

## Rollout order

1. PR1 nav/routes  
2. PR2 CRM UI  
3. PR3 shell  
4. PR4 CAPEX/consórcio  
5. PR5 E2E  
6. PR6 regulatory study doc  

Each PR shippable alone; later PRs may depend on earlier routes/testids.

## Open follow-ups (explicitly out)

- Opaque theme for entire logged-in app
- Delete dead route modules
- A4 pipeline stop emitting equipment CAPEX
- Seed legal templates into playbook generation
