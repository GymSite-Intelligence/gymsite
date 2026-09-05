# App logado CRM / shell / CAPEX / E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the approved wave: slim nav + CRM `/crm` opaque cards, shared Consultor/Degustação shell, report CAPEX without equipment kit and without Consórcio, Playwright asserts, regulatory CRM study doc only.

**Architecture:** Six serial shippable PRs. Nav/routes first. CRM skin second. Shared `EspecialistasChatShell` third. CAPEX strip reuses the existing financial cascade in `recalcula-cenario-com-kit.ts` (zero equipment instead of kit override). Playwright fourth. Regulatory matrix is markdown only.

**Tech Stack:** React 18, TanStack Router, Tailwind v4, Supabase auth, Playwright, `node --test` for pure TS helpers, `npx tsc --noEmit` in `frontend/`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-05-app-logado-crm-shell-capex-design.md`
- Hide from **menu only** (routes stay): `/mapa`, `/market-atlas`, `/assistente`, `/admin/llm`
- Keep in menu: Hex CARTO (`/carto-hex`), Obras CNO (`/cno-obras`)
- Admin/owner extra nav item: **only** Custos (`/custos`) — never Provedor IA in sidebar
- CRM: label `CRM`; URLs `/crm`, `/crm/$playbookId`; redirect `/execucao` → `/crm` (preserve search)
- CRM cards: solid `bg-card` + `border-border`; no glass fills; semantic tokens only
- CAPEX display: subtract equipment (+ frete equipamentos) and cascade payback/TIR via helper; hide Consórcio + kit sections web+PDF
- API paths `/api/execucao/*` stay (backend rename out of scope)
- Commits: only when human asks in implementing session
- Do not seed legal task templates into DB this wave

**File map**

| File | Role |
|---|---|
| `frontend/src/lib/nav-items.ts` | Visible nav lists |
| `frontend/src/lib/nav-items.test.ts` | Tenant vs admin asserts |
| `frontend/src/router.tsx` | `/crm` routes + redirects |
| `frontend/src/components/layout/AuthenticatedSidebarLayout.tsx` | Breadcrumb titles |
| `frontend/src/routes/PlanosListPage.tsx` | CRM list links |
| `frontend/src/components/execucao/GerarPlanoButton.tsx` | Navigate to `/crm/$id` |
| `frontend/src/components/execucao/PlaybookKanban.tsx` | Opaque cards |
| `frontend/src/components/execucao/PlaybookLista.tsx` | Opaque rows |
| `frontend/src/components/execucao/TarefaModal.tsx` | Solid status badges |
| `frontend/src/components/chat/EspecialistasChatShell.tsx` | Shared shell (new) |
| `frontend/src/components/site/DegustacaoRouteShell.tsx` | Use shared shell / stay thin |
| `frontend/src/routes/ConsultorPage.tsx` | `variant="app"` |
| `frontend/src/lib/recalcula-cenario-com-kit.ts` | Add strip-equipment cascade |
| `frontend/src/lib/recalcula-cenario-sem-equipamentos.test.ts` | Unit tests |
| `frontend/src/routes/RelatorioViewerPage.tsx` | Stop kit apply; strip; hide UI |
| `frontend/src/components/domain/CenarioFinanceiroTable.tsx` | Drop Equipamentos row |
| `frontend/src/components/domain/CapexBreakdownChart.tsx` | Drop Equipamentos slice |
| `frontend/playwright.config.ts` + `frontend/e2e/**` | E2E |
| `docs/produto/crm/tarefas-regulatorias-matriz.md` | Study doc |

---

### Task 1: Nav items — hide routes + CRM label + admin só Custos

**Files:**
- Modify: `frontend/src/lib/nav-items.ts`
- Create: `frontend/src/lib/nav-items.test.ts`

**Interfaces:**
- Consumes: `isOwnerOrAdmin: boolean`
- Produces: `getSidebarNavItems(isOwnerOrAdmin): SidebarNavItem[]` without mapa/atlas/assistente/llm; CRM at `/crm`; admin appends only `custosNavItem`

- [ ] **Step 1: Write failing test**

```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getSidebarNavItems } from './nav-items.ts'

test('tenant menu hides mapa atlas assistente llm', () => {
  const tos = getSidebarNavItems(false).map((i) => i.to)
  for (const bad of ['/mapa', '/market-atlas', '/assistente', '/admin/llm', '/custos']) {
    assert.equal(tos.includes(bad), false, bad)
  }
  assert.equal(tos.includes('/crm'), true)
  assert.equal(tos.includes('/carto-hex'), true)
  assert.equal(tos.includes('/cno-obras'), true)
  assert.equal(tos.includes('/consultor'), true)
})

test('admin menu adds only custos', () => {
  const tos = getSidebarNavItems(true).map((i) => i.to)
  assert.equal(tos.includes('/custos'), true)
  assert.equal(tos.includes('/admin/llm'), false)
})
```

- [ ] **Step 2: Run test — expect FAIL**

```powershell
cd frontend
node --import tsx --test src/lib/nav-items.test.ts
```

Expected: FAIL (still `/execucao` / hidden items present).

- [ ] **Step 3: Implement `nav-items.ts`**

- Change Planos entry to `{ title: 'CRM', to: '/crm', icon: ClipboardListIcon }`
- Remove from `appNavItems`: Mapa, Market Atlas, Assistente
- `getSidebarNavItems`: if admin return `[...appNavItems, custosNavItem]` only (drop `llmAdminNavItem` from return; keep export unused or delete export if unused)

- [ ] **Step 4: Re-run test — PASS**

- [ ] **Step 5: Commit (if human asked)**

```
fix(nav): hide dead routes; rename CRM; admin only custos
```

---

### Task 2: Router `/crm` + redirects from `/execucao`

**Files:**
- Modify: `frontend/src/router.tsx` (planosListRoute, execucaoRoute, AUTHENTICATED_PREFIXES if any)
- Modify: `frontend/src/components/layout/AuthenticatedSidebarLayout.tsx`
- Modify: `frontend/src/routes/PlanosListPage.tsx`
- Modify: `frontend/src/components/execucao/GerarPlanoButton.tsx`
- Grep: replace remaining `to: '/execucao` front navigations (not `/api/execucao`)

**Interfaces:**
- Consumes: same page components `PlanosListPage`, `ProjetoExecucaoPage`
- Produces: canonical paths `/crm`, `/crm/$playbookId`; legacy `/execucao` redirects

- [ ] **Step 1: Grep baseline**

```powershell
cd frontend
rg "to:\s*['\`]/execucao|/execucao" src --glob "*.{ts,tsx}"
```

- [ ] **Step 2: Change route paths to `/crm` and `/crm/$playbookId`**

Keep `validateSearch` on detail. Register **redirect routes** (TanStack Router `redirect` or tiny components):

```ts
// pattern: beforeLoad redirect
beforeLoad: ({ location }) => {
  throw redirect({
    to: '/crm',
    search: location.search as Record<string, unknown>,
    replace: true,
  })
}
```

And for `$playbookId`:

```ts
throw redirect({
  to: '/crm/$playbookId',
  params: { playbookId },
  search: location.search as Record<string, unknown>,
  replace: true,
})
```

Add `/crm` to any authenticated path allowlist arrays that currently list `/execucao` (see `router.tsx` line ~71).

- [ ] **Step 3: Update titles + links**

`AuthenticatedSidebarLayout.tsx`:

```ts
'/crm': 'CRM',
// pathname.startsWith('/crm/') → 'CRM'
```

`PlanosListPage` / `GerarPlanoButton`: `to="/crm/$playbookId"`.

- [ ] **Step 4: Typecheck**

```powershell
cd frontend
npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 5: Commit (if human asked)**

```
feat(crm): canonicalize /crm with /execucao redirects
```

---

### Task 3: CRM opaque task cards

**Files:**
- Modify: `frontend/src/components/execucao/PlaybookKanban.tsx`
- Modify: `frontend/src/components/execucao/PlaybookLista.tsx`
- Modify: `frontend/src/components/execucao/TarefaModal.tsx`
- Modify: `frontend/src/routes/PlanosListPage.tsx`

**Interfaces:**
- Consumes: existing `Tarefa` types
- Produces: same props; solid surfaces only

- [ ] **Step 1: List translucent classes to kill**

```powershell
cd frontend
rg "bg-(muted|accent|card|primary|blue|violet|red|amber|emerald)/|hover:bg-accent/" src/components/execucao src/routes/PlanosListPage.tsx
```

- [ ] **Step 2: Kanban card + column**

Card root must be:

```tsx
className="relative overflow-hidden rounded-lg border border-border bg-card p-3"
```

Column: `bg-secondary` solid (no `/xx`). Dragging: `opacity-80` OK (not glass fill).

- [ ] **Step 3: Lista + list page**

Replace `hover:bg-accent/40` with `hover:bg-muted` or `hover:border-primary`. List cards: `bg-card border-border` solid.

- [ ] **Step 4: TarefaModal badges**

Replace pastel `bg-blue-50 text-blue-700` etc. with:

```tsx
<Badge variant="secondary" className="rounded-full px-3 font-normal">…</Badge>
```

Or `variant="destructive"` / border tokens for atraso. No light-only pastel fills.

Replace `bg-muted/30`, `bg-accent/5` panels with `bg-muted` or `bg-card` + `border-border`.

- [ ] **Step 5: Visual gate**

Open `/crm/$id` dark theme — cards opaque, readable. Optional screenshot under `docs/superpowers/previews/`.

- [ ] **Step 6: Commit (if human asked)**

```
fix(crm): opaque canonical task cards
```

---

### Task 4: Shared EspecialistasChatShell (Consultor = Degustação chrome)

**Files:**
- Create: `frontend/src/components/chat/EspecialistasChatShell.tsx`
- Modify: `frontend/src/routes/ConsultorPage.tsx`
- Modify: `frontend/src/components/site/DegustacaoRouteShell.tsx` OR keep Degustacao as-is and make Consultor match **chat viewport** of SiteChat (prefer: extract shared **app-area** wrapper used by both)
- Soft-deprecate: `frontend/src/components/chat/ConsultorAppShell.tsx` (re-export thin wrapper → new shell)

**Interfaces:**
- Consumes: `UseConsultorChatReturn` for `variant="app"`; existing SiteChat props for public
- Produces:

```ts
export type EspecialistasShellVariant = 'public' | 'sandbox' | 'app'

export type EspecialistasChatShellProps =
  | { variant: 'public' | 'sandbox'; formulario: boolean; devToken?: string }
  | { variant: 'app'; chat: UseConsultorChatReturn }
```

Root element: `data-testid="especialistas-shell"`.

- [ ] **Step 1: Inventory UI parity targets**

Degustação chat uses `SiteChat` inside `DegustacaoRouteShell`. Consultor uses `ConsultorChat` + `ConsultorProjetoAside`. Spec requires **identical UI** — implement by:

1. For `variant="app"`, render the **same outer frame** as degustação main chat column (full-height, `bg-background`, no translucent panels).
2. Mount `ConsultorChat` in that frame; keep `ConsultorProjetoAside` only if it does not break visual parity — if aside breaks parity, move projeto controls into the same pattern Degustação uses (collapse into header/drawer) **without** inventing a third layout.

Minimum bar for merge: side-by-side screenshot degustação vs `/consultor` sharing typography, agent picker density, message bubbles, composer.

- [ ] **Step 2: Implement shell + wire pages**

`ConsultorPage.tsx`:

```tsx
export function ConsultorPage() {
  const chat = useConsultorChat()
  return <EspecialistasChatShell variant="app" chat={chat} />
}
```

`ConsultorAppShell.tsx` becomes:

```tsx
export function ConsultorAppShell(props: { chat: UseConsultorChatReturn }) {
  return <EspecialistasChatShell variant="app" chat={props.chat} />
}
```

- [ ] **Step 3: Typecheck**

```powershell
cd frontend
npx tsc --noEmit
```

- [ ] **Step 4: Commit (if human asked)**

```
refactor(consultor): share especialistas shell with degustacao
```

---

### Task 5: CAPEX without equipment — helper + unit tests

**Files:**
- Modify: `frontend/src/lib/recalcula-cenario-com-kit.ts` (add export; do not break `recalcularCenarioComKit` yet if still referenced)
- Create: `frontend/src/lib/recalcula-cenario-sem-equipamentos.test.ts`

**Interfaces:**
- Consumes: `CenarioJSON`, same cascade constants as kit recalculator
- Produces:

```ts
export function recalcularCenarioSemEquipamentos(
  cenario: CenarioJSON | undefined,
  area_m2: number | null | undefined,
): CenarioAjustado | undefined
```

Behavior: if no `capex_detalhado`, return cenario unchanged. Else set `equipamentos = 0`, `frete_equipamentos = 0`, recompute contingencia/subtotal/total and downstream (manutenção, seguro, capital giro, investimento, payback, margem, TIR) **same formulas** as `recalcularCenarioComKit`. Flag `_equipamentos_ocultos: true`. Null equipment treated as 0 (no NaN).

- [ ] **Step 1: Failing test**

```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { recalcularCenarioSemEquipamentos } from './recalcula-cenario-com-kit.ts'

test('strips equipamentos and frete from capex total', () => {
  const out = recalcularCenarioSemEquipamentos(
    {
      capex_detalhado: {
        equipamentos: 100_000,
        obra_adaptacao: 50_000,
        projeto_arquitetonico: 10_000,
        alvara_e_taxas: 5_000,
        frete_equipamentos: 8_000,
        contingencia_pct: 0.1,
        contingencia_valor: 0,
        total: 0,
      },
      capex_total: 999,
      custos_detalhados: {
        aluguel: 1, condominio: 0, iptu: 0, energia: 0, agua: 100,
        internet: 0, folha: 0, manutencao: 0, contabilidade: 0,
        sistema_gestao: 0, seguro: 0, outros: 0,
      },
      matriculas: { realista: { valor: 100 } },
      frequencia_semanal_aluno: 2,
      receita_mensal_estimada: 50_000,
    } as never,
    400,
  )
  assert.ok(out)
  assert.equal(out!.capex_detalhado!.equipamentos, 0)
  assert.equal(out!.capex_detalhado!.frete_equipamentos, 0)
  const sub = 0 + 50_000 + 10_000 + 5_000 + 0
  const expected = sub + sub * 0.1
  assert.equal(out!.capex_detalhado!.total, expected)
  assert.equal(out!.capex_total, expected)
})
```

(Adjust cast/`CenarioJSON` fields to match real type — copy required fields from an existing fixture if compile fails.)

- [ ] **Step 2: Run — FAIL**

```powershell
cd frontend
node --import tsx --test src/lib/recalcula-cenario-sem-equipamentos.test.ts
```

- [ ] **Step 3: Implement function** (factor shared cascade private helper if duplication > ~40 lines)

- [ ] **Step 4: Run — PASS**

- [ ] **Step 5: Commit (if human asked)**

```
feat(finance): recalcular cenario sem equipamentos kit
```

---

### Task 6: Wire report viewer + tables + PDF — hide kit & Consórcio

**Files:**
- Modify: `frontend/src/routes/RelatorioViewerPage.tsx`
- Modify: `frontend/src/components/domain/CenarioFinanceiroTable.tsx`
- Modify: `frontend/src/components/domain/CapexBreakdownChart.tsx`
- Modify: `frontend/src/components/dashboard/ParecerPdfExport.tsx` (and any Weasy/Jinja consumer if front still embeds equipamentos/consórcio copy)
- Grep PDF pipeline: `rg "Consórcio|Consorcio|Kit de Equipamentos|capex_equipamentos" frontend pdf -g"!*.json"`

**Interfaces:**
- Consumes: `recalcularCenarioSemEquipamentos` / map over low/mid/premium
- Produces: viewer without ConsorcioCard, without Kit section, without Equipamentos row; CAPEX numbers from stripped scenarios

- [ ] **Step 1: Stop applying kit override in viewer**

Replace `recalcularCenariosComKit(...)` block with strip:

```ts
const cenariosRecalc = {
  low: recalcularCenarioSemEquipamentos(out.viabilidade_3_cenarios?.low, areaM2Kit),
  mid: recalcularCenarioSemEquipamentos(out.viabilidade_3_cenarios?.mid, areaM2Kit),
  premium: recalcularCenarioSemEquipamentos(out.viabilidade_3_cenarios?.premium, areaM2Kit),
}
```

Remove UI that says valores recalculados via kit. Remove `<ConsorcioCard …/>`. Remove `<Section title="Kit de Equipamentos">…`.

- [ ] **Step 2: Table + chart**

In `CenarioFinanceiroTable` CAPEX rows array, **delete** the `{ label: 'Equipamentos', … }` entry (and frete equipamentos row if separate).

In `CapexBreakdownChart`, remove the Equipamentos slice from the segments array.

- [ ] **Step 3: PDF / parecer**

Ensure export HTML/PDF paths do not render Consórcio or Equipamentos line; use stripped CAPEX for investimento/payback strings.

- [ ] **Step 4: Grep gate**

```powershell
rg "ConsorcioCard|Kit de Equipamentos|label: 'Equipamentos'" frontend/src/routes/RelatorioViewerPage.tsx frontend/src/components/domain/CenarioFinanceiroTable.tsx
```

Expected: no ConsorcioCard / Kit section / Equipamentos label in those files (category CRM EQUIPAMENTOS elsewhere OK).

- [ ] **Step 5: Typecheck + unit tests**

```powershell
cd frontend
npx tsc --noEmit
node --import tsx --test src/lib/recalcula-cenario-sem-equipamentos.test.ts
```

- [ ] **Step 6: Commit (if human asked)**

```
fix(report): hide equipamentos and consorcio; CAPEX without kit
```

---

### Task 7: Playwright E2E scaffold + cases

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/auth.setup.ts`
- Create: `frontend/e2e/nav-crm.spec.ts`
- Create: `frontend/e2e/relatorio-capex.spec.ts`
- Create: `frontend/e2e/consultor-shell.spec.ts`
- Modify: `frontend/package.json` scripts `"test:e2e": "playwright test"`

**Interfaces:**
- Env: `E2E_BASE_URL`, `E2E_USER_EMAIL`, `E2E_USER_PASSWORD`, `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD`, optional `E2E_RELATORIO_ID`
- Fail fast if secrets missing (throw in setup — do not skip asserts)

- [ ] **Step 1: Install Playwright (devDependency)**

```powershell
cd frontend
npm i -D @playwright/test
npx playwright install chromium
```

- [ ] **Step 2: Config**

`playwright.config.ts`: `baseURL` from env default `https://gymsite.com.br`; project setup storageState; timeout generous for SPA.

- [ ] **Step 3: Specs (minimum)**

`nav-crm.spec.ts`: login as tenant → sidebar text/links must not include Mapa, Market Atlas, Assistente, Provedor de IA; must include CRM, Hex, CNO; visit `/crm` OK; visit `/mapa` still 200.

Admin project: sidebar has Custos; no Provedor de IA.

`relatorio-capex.spec.ts`: open fixture report → assert page has no `/Consórcio/i` and no `/Kit de Equipamentos/i`; if `E2E_EXPECTED_CAPEX` set, assert displayed CAPEX matches.

`consultor-shell.spec.ts`: `/consultor` has `[data-testid=especialistas-shell]`; optionally `/degustacao` same testid when logged-out public page loads shell.

- [ ] **Step 4: Document secrets in plan comment / devops note** — CI `workflow_dispatch` first.

- [ ] **Step 5: Commit (if human asked)**

```
test(e2e): nav CRM CAPEX consultor shell asserts
```

---

### Task 8: Regulatory tasks matrix (doc only)

**Files:**
- Create: `docs/produto/crm/tarefas-regulatorias-matriz.md`

**Interfaces:** none (markdown)

- [ ] **Step 1: Write matrix**

Sections: Vigilância (academia base + branch `precisa_lanchonete`), Arquiteto (`precisa_obra`), Engenheiro (MEP/AVCB/estrutura). Each row: gatilho, docs/atos (national baseline), título tarefa CRM, checklist bullets, categoria (`LEGAL` / `OBRAS`), notes município/UF.

Explicit: **no LLM**; next wave wires into `playbook_templates.py`.

- [ ] **Step 2: Link from design spec** (one line under PR6)

- [ ] **Step 3: Commit (if human asked)**

```
docs(crm): regulatory task matrix study
```

---

## Self-review (plan vs spec)

| Spec item | Task |
|---|---|
| Hide mapa/atlas/assistente/llm from menu | T1 |
| Keep Hex + CNO | T1 |
| Admin só Custos | T1 |
| CRM `/crm` + redirect | T2 |
| Opaque CRM cards | T3 |
| Shared consultor/degustação shell | T4 |
| CAPEX sem kit + cascade TIR/payback | T5–T6 |
| Hide Consórcio web+PDF | T6 |
| E2E C asserts | T7 |
| Legal study only | T8 |
| No dead-route code delete | honored |
| No DB seed | honored |

**Gap closed in plan:** viewer currently *applies* kit via `recalcularCenariosComKit` — T6 removes that and strips instead so payback/TIR stay consistent with CAPEX.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-05-app-logado-crm-shell-capex.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session with executing-plans + checkpoints  

Which approach?
