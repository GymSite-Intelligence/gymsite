# GymSite Intelligence — Frontend

Frontend Fase 2 do GymSite Intelligence. **Repo isolado, sem dependência do vectra-dashboard ou MiroFish.**

## Stack

- **Vite + React 18 + TypeScript** (SPA puro)
- **Tailwind CSS** (dark mode via class)
- **shadcn/ui** (componentes copiados em `src/components/ui/`, possuímos o código)
- **TanStack Router** (file-based, search params tipados) — *próxima fase*
- **TanStack Query** (server state + polling de `status`) — *próxima fase*
- **Zustand** (apenas `activeOrgId` + session) — *próxima fase*
- **Supabase JS** (RLS multi-tenant) — *aguardando projeto Supabase ativo*

## Setup local

```bash
cd frontend
npm install
npm run dev    # http://localhost:5174
```

## Status atual

✅ **Implementado**
- Boilerplate Vite/React/TS/Tailwind/shadcn
- Paleta dark + tipografia DM Sans/IBM Plex Mono
- 14 cores semânticas pra categorias de dor (taxonomia A3a)
- 4 cores pra vereditos
- `cn()` helper + `Badge` primitivo shadcn
- **`VeredictoBadge`** — 4 estados com emoji + label
- **`CategoriaDorBadge`** — 14 categorias com modulação por `sinal`
- `types/domain.ts` com todos os tipos do schema SQL (9 tabelas + view)
- Demo visual em `App.tsx` mostrando todas as variações

🔲 **Próximos**
- `npx supabase gen types` quando projeto ativo
- TanStack Router setup (rotas auth + app)
- Listagem (`Tela 2 — Meus Relatórios`)
- Formulário (`Tela 1 — Novo Relatório`)
- Viewer (`Tela 3 — Relatório`) com 12 seções
- Auth + multi-org seletor
- Mocks de relatórios reais (copiar de `../metrics/relatorios/`)

## Convenções

- Imports usam alias `@/*` → `./src/*`
- Domain components em `@/components/domain/` (lógica GymSite)
- Primitivos shadcn em `@/components/ui/` (sem customizar — usar `className`)
- Tipos JSONB (reviews, alertas, contato_decisor) tem cast manual em `domain.ts`

## Notas

- `VITE_USE_MOCKS=true` (default no `.env.example`) → frontend usa fixtures locais
- Quando projeto Supabase estiver ativo: criar `.env.local` com `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` e setar `VITE_USE_MOCKS=false`
