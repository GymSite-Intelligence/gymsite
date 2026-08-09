# Identidade visual — app GymSite (monorepo `frontend/`)

> **Paleta / logo canônicas:** repo `gym-insight-hub` →  
> `docs/frontend/CLAUDE.md` + artifact  
> `docs/frontend/artifacts/2026-07-09-cores-canonicas-logo/`  
> Artifact: https://claude.ai/code/artifact/01e0be74-6711-4ea6-b50e-014d98f9fa7b  
>
> Hub vence em conflito de **hex/logo**. Site/degustação = **referência já ok** — **não alterar** nesta onda.

**Escopo (mexer):** rotas do **app logado** em `gymsite/frontend` — shell, nav, relatórios, execução/tasks, mapa, prospecção, custos, perfil, admin, consultor, assistente, login.  
**Fora (não mexer):** chat/degustação do **site** (landing hub + shell de captação) — já no padrão.  
**Também fora:** inventar paleta por rota; `/theme-lab` como produção.

**Data:** 2026-08-03.

---

## 1. Fonte de verdade de cor e logo

| Token (landing `.gs-d`) | Hex | App (`GYMSITE_PALETTE` / Tailwind) |
|---|---|---|
| `--bg` | `#13161b` | `bg-background` / `.bg` |
| `--bg2` / card | `#181c22` | `bg-card` / `.card` |
| `--panel` | `#1c212a` | `bg-secondary` / `.card2` |
| `--border` | `#2b323d` | `border-border` |
| `--text` | `#eef1f4` | `text-foreground` |
| `--muted` | `#9aa4b0` | `text-muted-foreground` |
| `--dim` | `#6b7682` | labels terciários |
| `--green` (lime) | `#84cc01` | `primary` / `.lime` |
| `--green-d` | `#5c9400` | hover / gradiente |
| `--amber` | `#ffba52` | aviso (não CTA primário) |

**Logo:** fundo escuro → `gymsite-logo-white.png` (só altura; `width: auto`).  
**Proibido:** hex solto; roxo-índigo; fundo claro template; Inter/Roboto/Arial como display.

Código: `frontend/src/config/gymsite-design-system.ts` (`GYMSITE_PALETTE`).

---

## 2. Superfícies do app (trabalho desta onda)

| Área | Rotas (exemplos) | Notas |
|---|---|---|
| Shell / nav | layout autenticado | Logo clara; item ativo = lime |
| Home / dashboard | `/`, `/dashboard` | Cards `card`; CTA `primary` |
| Relatórios | `/relatorios`, `/relatorios/$id`, novo, aguardando | Tabelas/bordas canônicas; scores sem cor inventada |
| Comparar / mapa / atlas | `/comparar`, `/mapa`, `/market-atlas` | Markers/acento = lime ou muted; sem arco-íris |
| Execução (tasks) | `/execucao`, `/execucao/$playbookId` | Status com tokens |
| Prospecção / CNO / custos | `/prospeccao`, `/prospect`, `/cno-obras`, `/custos` | Idem |
| Consultor | `/consultor` | Layout produto (mock); **não** clone visual da degustação; **não** editar shell do site |
| Assistente legado | `/assistente` | Alinhar cromia; candidato a deprecar depois |
| Perfil / admin / login | `/perfil`, `/admin/*`, `/login` | Mesmos tokens |

**Não listado de propósito:** landing / degustação site — congelado.

`/theme-lab` = laboratório — **não** é referência de produção.

---

## 3. Ícones

### 3.1 Especialistas (5)

**Arte canônica:** `gymsite_intelligence/docs/produto/brand/icons/` → deploy site `gym-insight-hub/public/agentes/*.png` → app `frontend/public/agentes/*.png` (mesmos bytes do site).

Wrapper: círculo + `border-primary` / `ring-primary` (ativo).  
Componente: `AgentAvatar` com `imgSrc` (PNG), não SVG `agent-svg` no rail/welcome.  
Tamanhos: nav `h-9`–`h-10`, mensagem `h-8`, inline `h-7`, hero welcome `h-16`.

### 3.2 UI genérica

Lucide (enviar, check, mapa, settings) — stroke consistente; `text-primary` só ativo/CTA.

### 3.3 Acentos por especialista (cards `/agentes` no hub — referência)

Mercado `#84cc01` · Técnico `#55d6e0` · Regulatório `#f2c14a` · Arquiteto `#b98bf5` · Engenheiro `#f2884a`.  
No app: no máximo badge do agente — **nunca** recastear shell/nav/página inteira.  
**Não** alterar a página `/agentes` do hub nesta onda.

---

## 4. Padrões de componente (app-wide)

| Elemento | Token |
|---|---|
| Fundo página | `background` `#13161b` |
| Card / painel | `card` / `secondary` |
| Borda | `border` `#2b323d` |
| CTA primário / foco | `primary` `#84cc01` |
| Texto | `foreground` / `muted-foreground` |
| Bolha usuário (consultor app) | `primary` + `primary-foreground` |
| Bolha assistente | `card` + borda |
| Aviso | `amber` com parcimônia |
| Carimbo / citação | `border-l-primary` + `bg-primary/5` |

Labels de seção: caixa-alta + tracking (ex.: PROJETO, PESQUISAS).

---

## 5. Onda UI (organizar casa) — só app

1. **Shell + tokens** — nav/layout autenticado 100% canônico.  
2. **Consultor app** (`/consultor`) — layout produto (mock); ícones padronizados.  
3. **Relatórios + execução** — listas/detalhe/tasks sem drift de cor.  
4. **Restante app** — mapa, prospecção, custos, perfil, admin, assistente.

**Proibido nesta onda:** PRs em landing hub, `DegustacaoChatShell` modo site, CSS scoped da degustação.

Backend RAG / matar Gemini = frentes **paralelas**, não bloqueiam UI app.

---

## 6. Checklist antes de merge de UI

- [ ] Diff só em rotas/shell do **app** — zero mudança em site/degustação.
- [ ] Sem hex fora da §1 (salvo badge agente §3.3).
- [ ] Logo escura só em fundo claro; header escuro = logo clara.
- [ ] Ícones de especialista via `gymsite-icons` + wrapper circular.
- [ ] Rota nova usa `primary`/`card`/`border` — não inventa tema.
- [ ] `/theme-lab` não vaza tokens pra produção.
- [ ] `ConsultorPage` ≠ clone visual da degustação; site intocado.

---

## 7. Código âncora

| Onde | O quê |
|---|---|
| `gym-insight-hub/docs/frontend/CLAUDE.md` | Paleta + logo + artifacts (ler; não editar site) |
| `gymsite/frontend/src/config/gymsite-design-system.ts` | `GYMSITE_PALETTE` |
| `gymsite/frontend/src/components/icons/gymsite-icons.tsx` | Ícones |
| `gymsite/frontend/src/router.tsx` | Mapa de rotas app |
| `gymsite/frontend/src/index.css` | CSS vars / temas |
| `gymsite/frontend/src/routes/ConsultorPage.tsx` | Consultor app |
