# Design — Frontend nav (3 decisões) + ponte conceitual Eros

**Status:** Draft for review (não implementar até aprovação)  
**Date:** 2026-07-24  
**Repos:** `frontend/` (getgymsite / app logado)  
**Fora de escopo de código:** repo `C:\Users\marce\assistent-control` permanece intocado; Eros só como contrato/conceito.

---

## 0. Contexto

Auditoria do `frontend/` mostrou:

- Core vivo: dashboard, relatórios, execução, mapa, comparar, consultor, CNO, custos, prospecção.
- Ruído: Assistente alias, theme-lab, pdf-smoke, stacks órfãs (`useSiteChat`, `AppShell`, `AssistentePage`).
- Três superfícies ambíguas na nav (precisam decisão de produto, não só delete).

Eros (`assistent-control`) = inbox comercial Vectra (IG/Meta + SPIN).  
GymSite = inteligência de viabilidade + captura CNPJ×CNO.  
Smoke Eros (2026-07-24): UI Vite sobe; Supabase `gxmaxbjg…` **DNS morto** (`Failed to fetch`); Sakana key responde mas **crédito prepaid/plano PAYG esgotado** no teste anterior — plano Standard pode servir se billing mode da key = subscription; Ollama local OK.

---

## 1. Decisão A — Prospecção × Captação de Leads

### Problema

Dois itens top-level:

| Rota | Papel real |
|------|------------|
| `/prospect` | Captação: entrantes CNPJ (relatórios + busca municipal) → envia pra `oportunidades_prospeccao` |
| `/prospeccao` | CRM: qualifica + **webhook Navi/Claw** |

Fluxo intencional já documentado no código: **captar → qualificar → Navi**. Nav atual esconde a sequência.

### Opções

1. **Fundir numa página só** — tabs internas Captação | Qualificação.  
2. **Um item nav “Leads”** com sub-rotas `/leads/captacao` + `/leads/qualificacao` (aliases das rotas atuais).  
3. **Manter dois itens** e só reescrever títulos (“1. Captação” / “2. Qualificar → Navi”).

### Recomendação

**Opção 2 (nav única + duas rotas).**  
Preserva URLs/bookmarks com redirect; deixa a ordem explícita; evita mega-página.

### UX alvo

```
Sidebar: Leads
  → /leads (redirect → /leads/captacao)
  → tabs: Captação | Qualificação
CTA em Captação: “Enviar para qualificação” → /leads/qualificacao?…
CTA em Qualificação: “Enviar ao Navi” (webhook atual)
```

### Sucesso

- Um único ícone na sidebar.
- Copy da página diga o passo (1/2 ou 2/2).
- Webhook Navi inalterado nesta fase.

### Fora

- Não reescrever `useProspeccao.ts`.
- Não ligar Eros ainda nesta decisão (ver §4).

---

## 2. Decisão B — Mapa × Market Atlas

### Problema

| Rota | Papel |
|------|--------|
| `/mapa` | Pins de **relatórios** da org; lentes viabilidade/mercado; heatmap |
| `/market-atlas` | Catálogo estratégico de **ondas** (vermelho→azul) + KPIs A9 oceano |

Usuário lê “dois mapas”. São jobs diferentes.

### Opções

1. **Remover Atlas da sidebar**; entrada só via cards do Dashboard.  
2. **Renomear** Atlas na nav (“Oceano / Atlas estratégico”) e Mapa (“Mapa dos meus relatórios”).  
3. **Fundir** num mapa com modo `relatorios | oceano` (custo alto, YAGNI agora).

### Recomendação

**Opção 2 + reforço de deep-link do Dashboard (já parcial).**  
Os dois ficam; naming carrega o job. Fusão (3) só se analytics mostrar abandono de um deles.

### Sucesso

- Títulos/nav sem a palavra genérica “Mapa” nos dois.
- Uma frase de apoio sob o H1 de cada página.

### Fora

- Não mudar camada Google Maps / pigeon neste ciclo.

---

## 3. Decisão C — Novo relatório: Consultor × formulário

### Problema

- CTA sidebar “Novo relatório” → `/consultor` (chat).
- Form clássico ainda em `/relatorios/new` (listagem, cards, escape hatch).

Dois jeitos de pedir o mesmo pipeline.

### Opções

1. **Consultor = único caminho**; form só via link “Avançado” na listagem / consultor.  
2. **Form = único caminho**; consultor vira Q&A pós-relatório.  
3. **Manter ambos iguais na nav** (status quo — rejeitar).

### Recomendação

**Opção 1.**  
Chat já é a jornada de produto (handoff especialistas, pré-fill). Form permanece para poder/editar campos explícitos e “Tentar de novo” com search params.

### UX alvo

```
Sidebar CTA → /consultor
/relatorios → botão secundário “Formulário clássico” → /relatorios/new
Consultor → link discreto “Preferir formulário”
Remover item nav “Assistente” (alias morto de /consultor)
```

### Sucesso

- Um CTA primário.
- Zero item “Assistente” na sidebar.
- `/assistente` continua redirect (compat).

### Fora

- Não apagar `NovoRelatorioPage` neste ciclo.
- Corte da stack órfã `AssistentePage` / `useConversationalChat` = PR separado “corte seguro”.

---

## 4. Ponte conceitual — GymSite `frontend/` × Eros (`assistent-control`)

### Princípio

| Sistema | Job |
|---------|-----|
| GymSite front | Inteligência + captura estruturada (CNPJ, CNO, relatório, mapa) |
| Eros | Inbox humano IG/WA + envio manual (fase atual do brainstorm: **C**) |

**Não** embutir UI Eros no `frontend/` do GymSite.  
**Não** editar o repo Eros neste design — só contrato.

### Onde o front GymSite já “quase” fala com o mundo comercial

```
/prospect (captação)
    → oportunidades_prospeccao
/prospeccao (qualificação)
    → webhook Navi/Claw  (OportunidadeDrawer: whatsapp_link, webhook_*)
SHOW_WHATSAPP_UI = false  (wa.me em cards de concorrente — outro caso)
```

Hoje o destino do webhook é **Navi/Claw**, não Eros.  
Eros smoke: precisa Supabase Eros vivo + Meta; LLM SPIN é fase 2 (humano aprova — escolha C do brainstorm).

### Abordagens de conexão (produto)

**A — Irmãos via webhook (recomendado)**  
Quando oportunidade vai a `qualificado` / `webhook_enviado`, payload também (ou em vez de) cria/atualiza `eros_leads` + thread vazia no projeto Supabase do Eros.  
GymSite front: botão “Abrir no Eros” (deep link) no drawer — só URL, zero embed.

**B — GymSite só gera; Eros puxa**  
Eros periodicamente lê API GymSite (`oportunidades` qualificadas). Mais acoplamento de auth entre projetos.

**C — Um Supabase / monorepo**  
Cedo demais; mistura tenancy GymSite × CRM Vectra.

### Recomendação de ponte

**A.** Contrato mínimo (rascunho):

```json
{
  "event": "oportunidade.qualificado",
  "source": "gymsite",
  "oportunidade": {
    "id": "uuid",
    "cnpj": "...",
    "razao_social": "...",
    "cidade": "...",
    "uf": "...",
    "bairro": null,
    "score_match": 0.0,
    "whatsapp_link": null,
    "instagram_username": null,
    "relatorio_id": null
  }
}
```

Mapeamento Eros (conceitual):

| GymSite | Eros |
|---------|------|
| `razao_social` | `eros_leads.name` |
| `instagram_username` / external | `username` + `external_id` |
| canal default | `instagram` ou `whatsapp` se só telefone |
| `oportunidade.id` | tag / `notes` / meta_json |

Inbox Eros fase 1 (já escolhido): **receber + enviar manual**; SPIN botão existe mas não é bloqueante.

### O que o front GymSite ganha depois da ponte

1. Nav Leads limpa (§1) → operador acha o webhook.  
2. Drawer: status webhook + link “Abrir conversa no Eros” quando `eros_conversation_id` voltar no payload de resposta.  
3. Corte órfãos (§5) → menos confusão “qual chat é o quê” (Consultor ≠ Eros).

### O que explicitamente não conectar

- Degustação / Consultor GymSite ↛ Meta DM.  
- Ollama sandbox GymSite ↛ Edge Eros (Eros já tem `LLM_PROVIDER` próprio: sakana/ollama/gemini).  
- Market Atlas / Mapa ↛ kanban Eros (sem sinal comercial direto).

---

## 5. Corte seguro paralelo (não é das “3 decisões”, mas desbloqueia clareza)

Remover ou gate `import.meta.env.DEV` em PR separado:

- Nav item Assistente; stack `AssistentePage` + `useConversationalChat` + `ChatLayout`/`ChatSidebar`
- `AppShell.tsx`, `store.ts`, `useSiteChat` (+ exports mortos), `TurnstileWidget` neste SPA
- `/theme-lab`, `/pdf-smoke` (ou só em DEV)
- Aliases `@deprecated` sem caller

Manter: mocks `VITE_USE_MOCKS` para dev local.

---

## 6. Ordem de implementação sugerida

1. PR corte seguro órfãos + tirar Assistente da nav.  
2. PR Decisão C (CTA Consultor + links form secundários).  
3. PR Decisão A (nav Leads + redirects).  
4. PR Decisão B (rename copy Mapa/Atlas).  
5. Spec/plano **ponte webhook → Eros** (repo Eros intocado até contrato aprovado + Supabase Eros restaurado).

---

## 7. Test plan (quando implementar)

- [ ] Sidebar: um item Leads; sem Assistente.  
- [ ] `/assistente` → `/consultor`.  
- [ ] CTA Novo → consultor; form alcançável por link secundário.  
- [ ] `/mapa` e `/market-atlas` títulos distintos.  
- [ ] Webhook Navi ainda dispara (regressão).  
- [ ] `npx tsc --noEmit` no `frontend/`.

---

## 8. Abertos (precisam do Marcelo)

1. Destino do webhook na ponte: **substituir** Navi, **duplicar** (Navi + Eros), ou flag por org?  
2. Canal Eros fase inbox (brainstorm pausado): só IG / IG+WA / só WA?  
3. Supabase Eros (`gxmaxbjg…`): restaurar projeto vs apontar URL nova — bloqueia qualquer deep link real.
