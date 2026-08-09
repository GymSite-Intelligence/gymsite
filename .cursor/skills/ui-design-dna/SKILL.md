---
name: ui-design-dna
description: >-
  Aplica DNA visual GymSite (paleta carvão+lime, logo, tokens Tailwind).
  Use ao criar/editar telas, componentes, botões ou CSS do app logado frontend/.
---

# UI Design DNA — GymSite

Fidelidade à marca. Sem hex inventado. Sem tema lab (teal/índigo/laranja) em produção.

## Quando usar

- Qualquer mudança visual em `frontend/` (app logado).
- Novos cards, CTAs, shell, consultor, relatórios, execução.
- **Não** redesenhar landing/degustação do site (`gym-insight-hub`) nesta skill — site congelado (spec 2026-08-03).

## Fonte de verdade

| Fonte | Path |
|-------|------|
| Hex / logo | `docs/frontend/IDENTIDADE_VISUAL_APP.md` |
| Spec UI | `docs/superpowers/specs/2026-08-03-app-ui-identity-design.md` |
| TS palette | `frontend/src/config/gymsite-design-system.ts` → `GYMSITE_PALETTE` |
| Cursor rules | `.cursor/rules/frontend-logo.mdc`, `frontend-desing.mdc` |

Hub (`gym-insight-hub/docs/frontend/CLAUDE.md` + artifact cores) **vence** se hex divergir.

## Paleta canônica (hex reais)

| Uso | Hex | Token / classe |
|-----|-----|----------------|
| Background | `#13161b` | `bg-background` / `GYMSITE_PALETTE.bg` |
| Card | `#181c22` | `bg-card` / `.card` |
| Painel / elevated | `#1c212a` | `bg-secondary` / `.card2` |
| Border | `#2b323d` | `border-border` |
| Text | `#eef1f4` | `text-foreground` / `.fg` |
| Muted | `#9aa4b0` | `text-muted-foreground` |
| Dim (terciário) | `#6b7682` | labels fracos |
| **Primary / lime** | `#84cc01` | `bg-primary` / `text-primary` / `.lime` |
| Lime hover | `#5c9400` | hover / gradiente |
| Amber (aviso) | `#ffba52` | aviso só — **nunca** CTA principal |
| Texto sobre lime | `#13161b` | `text-primary-foreground` |

### Status (parcimônia)

Usar tokens semânticos do app (`status-good` / warning / critical) — não inventar verde/vermelho solto.

### Acentos por especialista (só badge)

Mercado `#84cc01` · Técnico `#55d6e0` · Regulatório `#f2c14a` · Arquiteto `#b98bf5` · Engenheiro `#f2884a`.  
**Nunca** recastear shell/nav/página inteira com essas cores.

## Regras Tailwind

1. Preferir `bg-primary`, `text-foreground`, `border-border`, `bg-card` — **não** `#84cc01` no JSX.
2. Hex só em `GYMSITE_PALETTE` / CSS vars alinhadas — se precisar hex no canvas/mapa, importar da palette.
3. Proibido: roxo-índigo, purple gradient, cream terracotta, Inter/Roboto/Arial como display.
4. `/theme-lab` (`dir-a`/`dir-b`/`dir-c`/`geo`) = laboratório — **não** copiar pra produção.

## Logo

| Fundo | Arquivo |
|-------|---------|
| Escuro (app padrão) | `public/gymsite-logo-white.png` |
| Claro | `public/gymsite-logo.png` |

- Só altura (`h-*`); `width: auto` — **nunca** distorcer aspect ratio.
- Respiro mínimo ~24px (`p-6`) ao redor da logo.

## Componentes

- Named exports; arquivo &lt; ~200 linhas ou extrair subcomponentes.
- Interativo: `hover`, `focus-visible`, `aria-*` quando couber.
- CTA principal = lime (`bg-primary` + texto escuro `#13161b`).
- Cards: `bg-card` + `border-border`; sem sombra multi-camada genérica.

## Checklist rápido

- [ ] Sem hex solto no componente novo
- [ ] Primary = lime `#84cc01` via token
- [ ] Fundo escuro = `#13161b` família
- [ ] Logo branca no shell escuro
- [ ] Site/degustação intocado
- [ ] `npx tsc --noEmit` no `frontend/` se TS mudou
