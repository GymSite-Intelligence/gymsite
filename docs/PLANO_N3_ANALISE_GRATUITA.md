# Plano Técnico — N3: Análise Gratuita do Agente do Site

Conecta o **ChatAgent** da landing (`gym-insight-hub`, Cloudflare Pages) ao
pipeline determinístico de viabilidade do `gymsite_intelligence`, entregando
**1 análise gratuita por visitante** (mini-relatório), com anti-abuso.

LLM: **Vertex/Gemini** (já usado no backend). Escopo: **N3** (subset do pipeline A0-A9).

---

## 1. Arquitetura / fluxo

```
ChatAgent (site)  — coleta cidade/bairro/modelo + email + Turnstile token
      │  POST público
      ▼
/api/site-agent/analise   (novo router, backend)
  1. verifica Turnstile (anti-bot)
  2. entitlement: email+IP já usou?  → sim: {status:"quota_used"} (vira lead quente)
  3. allowance SearchAPI (resumo_orcamento)  → estourou: {status:"fila"} / avisa
  4. cria stub `relatorios` (user_id=NULL, org_id=ANON_ORG, access_token=uuid, fonte=landing)
  5. grava `analise_gratuita` (email,ip → relatorio_id)
  6. _enqueue_ou_background(job)  → gymsite_worker roda o MESMO pipeline ADK
  7. retorna {relatorio_id, access_token, status:"processando", eta_min:5}
      │
      ▼  polling ~10s
GET /api/site-agent/analise/{id}?token=...   (backend lê Supabase service_role, valida token)
      │  status PRONTO
      ▼
mini-relatório (subset) renderizado no modal / página /analise/{id}
(opcional) e-mail com link quando pronto
```

**Por que backend no meio (não Supabase anon direto):** RLS de `relatorios` é
`for all using (org_id in user_org_ids())` → anônimo (uid null) **lê zero**.
Só `service_role` bypassa. Logo o fetch do resultado passa pelo backend, que
valida o `access_token` não-adivinhável e devolve só o subset permitido.

---

## 2. Backend (`gymsite_intelligence`) — a criar

### 2.1 Migration `db/migrations/XXXX_analise_gratuita.sql`
- Tabela `analise_gratuita`:
  - `id uuid pk`, `email text`, `ip inet`, `relatorio_id uuid fk relatorios`,
    `created_at timestamptz`, `user_agent text`, `utm jsonb`.
  - `unique (lower(email))` → 1 grátis por email (regra de negócio).
  - índice `(ip, created_at)` p/ cap por IP/dia.
- `alter table relatorios add column access_token uuid` (fetch anônimo seguro).
- Seed `ANON_ORG_ID` (org dedicada aos runs grátis — isola métricas/custo).
- RLS: `analise_gratuita` enable RLS, sem policy anon (só service_role).

### 2.2 Router `backend/routers/site_agent.py` (público, prefix `/api/site-agent`)
- `POST /analise` (LeadInput estendido: + cidade/bairro/modelo + turnstile_token):
  - `verificar_turnstile(token, ip)` (helper novo).
  - checa `analise_gratuita` por email → `quota_used`.
  - checa `resumo_orcamento()` (SearchAPI) → se acima do threshold, status `fila`.
  - cria stub `relatorios` (reusa o caminho do `POST /api/relatorios`, com
    `user_id=None`, `org_id=ANON_ORG_ID`, `access_token=uuid4`).
  - insere `analise_gratuita` + insere `leads` (reusa `_persistir_lead`).
  - `_enqueue_ou_background(job, background)` — **mesmo runner do pipeline**.
- `GET /analise/{id}?token=...`:
  - service_role read; valida `access_token`; 404 se não bater.
  - projeta **subset** (ver §4) de `relatorio_outputs` + `competidores` (top-3).
  - 200 com `{status, mini_relatorio|null}`; status de `relatorios.status`.
- Rate limit: cai no `DEFAULT_RPM=60`/IP (já existe). Add cap/dia/IP via Redis.

### 2.3 Helpers / reuso
- **Turnstile**: `tools/turnstile.py` → POST `https://challenges.cloudflare.com/turnstile/v0/siteverify` (secret em env `TURNSTILE_SECRET`).
- **Reusa sem reescrever**: `_enqueue_ou_background` + `gymsite_worker` (runner),
  `db/supabase_writer` (grava), `tools/searchapi_account.resumo_orcamento` (guard),
  `_persistir_lead` (leads.py), `kb_rag` (se quiser texto RAG no resumo).
- Montar router em `api.py`: `app.include_router(site_agent_router)`.

### 2.4 CORS (bug aberto)
Adicionar à `CORS_ORIGINS` (.env/.env.production) as origens vivas:
`https://getgymsite.com.br,https://gym-insight-hub.pages.dev` e incluir
`gym-insight-hub.pages.dev` no `_cors_origin_regex`. **OU** depende do Caminho A
(apontar `gymsite.com.br` → projeto), que já está na allowlist. Resolver junto.

---

## 3. Frontend (`gym-insight-hub`) — ChatAgent

- Adicionar **Cloudflare Turnstile** widget no form (script + sitekey via `VITE_TURNSTILE_SITEKEY`).
- `handleSubmit`: trocar o `POST /api/leads` por `POST /api/site-agent/analise`
  (que internamente já grava o lead). Mandar `turnstile_token` + perfil/região.
- Novos estados no modal:
  - `processando` → polling `GET /analise/{id}?token` a cada ~10s + barra "gerando análise (~5 min)".
  - `pronto` → render do mini-relatório.
  - `quota_used` → "você já usou sua análise gratuita" + CTA vendas/WhatsApp.
  - `fila` → "alta demanda, te enviamos por email".
- Persistir `{relatorio_id, access_token}` em `localStorage` (visitante fecha/volta).
- Opção: página dedicada `/analise/$id` (rota TanStack) p/ link de email.

---

## 4. Subset do mini-relatório (free) vs gateado (pago)

**FREE expõe** (de `relatorio_outputs`): `veredito`, `resumo_executivo`,
`nivel_saturacao`, `score_bairro`, `total_concorrentes_analisados`,
`rating_medio_concorrentes`, `modelo_recomendado`, **top-3 concorrentes**
(nome + rating + bairro).

**PAGO/gateado** (não retorna no free): A9 posicionamento ERRC, lista completa
de concorrentes + planos/preços, cenários financeiros detalhados,
`bairros_alternativos`, **PDF formal**.

> O gate é na **projeção do GET** — o pipeline roda completo e grava tudo;
> o endpoint free só devolve o subset. Upsell = "veja o relatório completo".

---

## 5. Anti-abuso (defesa em profundidade)

| Camada | Mecanismo | Estado |
|---|---|---|
| Bot | **Turnstile** no submit | criar |
| Burst | Rate limit Redis 60rpm/IP | ✅ existe |
| Volume/IP | cap N/dia/IP (Redis counter) | criar |
| Regra negócio | `unique(email)` em `analise_gratuita` | criar |
| Gasto global | **allowance SearchAPI** + cache 7d + `resumo_orcamento` | ✅ existe |
| Retry storm | `PIPELINE_MAX_CUSTO_BRL=20` | ✅ existe |
| Leitura | `access_token` + RLS nega anon | criar token |

LGPD: email+IP = dado pessoal → consentimento já no checkbox LGPD do form.

---

## 6. Riscos / decisões abertas

1. **SearchAPI = plano PAGO próprio em produção** (key/allowance injetada pelo
   ambiente, não no `.env.production`). O free de ~100/mês é só dev (Tier 0).
   Custo ≈ **$0.004/search** × N searches por relatório; teto = `monthly_allowance`
   + `remaining_credits` (pagos), lidos ao vivo por `resumo_orcamento()`; budget
   guard já alerta em **80%** e bloqueia em **95%**.
   → Decisão real: definir um **cap global de análises grátis/dia** atrelado ao
   `restante` do `resumo_orcamento` (throttle suave antes do 95%), em vez de
   confiar só no entitlement por email. Monitorar via `/api/custos/searchapi`.
2. **Custo Gemini** do pipeline em volume free — monitorar via `api_cost_tracker`.
3. **Espera 3-5 min** (N3). Se quiser instantâneo, seria N1/N2 (só Supabase, sem
   SearchAPI live) — mas decidimos N3 com mapa de concorrentes.
4. **org anônima vs `user_id` null**: usar `ANON_ORG_ID` dedicada (isola RLS + custo).
5. **Fase seguinte** ("o que pode informar ou não"): plugar o guardrail
   `conversational_engine.classificar_intencao` (`fora_de_escopo`) na conversa,
   se o agente do site também responder perguntas livres (além do relatório).

---

## 7. Ordem de implementação sugerida
1. Migration (`analise_gratuita` + `access_token` + ANON_ORG).
2. Turnstile helper + CORS fix.
3. Router `/api/site-agent` (POST + GET) reusando runner.
4. Frontend: Turnstile + polling + estados + render subset.
5. E-mail "pronto" (opcional).
6. Teste e2e: lead → run → polling → mini-relatório; 2ª vez mesmo email → quota_used.
