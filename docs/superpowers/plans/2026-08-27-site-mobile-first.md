# Site público mobile-first + chat sem plaquinhas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Public site navigable at ~375px (hamburger replacing vanished nav) and degustação welcome screen without marketing MiniCards / context chips.

**Architecture:** Extract `SiteNavLink[]` constants + `SitePublicMenu` (inline `md+`, Sheet below). Strip two blocks from `SiteWelcomePanel`. Tighten degustação/explorar headers on small viewports. Verify in browser at 375px.

**Tech Stack:** React 18, TanStack Router, Tailwind v4, shadcn `Sheet`, `npx tsc --noEmit`, `node --test` (assert) for link lists. No Vitest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-27-site-mobile-first-design.md`
- Public routes only; do not change app-logged shell
- Chat: remove MiniCards + `MERCADO_CONTEXTO_PESQUISAS` chips only; keep example, metodologia, crachá, sugestões
- `/agentes` hero `tagchips` stay
- Breakpoint **768px** (`md:`); touch target ≥ 44px on menu button
- Tokens: `border-border`, `text-foreground`, `text-primary` — no new hex in JSX
- Commits: only if the human asked in the implementing session
- Preview: `docs/superpowers/previews/2026-08-27-site-mobile-*.png` before asking merge

**File map**

| File | Role |
|---|---|
| `frontend/src/lib/sitePublicNav.ts` | Link lists per surface |
| `frontend/src/lib/sitePublicNav.test.ts` | Assert labels/hrefs |
| `frontend/src/components/site/SitePublicMenu.tsx` | Hamburger + inline nav |
| `frontend/src/components/site/SiteWelcomePanel.tsx` | Drop chips |
| `frontend/src/routes/LandingPage.tsx` + `gymsite-landing.scoped.css` | Plug menu; stop `display:none` nav |
| `frontend/src/routes/AgentesPage.tsx` + `agentes.scoped.css` | Plug menu |
| `frontend/src/routes/BlogIndexPage.tsx` `BlogSlugPage.tsx` + `blog.scoped.css` | Plug menu |
| `frontend/src/components/site/DegustacaoRouteShell.tsx` | Menu + pin-only logo on xs |
| `frontend/src/routes/ExplorarPage.tsx` + `explorar-chrome.css` | Menu if nav overflows |
| `frontend/src/routes/PrivacidadePage.tsx` | Home link + padding if needed |

---

### Task 1: Welcome panel — no marketing chips

**Files:**
- Modify: `frontend/src/components/site/SiteWelcomePanel.tsx`
- Test: visual + grep (no Vitest). Gate: `npx tsc --noEmit` after Task 2 can wait; this task is JSX-only.

**Interfaces:**
- Consumes: `AgenteLanding`, `DEGUSTACAO_COPY`, `onUseExample`
- Produces: same `SiteWelcomePanel` props; no `MiniCard`; no `contextoPesquisas` UI

- [ ] **Step 1: Confirm chips exist (fail criterion)**

Grep must find `badgesAtritoZero` and `MERCADO_CONTEXTO_PESQUISAS` **used in JSX** in `SiteWelcomePanel.tsx` before the edit.

- [ ] **Step 2: Remove those two blocks**

Delete the `contextoPesquisas` section (the `flex-wrap` of spans) and the `grid` that maps `DEGUSTACAO_COPY.badgesAtritoZero` to `MiniCard`. Delete the local `MiniCard` function if unused. Remove unused imports (`MERCADO_CONTEXTO_PESQUISAS` if unused). **Keep** tagline, tema, saudação, “Sugestão técnica”, Usar exemplo, metodologia box.

Do **not** remove `badgesAtritoZero` from `degustacaoCopy.ts` (`AgentesPage` still uses it).

- [ ] **Step 3: Grep gate**

```powershell
cd frontend
rg "MiniCard|MERCADO_CONTEXTO_PESQUISAS|badgesAtritoZero" src/components/site/SiteWelcomePanel.tsx
```

Expected: **no matches**.

- [ ] **Step 4: Commit (only if human asked)**

```
fix(site): drop degustacao welcome marketing chips
```

---

### Task 2: Nav data + tests

**Files:**
- Create: `frontend/src/lib/sitePublicNav.ts`
- Create: `frontend/src/lib/sitePublicNav.test.ts`

**Interfaces:**
- Consumes: none
- Produces:

```ts
export type SiteNavLink = { href: string; label: string }

export const LANDING_NAV: SiteNavLink[]
export const AGENTES_NAV: SiteNavLink[]
export const BLOG_NAV: SiteNavLink[]
export const DEGUSTACAO_NAV: SiteNavLink[]
export const DEGUSTACAO_SANDBOX_NAV: SiteNavLink[]
export const EXPLORAR_SITE_NAV: SiteNavLink[]
```

- [ ] **Step 1: Write failing test**

Create `frontend/src/lib/sitePublicNav.test.ts`:

```ts
import assert from 'node:assert/strict'
import test from 'node:test'
import {
  AGENTES_NAV,
  BLOG_NAV,
  DEGUSTACAO_NAV,
  DEGUSTACAO_SANDBOX_NAV,
  EXPLORAR_SITE_NAV,
  LANDING_NAV,
} from './sitePublicNav.ts'

test('landing nav has 8 destinations', () => {
  assert.equal(LANDING_NAV.length, 8)
  assert.deepEqual(
    LANDING_NAV.map((l) => l.label),
    [
      'Fontes',
      'Benefícios',
      'Método',
      'Especialistas',
      'Explorar',
      'Blog',
      'LGPD',
      'Entrar',
    ],
  )
  assert.equal(LANDING_NAV[0].href, '#fontes')
  assert.equal(LANDING_NAV[7].href, '/login')
})

test('agentes / blog / degustacao / explorar hrefs', () => {
  assert.deepEqual(
    AGENTES_NAV.map((l) => l.href),
    ['/#fontes', '/#metodo', '/explorar', '/blog', '/#lgpd'],
  )
  assert.equal(BLOG_NAV.some((l) => l.href === '/degustacao'), true)
  assert.deepEqual(
    DEGUSTACAO_NAV.map((l) => l.label),
    ['Especialistas', 'Explorar', 'Início'],
  )
  assert.ok(DEGUSTACAO_SANDBOX_NAV.length > DEGUSTACAO_NAV.length)
  assert.deepEqual(
    EXPLORAR_SITE_NAV.map((l) => l.label),
    ['Especialistas', 'Degustação', 'Início'],
  )
})
```

- [ ] **Step 2: Run test — must FAIL**

```powershell
cd frontend
node --experimental-strip-types --test src/lib/sitePublicNav.test.ts
```

Expected: FAIL (module not found).

- [ ] **Step 3: Implement `sitePublicNav.ts`**

```ts
export type SiteNavLink = { href: string; label: string }

export const LANDING_NAV: SiteNavLink[] = [
  { href: '#fontes', label: 'Fontes' },
  { href: '#beneficios', label: 'Benefícios' },
  { href: '#metodo', label: 'Método' },
  { href: '/agentes', label: 'Especialistas' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/blog', label: 'Blog' },
  { href: '#lgpd', label: 'LGPD' },
  { href: '/login', label: 'Entrar' },
]

export const AGENTES_NAV: SiteNavLink[] = [
  { href: '/#fontes', label: 'Fontes' },
  { href: '/#metodo', label: 'Método' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/blog', label: 'Blog' },
  { href: '/#lgpd', label: 'LGPD' },
]

export const BLOG_NAV: SiteNavLink[] = [
  { href: '/#fontes', label: 'Fontes' },
  { href: '/agentes', label: 'Especialistas' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/blog', label: 'Blog' },
  { href: '/degustacao', label: 'Degustação' },
]

export const DEGUSTACAO_NAV: SiteNavLink[] = [
  { href: '/agentes', label: 'Especialistas' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/', label: 'Início' },
]

export const DEGUSTACAO_SANDBOX_NAV: SiteNavLink[] = [
  { href: '/agentes', label: 'Especialistas' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/sandbox-ollama.html', label: 'Sandbox HTML' },
  { href: '/degustacao', label: 'Degustação' },
  { href: '/', label: 'Início' },
]

export const EXPLORAR_SITE_NAV: SiteNavLink[] = [
  { href: '/agentes', label: 'Especialistas' },
  { href: '/degustacao', label: 'Degustação' },
  { href: '/', label: 'Início' },
]
```

Explorar public header currently has “Especialistas”, “Degustação”, current “Explorar”, “Início”. `EXPLORAR_SITE_NAV` omits the current-page label (Explorar) — menu is for **leaving**. On desktop keep the `is-current` span. On mobile hamburger uses `EXPLORAR_SITE_NAV` only.

- [ ] **Step 4: Re-run test — PASS**

Same `node --test` command. Expected: 2 passing.

- [ ] **Step 5: Commit (only if human asked)**

```
feat(site): public nav link lists
```

---

### Task 3: `SitePublicMenu`

**Files:**
- Create: `frontend/src/components/site/SitePublicMenu.tsx`
- Modify: none until Task 4

**Interfaces:**
- Consumes: `SiteNavLink[]` from Task 2
- Produces: `SitePublicMenu({ links, activeHref?, className? })`

- [ ] **Step 1: Implement component**

Use existing Sheet exports from `frontend/src/components/ui/sheet.tsx` (`Sheet`, `SheetTrigger`, `SheetContent`, `SheetHeader`, `SheetTitle`, `SheetClose`). Read the file for exact export names before writing.

Pattern:

```tsx
import { Menu } from 'lucide-react'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import type { SiteNavLink } from '@/lib/sitePublicNav'

export function SitePublicMenu({
  links,
  activeHref,
  className,
}: {
  links: SiteNavLink[]
  activeHref?: string
  className?: string
}) {
  return (
    <div className={cn('flex items-center', className)}>
      <nav className="hidden md:flex md:items-center md:gap-6" aria-label="Principal">
        {links.map((l) => (
          <a
            key={l.href + l.label}
            href={l.href}
            className={cn(
              'text-sm font-medium text-muted-foreground hover:text-foreground',
              activeHref === l.href && 'text-foreground',
            )}
          >
            {l.label}
          </a>
        ))}
      </nav>
      <Sheet>
        <SheetTrigger
          className="inline-flex size-11 items-center justify-center rounded-md border border-border md:hidden"
          aria-label="Abrir menu"
        >
          <Menu className="h-5 w-5" />
        </SheetTrigger>
        <SheetContent side="right" className="bg-background text-foreground">
          <SheetHeader>
            <SheetTitle>Menu</SheetTitle>
          </SheetHeader>
          <nav className="mt-4 flex flex-col gap-1" aria-label="Principal">
            {links.map((l) => (
              <a
                key={l.href + l.label}
                href={l.href}
                className="flex min-h-11 items-center rounded-md px-3 text-base hover:bg-accent"
              >
                {l.label}
              </a>
            ))}
          </nav>
        </SheetContent>
      </Sheet>
    </div>
  )
}
```

If `SheetContent` already includes a close button, do not duplicate. If landing `.gs-d a{color:inherit}` fights Tailwind on inline nav, wrap landing usage in a class that sets color on `a` (see Task 4 CSS).

- [ ] **Step 2: `npx tsc --noEmit` in `frontend/`**

Expected: exit 0.

- [ ] **Step 3: Commit (only if human asked)**

```
feat(site): public hamburger menu
```

---

### Task 4: Landing, agentes, blog

**Files:**
- Modify: `frontend/src/routes/LandingPage.tsx`
- Modify: `frontend/src/routes/gymsite-landing.scoped.css`
- Modify: `frontend/src/routes/AgentesPage.tsx`
- Modify: `frontend/src/routes/agentes.scoped.css`
- Modify: `frontend/src/routes/BlogIndexPage.tsx`
- Modify: `frontend/src/routes/BlogSlugPage.tsx`
- Modify: `frontend/src/routes/blog.scoped.css`

**Interfaces:**
- Consumes: `SitePublicMenu`, `LANDING_NAV`, `AGENTES_NAV`, `BLOG_NAV`

- [ ] **Step 1: Landing**

Replace the inner `.nav-links` block with:

```tsx
<SitePublicMenu links={LANDING_NAV} />
```

In `gymsite-landing.scoped.css`:
- Remove `.gs-d .nav-links{display:none}` inside `@media(max-width:600px)`.
- Optional: `.gs-d nav a{color:var(--muted)}` / hover `--text` so Sheet portal (outside `.gs-d`) is untouched but inline links inside `.gs-d` stay readable.

Keep `.gs-d .nav-in` flex space-between.

- [ ] **Step 2: Agentes**

Replace `<nav className="nav">…</nav>` with `<SitePublicMenu links={AGENTES_NAV} />`.

Remove `@media(max-width:720px){.gs-ag .nav{display:none}}`. Header stays `justify-content:space-between`.

- [ ] **Step 3: Blog index + slug**

Replace the `<nav className="nav">` with `<SitePublicMenu links={BLOG_NAV} activeHref="/blog" />`.

Remove `@media (max-width: 720px) { .gs-blog .nav { display: none; } }`.

- [ ] **Step 4: tsc**

```powershell
cd frontend
npx tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 5: Commit (only if human asked)**

```
feat(site): hamburger on landing agentes blog
```

---

### Task 5: Degustação + explorar headers

**Files:**
- Modify: `frontend/src/components/site/DegustacaoRouteShell.tsx`
- Modify: `frontend/src/routes/ExplorarPage.tsx` (anonymous header only)
- Modify: `frontend/src/components/explorar/explorar-chrome.css`

**Interfaces:**
- Consumes: `DEGUSTACAO_NAV`, `DEGUSTACAO_SANDBOX_NAV`, `EXPLORAR_SITE_NAV`, `SitePublicMenu`

- [ ] **Step 1: DegustacaoRouteShell**

`DegustacaoLogoLink`: wrap the wordmark span:

```tsx
<span className="hidden sm:inline">
  GymSite <span className="text-primary">Intelligence</span>
</span>
```

Replace `DegustacaoRouteNav` with:

```tsx
<SitePublicMenu
  links={variant === 'sandbox' ? DEGUSTACAO_SANDBOX_NAV : DEGUSTACAO_NAV}
/>
```

Keep `ml-auto` on the menu wrapper (`className="ml-auto"`). Keep sandbox amber badge.

Do **not** remove chat drawers (especialistas / jornada).

- [ ] **Step 2: Explorar anonymous header**

Where `degustacao && (` header): keep brand; replace `<nav>…</nav>` with desktop `hidden md:flex` **or** only `SitePublicMenu links={EXPLORAR_SITE_NAV}` plus a visually hidden/current “Explorar” on `md+` if needed.

Simplest: `SitePublicMenu` with `EXPLORAR_SITE_NAV` and `className="ml-auto"`. On `md+` three links; current page is obvious from URL. Drop the `is-current` span **or** keep it only `hidden md:inline` next to the menu — do not duplicate Explorar in the hamburger.

CSS: `.explorar-site-header nav { display: none }` can go if nav is gone. Hide wordmark on xs:

```css
@media (max-width: 639px) {
  .explorar-site-brand span { display: none; }
}
```

- [ ] **Step 3: tsc**

Expected: exit 0.

- [ ] **Step 4: Commit (only if human asked)**

```
feat(site): compact public headers on degustacao explorar
```

---

### Task 6: Privacidade + browser proof

**Files:**
- Modify: `frontend/src/routes/PrivacidadePage.tsx` (logo should go `/` not `/login` if still login-only — check current `Link to="/login"`; public home is `/`)
- Preview: `docs/superpowers/previews/2026-08-27-site-mobile-landing.png` etc.

**Interfaces:** none new

- [ ] **Step 1: Privacidade**

Header: `Link to="/"` with pin or text “Início”; `px-4` already via container. No mega-menu required.

Login already `px-4 max-w-sm` — do not restyle unless 375px screenshot shows overflow.

- [ ] **Step 2: Browser 375×667**

Start `npx vite --port 5174` in `frontend/`. For each: `/`, `/agentes`, `/degustacao`, `/explorar?degustacao=1` or whatever `explorarHref` uses for anonymous site chrome — read `explorarHref` / `ExplorarPage` `degustacao` search param.

Pass criteria from spec §4 A–E. Save screenshots under `docs/superpowers/previews/2026-08-27-site-mobile-*.png`.

- [ ] **Step 3: tsc final**

```powershell
cd frontend
npx tsc --noEmit
node --experimental-strip-types --test src/lib/sitePublicNav.test.ts
```

Expected: tsc 0, tests pass.

---

## Plan self-review vs spec

| Spec | Task |
|---|---|
| MiniCards + contexto chips gone | 1 |
| Hamburger &lt; 768, lists 3.1 | 2–4 |
| Degustação compact + explorar overflow | 5 |
| Login/privacidade no scroll-x | 6 |
| Aceite F tsc | 3–6 |
| `/agentes` tagchips stay | 1 does not touch AgentesPage chips |
| App logado untouched | no AppShell files |
| Preview 375px | 6 |
