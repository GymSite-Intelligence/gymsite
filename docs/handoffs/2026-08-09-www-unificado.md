# Handoff — Unificar www.gymsite.com.br (landing + blog + degustação + explorar + app)

**Data:** 2026-08-09  
**De:** sessão Cursor no repo `C:\Users\marce\assistent-control` (plano “Unificar www gymsite”)  
**Para:** agente / sessão no repo **`C:\Users\marce\gymsite`** (este monorepo)  
**Humano:** Marcelo  
**Cutover DNS:** `docs/ops/CUTOVER-WWW-GYMSITE.md` (humano; não automatizar)

> Se este doc divergir do código: **confie no código** + `.agent/rules/P-000_REGRA_MESTRA_MUDANCA.md` §8–§9.

---

## 1. Pedido

Um host só: **`www.gymsite.com.br`**. Mesmos paths anônimo e logado. Portar site do hub (`gym-insight-hub`) para `frontend/` deste repo. `getgymsite.com.br` vira 301. API fica `api.getgymsite.com.br`.

**Não** misturar com Eros / `assistent-control` (app-assistent = CRM interno).

---

## 2. Decisões travadas

| # | Escolha |
|---|---|
| Front | **Um SPA:** `frontend/` → Pages CF projeto **`gymsite`** |
| `/` | Landing **sempre**. Logado entra em `/dashboard` (sidebar). |
| Paths | Entitlement muda, URL não. `/explorar` único. **Sem** `/degustacao/explorar`. |
| Chat isca | `/degustacao` neste front. Worker **`gymsite-degustacao`** (ainda no repo hub). |
| Blog público | `frontend/content/blog/` + `src/lib/blog/posts.ts`. **Não** hub. |
| API A0–A9 | `api.getgymsite.com.br` (Hetzner). Sem unificar `api.gymsite.com.br` nesta onda. |

---

## 3. O que já está no código (este repo)

### Auth / rotas — `frontend/src/router.tsx`

- Modelo invertido: **`APP_PREFIXES`** + `RequireAuth` + sidebar.
- Resto (`/`, `/blog`, `/degustacao`, `/agentes`, `/login`, …) = `<Outlet />` sem login.
- `/explorar`: se **logado** → sidebar; se **anon** → chrome site (`degustacao = !user` em `ExplorarPage.tsx`).
- `/` = `LandingPage` (não mais `redirect → /dashboard`).
- `/?abrir=chat|analise|…` → `/degustacao` (`legacyAbrirToDegustacaoSearchFromRecord`).
- `/degustacao/explorar` → `redirect` `/explorar` + `_redirects` 301.
- `/assistente` → `/consultor` (já existia).

### Site portado do hub (não reescrever UX)

| Path | Arquivo |
|------|---------|
| `/` | `frontend/src/routes/LandingPage.tsx` + `gymsite-landing.scoped.css` |
| `/agentes` | `frontend/src/routes/AgentesPage.tsx` + `agentes.scoped.css` |
| `/degustacao` | `frontend/src/routes/DegustacaoPage.tsx` + `components/site/*` + `SiteChat.tsx` |
| `/blog` `/blog/$slug` | `BlogIndexPage.tsx` / `BlogSlugPage.tsx` + `src/lib/blog/` + `content/blog/*.md` |
| Chat API client | `frontend/src/lib/siteAgent.ts` (`VITE_DEGUSTACAO_PROVIDER=cloudflare` → same-origin Worker) |
| URLs | `frontend/src/lib/degustacaoUrls.ts` — `explorarHref()` = `/explorar`, `appLoginHref()` = `/login` |

**Fallback Fugu TanStack Start (`createServerFn`) NÃO veio.** `useSiteChat.ts` só Worker/API; sem `fuguDegustacao.functions`.

**Assets:** `frontend/public/` — logo, dashboard.jpg, `agentes/*.png`.  
**`public/_routes.json`:** `exclude: ["/api/site-agent/*"]` (Worker não pode cair no SPA).

### Env

- `.env.example` / `.env.production.example`: `VITE_DEGUSTACAO_PROVIDER=cloudflare`, Turnstile.
- Chat isca: provider cloudflare → `siteAgent.ts` usa `window.location.origin` se `VITE_API_BASE` vazio.
- A0–A9 logado: `VITE_API_BASE=https://api.getgymsite.com.br`.

### Docs atualizados neste repo

- `.agent/rules/P-000_REGRA_MESTRA_MUDANCA.md` §7–§9 (host canônico www).
- `docs/CONVERGENCE_DEPLOY.md` — bloco “Unificação www (2026-08-09)”.
- `docs/superpowers/specs/2026-08-07-explorar-mapa-design.md` — `/explorar` misto.
- `docs/ops/CUTOVER-WWW-GYMSITE.md` — **checklist DNS/Pages (sua próxima missão).**

`npx tsc --noEmit` no `frontend/` passou após o port (2026-08-09).

---

## 4. Hub (`C:\Users\marce\gym-insight-hub`) — legado

Stopgap **até cutover** (www ainda é hub em produção):

- `src/lib/degustacaoUrls.ts`: `explorarHref()` = `https://getgymsite.com.br/explorar` (**não** `www/explorar` — loop se www = hub).
- Teste `degustacaoUrls.test.ts` alinhado.
- Nota: `docs/ops/CUTOVER-WWW-TO-GYMSITE.md`.

**Não** colocar `_redirects` 301 hub → www enquanto hub servir www.

Worker `workers/degustacao` (`gymsite-degustacao`) **fica no hub**. Rotas já incluem `www.gymsite.com.br/api/site-agent/*`. Não mover nesta onda.

---

## 5. O que VOCÊ (agente gymsite) faz agora

### A. Commit / PR (se ainda uncommitted)

Arquivos novos/alterados concentrados em `frontend/` + docs acima. **Não** commitar `.env.local` / secrets. Human pede commit explícito.

### B. Cutover (humano + você no painel CF) — ordem rígida

Ler e executar `docs/ops/CUTOVER-WWW-GYMSITE.md`:

1. Deploy `frontend/` → Pages projeto **`gymsite`**.
2. Anexar custom domain **www.gymsite.com.br** nesse projeto.
3. **Remover www** do projeto **gym-insight-hub** (dois Pages no mesmo host = quebra).
4. Redirect Rule zona `getgymsite.com.br`: host `getgymsite.com.br` → 301 `https://www.gymsite.com.br/${path}` (query). **Exceto** `api.` / `api-hetzner.`.
5. Apex `gymsite.com.br` já 301 → www (HostGator) — **não mexer**.
6. Supabase Auth → Redirect URLs: `https://www.gymsite.com.br/**` e `/auth/callback`.
7. Build Pages: `VITE_DEGUSTACAO_PROVIDER=cloudflare`, Turnstile, publishable Supabase, `VITE_API_BASE` para A0–A9.

### C. Smoke pós-cutover

- `/` landing  
- `/blog` + slug cidade (ex. post BH Q1)  
- `/degustacao` chat (Worker + Turnstile)  
- `/explorar` anon (1 recorte)  
- `/login` → `/dashboard` → `/consultor` → `/explorar` **com sidebar**  
- `getgymsite.com.br/explorar` → 301 www `/explorar`  
- `/degustacao/explorar` → `/explorar`

### D. Depois do cutover estável

- Hub `explorarHref` → `/explorar` relative ou `https://www.gymsite.com.br/explorar`.
- Desanexar/arquivar Pages hub (Worker permanece).
- Comparativo Q1 blog: só depois gate humano no assistent-control + slug em `frontend/src/lib/blog/posts.ts`. **Não** publicar sozinho.

---

## 6. Não fazer

- Não publicar landing de novo no CF **gym-insight-hub**.
- Não tratar `getgymsite.com.br` como host de UI após 301.
- Não reintroduzir `/degustacao/explorar` como rota viva.
- Não redirect `/` → `/dashboard`.
- Não ingest blog no RAG Eros / grupo Receita 57k.
- Não Graph/Meta publish IG.
- Não mover Worker para este monorepo nesta onda.
- Não `wrangler pages deploy` / trocar custom domain sem ok do humano (sai da máquina).

---

## 7. Mapa mental

```
www.gymsite.com.br  →  Pages gymsite (este frontend/)
  /                    landing
  /blog, /blog/$slug   content/blog + posts.ts
  /agentes             cards → /degustacao?agente=
  /degustacao          SiteChat → Worker /api/site-agent/*
  /explorar            anon = Turnstile/cap; logado = app sidebar
  /login /dashboard /consultor /relatorios* …

getgymsite.com.br/*  →  301 www (exceto api.)
api.getgymsite.com.br →  Hetzner A0–A9
```

---

## 8. Satélite (outro repo — não é sua árvore)

`C:\Users\marce\assistent-control`: fila editorial `/content`, drafts em `Docs/blog/gymsite/`. Publish = **você** (este frontend + deploy Pages gymsite). Ops: `Docs/ops/marketing-loop.md`, `Docs/superpowers/ops/2026-07-25-gymsite-canonical-routes.md`.

---

## 9. Rollback cutover

Reanexar www ao hub; remover redirect getgymsite; redeploy hub. Front unificado neste repo **não apagar**.
