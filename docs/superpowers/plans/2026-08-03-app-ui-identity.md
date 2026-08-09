# App UI Identity — Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Spec: `docs/superpowers/specs/2026-08-03-app-ui-identity-design.md`.

**Goal:** App logado alinhado à paleta canônica; `/consultor` com layout próprio (não `DegustacaoChatShell`).

**Architecture:** Extrair shell só-app do consultor; full-bleed no layout autenticado em `/consultor`; site/degustação intocado.

**Tech Stack:** React 18, TanStack Router, Tailwind tokens (`primary`/`card`/`border`), `gymsite-icons`.

## Global Constraints

- Zero diff em landing hub / modo site de degustação.
- Sem hex solto; tokens `GYMSITE_PALETTE` / CSS vars.
- Logo escura só fundo claro; sidebar = `gymsite-logo-white` via `BrandLogo`.
- Teste: `cd frontend && npx tsc --noEmit`.
- Não commit sem pedido explícito do humano.

---

## File map

| File | Role |
|---|---|
| `components/chat/ConsultorAppShell.tsx` | **New** — chat + projeto aside (app only) |
| `routes/ConsultorPage.tsx` | Usa `ConsultorAppShell`, não `DegustacaoChatShell` |
| `layout/AuthenticatedSidebarLayout.tsx` | Título `/consultor`; full-bleed nessa rota |
| `DegustacaoChatShell.tsx` | **Não alterar** (site) |

---

### Task U1 — Shell: título + full-bleed consultor

- [x] Add `'/consultor': 'Consultor'` to `PAGE_TITLES`
- [x] When pathname starts with `/consultor`, render Outlet without `gap-4 p-4` wrapper (full height)
- [x] Verify: `npx tsc --noEmit`

### Task U2 — ConsultorAppShell

- [x] Create `ConsultorAppShell` composing `ConsultorChat` + `ConsultorProjetoAside` + actions (nova conversa / header mínimo app)
- [x] `ConsultorPage` → `ConsultorAppShell`
- [x] Do not change `DegustacaoChatShell`
- [x] Verify: `npx tsc --noEmit`

### Task U3+ (later PRs)

- Relatórios + execução cromia
- Resto das rotas

---

## Ondas U3/U4

Adiar; este plano entrega U1+U2 como primeiro PR visual.
