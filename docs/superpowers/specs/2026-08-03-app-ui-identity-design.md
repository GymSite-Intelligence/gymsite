# Design — Identidade visual do app logado (só UI)

**Status:** Approved — implementing (U1+U2 done 2026-08-03)  
**Date:** 2026-08-03  
**Repos:** `gymsite/frontend` — rotas autenticadas + shell  
**Referência de marca:** `gym-insight-hub/docs/frontend/CLAUDE.md` + artifact `2026-07-09-cores-canonicas-logo`  
**Doc operacional:** [`docs/frontend/IDENTIDADE_VISUAL_APP.md`](../frontend/IDENTIDADE_VISUAL_APP.md)

---

## 0. Contexto

Casa bagunçada no app: `ConsultorPage` ainda monta `DegustacaoChatShell` (visual de site); tokens às vezes drift; Gemini/RAG/backend **fora** deste spec.

**Decisões de produto já fechadas (sessão 2026-08-02/03):**

| Decisão | Escolha |
|---|---|
| Escopo desta spec | **Só UI do app** |
| Site / degustação | Já no padrão → **não mexer** |
| Paleta | Canônica hub (carvão + lime `#84cc01`) |
| Consultor app | Layout próprio (mocks produto), ≠ shell site |
| Ordem de trabalho | Shell → Consultor → Relatórios+Execução → resto app |
| Backend (RAG, matar Gemini SDK) | Frentes paralelas; **não** nesta spec |

---

## 1. Meta e não-metas

### Meta

App logado visualmente coerente com a marca GymSite: mesma paleta, logo, ícones de especialista e padrões de card/CTA em **todas** as rotas autenticadas.

### Não-metas

- Qualquer PR em landing / hub / modo site de `DegustacaoChatShell`
- Troca de provedor LLM, RAG pgvector, corte de tools backend
- Redesign de informação do relatório PDF
- Fundir/depurar nav prospecção×prospect (spec nav 2026-07-24 — separado)
- Tornar `/theme-lab` padrão de produção

### Sucesso

1. Diff de UI **zero** em arquivos só-site/degustação.  
2. `/consultor` parece o mock produto (especialistas + welcome/projeto), não a landing.  
3. Shell + rotas principais usam só tokens da §2 (sem hex solto).  
4. Checklist de [`IDENTIDADE_VISUAL_APP.md`](../frontend/IDENTIDADE_VISUAL_APP.md) passa em review visual.

---

## 2. Design tokens (fonte de verdade)

| Uso | Hex | Token app |
|---|---|---|
| Fundo | `#13161b` | `bg-background` |
| Card | `#181c22` | `bg-card` |
| Painel | `#1c212a` | `bg-secondary` |
| Borda | `#2b323d` | `border-border` |
| Texto | `#eef1f4` | `text-foreground` |
| Muted | `#9aa4b0` | `text-muted-foreground` |
| Lime (marca) | `#84cc01` | `primary` |
| Lime hover | `#5c9400` | hover / gradiente |
| Aviso | `#ffba52` | amber (parcimônia) |

**Logo:** header/sidebar escuro → `gymsite-logo-white.png` (só altura; `width: auto`).  
**Código:** `frontend/src/config/gymsite-design-system.ts` (`GYMSITE_PALETTE`).  
**Proibido:** hex solto; Inter/Roboto/Arial como display; tema-agente pintando página inteira.

Acentos por especialista (Mercado/Técnico/…) = só badge — ver hub `/agentes`. Não editar hub nesta spec.

---

## 3. Arquitetura UI

### 3.1 Shell

- Layout autenticado: `AuthenticatedSidebarLayout` + `AppSidebar`.  
- Item ativo nav = `text-primary` / fundo `primary/10`.  
- Sem topbar legado `AppShell` se ainda sobrar — não reintroduzir.

### 3.2 Consultor (`/consultor`) — alvo visual

Hoje:

```tsx
// ConsultorPage.tsx
return <DegustacaoChatShell mode="app" chat={chat} />
```

Alvo: página/composiçãos **própria** do app (não `mode="app"` no shell de degustação).

Estrutura (mocks aprovados):

```text
AuthenticatedSidebarLayout
└─ ConsultorPage
   ├─ coluna especialistas (Mercado | Técnico | Regulatório | Arquiteto | Engenheiro)
   │     ícones gymsite-icons + wrapper circular border-primary
   ├─ centro: empty state “Especialista em …” + sugestão técnica + tags
   │     OU thread de mensagens + input (bolha user = primary)
   └─ aside: PROJETO + PESQUISAS (checklist)
```

Reusar o que já existe se couber sem puxar visual de site: `ConsultorWelcomePanel`, `ConsultorProjetoAside`, `ConsultorChat` (extrair do shell).  
**Não** alterar comportamento do shell quando `mode="landing"` / uso no site.

Hooks (`useConsultorChat`) podem permanecer; muda **apresentação**.

### 3.3 Ícones

| Tipo | Fonte | Wrapper |
|---|---|---|
| 5 especialistas | `gymsite-icons.tsx` | círculo + `border-primary` / `ring-primary` ativo |
| UI genérica | Lucide | stroke consistente; primary só CTA/ativo |

Tamanhos: nav `h-9`–`h-10`, mensagem `h-8`, inline `h-7`.

### 3.4 Demais rotas

Mesmos tokens em: dashboard, relatórios, execução/tasks, comparar, mapa, atlas, prospecção, prospect, CNO, custos, perfil, admin, login, assistente.

Sem redesign de IA/fluxo — só cromia, bordas, CTA, ícones onde drift.

---

## 4. Ondas de implementação (UI only)

| Onda | Escopo | Done when |
|---|---|---|
| **U1** | Shell + `AppSidebar` + tokens globais app | Nav/logo/ativo = canônico; sem hex drift no shell |
| **U2** | `/consultor` layout produto | Não usa `DegustacaoChatShell`; mock ok desktop+mobile |
| **U3** | Relatórios + `/execucao*` | Listas/detalhe/tasks sem cor inventada |
| **U4** | Resto app | mapa, prospecção, custos, perfil, admin, assistente, login |

Cada onda = PR separado. Teste: `npx tsc --noEmit` no `frontend/`. Review visual contra §2 + mocks.

**Gate anti-regressão site:** CI/review checklist — nenhum arquivo de landing hub; nenhum diff em caminhos só-degustação sem necessidade app. Se `DegustacaoChatShell.tsx` for tocado, só extrair código compartilhado **sem** mudar `mode` site / aparência landing.

---

## 5. Error / edge (UI)

| Caso | Comportamento |
|---|---|
| Mobile consultor | Aside projeto/jornada = drawer ou sheet; especialistas acessíveis |
| Sem projeto ainda | Empty state welcome (mock 2), não tela quebrada |
| Assistente legado `/assistente` | Alinhar tokens; não investir layout novo além do necessário |
| `/theme-lab` | Intocado ou escondido da nav — não é referência |

---

## 6. Testing

- `cd frontend && npx tsc --noEmit` por onda.  
- Checklist visual §6 de `IDENTIDADE_VISUAL_APP.md`.  
- Spot-check: `/consultor`, `/relatorios`, `/execucao`, shell.  
- Confirmar site/degustação **inalterado** (git diff path filter).

---

## 7. Fora / paralelo (não bloquear)

- RAG Eros-style no gymsite  
- Remover Gemini SDK / NVIDIA fallback  
- Corte de tools do `consultor_engine`  
- NLP DistilBERT  

Documentar em specs futuras quando retomar.

---

## 8. Self-review

| Check | Resultado |
|---|---|
| Placeholders TBD? | Não — ondas U1–U4 concretas |
| Contradição site vs app? | Não — site congelado; app só |
| Escopo único? | Sim — UI app only |
| Ambiguity ConsultorPage? | Explícito: sair de `DegustacaoChatShell`; reusar painéis existentes |

---

## 9. Aprovação

Spec escrita em:

`docs/superpowers/specs/2026-08-03-app-ui-identity-design.md`

Revisar. Quer mudança? Depois disso → plano de implementação (`writing-plans`), **só** após teu ok.
