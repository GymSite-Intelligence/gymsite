# Design — Site público mobile-first + chat sem plaquinhas

**Status:** Approved in conversation 2026-08-27 (Marcelo: “esta certo” / “Sim”)  
**Date:** 2026-08-27  
**Repos:** `gymsite/frontend` — rotas **públicas** do SPA  
**Humano:** Marcelo

---

## 0. Contexto

No telefone, várias páginas do site **escondem o menu e não substituem** (`display: none`). Quem cai em `/`, `/agentes` ou `/blog` fica sem caminho para o resto. No chat da degustação, o primeiro ecrã enche de plaquinhas de marketing.

Não é redesign da landing. É **dar para usar no celular** e **tirar ruído no chat**.

---

## 1. Decisões travadas

| # | Escolha |
|---|---|
| Superfície | Só **site público**: `/`, `/agentes`, `/blog`, `/blog/$slug`, `/degustacao`, `/teste`, `/explorar` (anônimo), `/privacidade`, `/login` |
| Fora | App logado (`/dashboard`, relatórios, mapa interno, consultor, execução, admin, …) |
| Chat — some | Grid MiniCards (`badgesAtritoZero` + kickers) e as tags “O que este consultor cruza” (`MERCADO_CONTEXTO_PESQUISAS`) em `SiteWelcomePanel` |
| Chat — fica | Crachá de quem respondeu, “passou o bastão”, bolinhas de sugestão, box “Sugestão técnica” + Usar exemplo, box metodologia/LGPD |
| `/agentes` tagchips | **Ficam** (catálogo, não é o campo do chat) |
| Abordagem | Cirúrgica: um menu hamburger reutilizado; sem chrome único de marketing |
| Breakpoint menu | **&lt; 768px** (`md`): hamburger. ≥ 768px: links em linha como hoje (landing hoje some o nav em 600px — unificar para 768px) |
| Alvo toque | Controles do menu e CTAs do header ≥ **44×44 px** |

---

## 2. Meta e não-metas

### Meta

1. Em viewport ~375×667, o visitante **navega entre as rotas públicas** sem depender do rodapé.  
2. No chat `/degustacao` (e `/teste`), a tela vazia **não mostra** as três MiniCards nem as tags de contexto.  
3. Composer do chat **não fica atrás** da home indicator / teclado além do `safe-area` já existente; se ainda cobrir, ajustar `dvh` + padding, sem mudar o fluxo da API.

### Não-metas

- Redesign visual da landing, blog dossier, cards de especialistas.  
- App logado, PDF, pipeline A0–A9.  
- Instalar Vitest / Testing Library (repo front testa com `node:assert` + `tsc`).  
- Esconder plaquinhas só no mobile (somem em **qualquer** largura).  
- Novo IA copy; não inventar itens de menu que a página não tinha.

---

## 3. Arquitetura UI

### 3.1 `SitePublicMenu`

Componente único em `frontend/src/components/site/SitePublicMenu.tsx`.

- **Props:** `links: { href: string; label: string }[]` (ordem = ordem da lista).  
- Desktop (`md+`): renderiza os mesmos `href` como links em linha (classe do host pode wrappear).  
- Mobile: botão ícone (Menu) abre `Sheet` (`frontend/src/components/ui/sheet.tsx`) com a lista empilhada, `aria-label="Abrir menu"`, fecha ao navegar.  
- Sem hex solto: `border-border`, `text-foreground`, `text-primary` no item ativo se houver.

**Onde pluga**

| Rota | Links (labels) | Notas |
|---|---|---|
| `/` | Fontes `#fontes`, Benefícios `#beneficios`, Método `#metodo`, Especialistas `/agentes`, Explorar `/explorar`, Blog `/blog`, LGPD `#lgpd`, Entrar `/login` | Substituir `.nav-links` hidden |
| `/agentes` | Fontes `/#fontes`, Método `/#metodo`, Explorar `/explorar`, Blog `/blog`, LGPD `/#lgpd` | Igual ao nav atual |
| `/blog`, `/blog/$slug` | Fontes `/#fontes`, Especialistas `/agentes`, Explorar `/explorar`, Degustação `/degustacao` | Manter `is-active` no Blog |
| `/degustacao`, `/teste` | Especialistas, Explorar, Início; sandbox: + Sandbox HTML + Degustação | Trocar `DegustacaoRouteNav` inline que estoura no `h-14` |
| `/explorar` anônimo | Especialistas, Degustação, Início (já no header) | Se overflow no 375px: mesmos links no `SitePublicMenu` |
| `/login`, `/privacidade` | Link voltar / início já existente; se só logo, **não** inventar mega-menu — garantir `px` e `max-w` sem scroll-x |

### 3.2 Chat (`SiteWelcomePanel`)

Remover:

- Bloco `contextoPesquisas` (flex-wrap de spans).  
- Grid `DEGUSTACAO_COPY.badgesAtritoZero` / `MiniCard`.

Manter avatar, tagline, título, saudação, card de exemplo, box metodologia.

`MiniCard` local pode morrer se ficar sem uso. `ChatMiniCard.tsx` e `degustacaoCopy.badgesAtritoZero` podem permanecer para `/agentes` tagchips.

### 3.3 Degustação header

Em `&lt; sm`: logo = **só pin** (texto “GymSite Intelligence” `hidden sm:inline`) para caber hamburger + safe area.

Altura do chat: manter `100dvh` minus header; composer já usa `pb-[max(0.5rem,env(safe-area-inset-bottom))]`.

### 3.4 Explorar anônimo

Header `.explorar-site-header`: pin + wordmark não podem empurrar nav para fora. Se quebrar em 375px: wordmark some, nav vai para `SitePublicMenu`.

Painéis flutuantes: não bloquear 100% da altura do mapa; scroll interno no painel de resultado. Sem mudar motor de isócrona.

### 3.5 Login / privacidade

`container` + padding horizontal ≥ 16px; inputs `w-full`; sem `overflow-x` na viewport.

---

## 4. Aceite (testável)

| # | Passa se | Falha se |
|---|---|---|
| A | 375px em `/`, `/agentes`, `/blog`: existe controle de menu e todos os destinos da tabela 3.1 abrem | Nav some e não há hamburger |
| B | `/degustacao` tela vazia: zero MiniCards e zero tags de contexto | Texto “uma região por vez” ou “Demografia (IBGE)” como chip |
| C | `/degustacao`: ainda há “Usar pergunta exemplo” e crachá após 1 resposta | Exemplo ou crachá sumiram |
| D | `/explorar` anônimo: mapa visível; header não gera scroll-x | Barra horizontal na página |
| E | `/login` e `/privacidade`: formulário/texto lêem sem zoom forçado de 300px de overflow | Scroll-x |
| F | `npx tsc --noEmit` em `frontend/` | Erro de tipo |

**Preview:** screenshots 375px em `docs/superpowers/previews/2026-08-27-site-mobile-*.png` (landing, agentes, degustação welcome, explorar) **antes** de pedir ok de merge — [preview-aprovacao](../../.agent/rules/preview-aprovacao.md).

---

## 5. Waves

1. Chat: cortar MiniCards + tags em `SiteWelcomePanel`.  
2. `SitePublicMenu` + landing / agentes / blog.  
3. Degustação header + explorar header overflow.  
4. Login / privacidade + verificação browser 375px.

Uma PR / uma onda de código; waves = ordem no plano, não deploys separados.

---

## Self-review

**Data:** 2026-08-27  

| Check | Resultado |
|---|---|
| Placeholder | Nenhum TBD. Breakpoint 768px explícito. |
| Consistência | Chat some plaquinhas em **todas** as larguras; `/agentes` tagchips ficam. Menu só &lt; 768px. |
| Escopo | Um plano front. Sem backend. |
| Ambiguidade | “Campo chat” = `SiteWelcomePanel` no thread vazio, não o `<input>`. |
| Aceite | Tabela §4 binária. |
| Fora | App logado, Vitest, redesign landing, esconder só no mobile. |

**Correções neste passe:** unificar hide-nav 600 vs 720 → **768px**; deixar explícito que tagchips de `/agentes` não saem.
