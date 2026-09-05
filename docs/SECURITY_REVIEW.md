# Security Review — GymSite Intelligence

> Auditoria de **postura** de segurança feita em 2026-07-04, antes do lançamento do MVP.
> **Não é pen-test:** baseia-se em leitura de código, dos Supabase security advisors e da
> configuração de infra — não em ataque ao sistema rodando. Os itens são hipóteses de risco
> priorizadas; confirmar cada um contra o comportamento real antes de tratar como fato.

## Escopo e contexto

- **Backend:** FastAPI (`api.py` + `backend/routers/`), roda na **Hetzner VPS** (Docker) com `service_role`
  do Supabase. **Consequência crítica:** o RLS do Postgres **não filtra** as queries do backend
  (service_role bypassa RLS) — toda autorização precisa ser feita **na aplicação**, explicitamente.
- **Banco:** projeto Supabase `epgedaiukjippepujuzc` compartilhado com outro produto (Vectra
  Cargo). Schemas do GymSite: `gymsite`, `shared`, mais views de compat em `public`.
- **Endpoint público:** análise gratuita (`backend/routers/site_agent.py`) — única superfície
  aberta sem login.
- **Módulo interno (admin):** prospecção/scout — coleta dado de sócios de CNPJ, uso interno
  (GymSite + Vectra), futuro produto para fornecedores. Isolado apenas na UI hoje — ver P1.1.
- **Advisors:** 818 findings totais no projeto; **232 tocam o GymSite** (0 ERROR nos schemas
  `gymsite`/`shared`, 1 ERROR em `public`).

Legenda de prioridade: **P1** = corrigir antes do MVP público · **P2** = primeiras semanas ·
**P3** = higiene/endurecimento.

---

## ✅ Resolvido

### IDOR de relatório — `_assert_relatorio_access` (PR #48)
`GET /api/relatorios/{id}`, `/pdf` e `/mapa-mercado` entregavam o relatório completo para
qualquer request que soubesse o UUID (sem JWT, sem access_code). Corrigido para deny-by-default;
`/pdf` (que não tinha check nenhum) agora valida. Cobertura: `tests/test_relatorio_idor.py`.
Ver [PR #48](https://github.com/Marcelo-Rosas/gymsite/pull/48).

### Capability token — análise grátis (site-agent) — ✅ RESOLVIDO (2026-08-26)
Poll anônimo exige `X-Access-Token` (não query), TTL `access_token_expires_at` (48h),
one-shot no 1º `pronto` (`_invalidar_access_token`), Referrer-Policy no Pages.
Cobertura: `tests/test_access_token_ttl.py`. Logs: `tools/log_redaction.py` + JSONFormatter
(`backend_improvements.py`) mascaram Bearer / X-Access-Token / JWT. Residual: LeadAccess
`id ≠ access_code`.

---

## 🔴 P1 — antes do MVP público

### P1.1 — Módulo de prospecção (scout) não está isolado no servidor — ✅ RESOLVIDO (2026-07-04)
> **Status:** as duas defesas aplicadas. (1) Gate `require_admin` nos 11 endpoints
> `/api/prospeccao/*` — PR #52, em prod (rev `gymsite-api-00386`), + `ADMIN_EMAILS` configurado.
> (2) RLS do scout endurecido — migration `20260704_scout_rls_service_role_only.sql`: as tabelas
> `gymsite.prospects/scout_cadencia/scout_messages` (single-tenant, sem `org_id`) agora só aceitam
> `service_role` (policies `authenticated` removidas + grants `anon`/`authenticated` revogados).
> Verificado em prod: só `scout_service_all_*` resta; anon/authenticated sem grant. O texto abaixo
> é o registro do problema original.

> **Contexto de produto (2026-07-04):** o módulo de prospecção — que coleta dado pessoal de
> sócios de CNPJ (`email_socio_administrador`, `telefone_socio_administrador`) — é **interno /
> admin-only**, para prospecção do GymSite + Vectra Cargo, e no futuro vira produto próprio
> vendido a fornecedores de equipamento fitness. **Não** faz parte do produto voltado ao dono de
> academia. Ver [[decisao-prospeccao-modulo-interno]] na memória.

**O gate "admin-only" existe hoje só no FRONT (as pages), não no backend.** Os endpoints
`/api/prospeccao/*` (`api.py`) usam apenas `_require_authenticated` (qualquer JWT válido, filtrado
por org) — não há `require_admin` no servidor. Pelo P-005 do processo de mudança ("cliente é
cosmético; validação no servidor"), UI não é controle de acesso.

Combinado com as **4 policies RLS "always true"** que anulam o isolamento por org para qualquer
autenticado:
- `gymsite.prospects` → `scout_prospects_insert` (INSERT with check `true`) e
  `scout_prospects_update` (UPDATE using/check `true`)
- `gymsite.scout_cadencia` → `scout_cadencia_update`
- `gymsite.scout_messages` → `scout_msgs_update`

**Risco (vetor corrigido):** não é cross-tenant *entre clientes* — é **vazamento do módulo interno
de prospecção para clientes do MVP**. Quando o **signup público** abrir, cada dono de academia
recebe um JWT válido; sem gate admin no servidor e com o isolamento de org furado pelas policies,
um cliente pode alcançar dados de prospecção (incl. contatos de sócios de terceiros — o dado
LGPD-sensível). Hoje o risco é ~zero (só admins têm conta).

**Gatilho:** fechar **antes de abrir cadastro público**. ✅ FEITO.
**Remediação aplicada (duas defesas):**
1. ✅ Gate `require_admin` no servidor em todos os `/api/prospeccao/*` (PR #52). Defesa primária.
2. ✅ RLS scout → service_role-only (migration `20260704_scout_rls_service_role_only.sql`). Defesa
   em profundidade. NOTA: a proposta inicial ("predicado por org") era inválida — as tabelas scout
   NÃO têm `org_id` (single-tenant interno); o isolamento correto é só service_role, não por org.
   O padrão por-org (`public.user_org_ids()`) vale para `public.oportunidades_prospeccao` (que tem
   org_id e já foi hardened em `20260531_prospeccao_rls_hardening.sql`).

> **Nota LGPD (fora do escopo de código):** "uso interno" não isenta o tratamento de dado de sócio
> pessoa física. Base legal provável = legítimo interesse (prospecção B2B própria), condicionada a
> teste de proporcionalidade documentado + direito de oposição + transparência no 1º contato. A
> **comercialização futura** do módulo a fornecedores muda a base legal (fornecer/monetizar contato
> de PF a terceiro) e é **trava de go-to-market** — conformidade pronta ANTES de comercializar.

### P1.2 — `public.v_relatorios_resumo` é SECURITY DEFINER — ✅ RESOLVIDO (2026-07-04)
Único ERROR de advisor que toca o GymSite. A view rodava com permissões do criador (postgres),
ignorando o RLS de `relatorios` — e como o front consome a view via Supabase JS (authenticated,
`useRelatorios.ts`), qualquer usuário logado veria relatórios de TODAS as orgs (vazamento
cross-tenant, crítico no signup público).
**Remediação aplicada:** `security_invoker = on` (migration
`20260704_v_relatorios_resumo_security_invoker.sql`, em prod). O RLS por org das tabelas base
(policies `mt_*`) passa a valer. Verificado: authenticated tem GRANT nas base; 72 relatórios em
1 org; 2 membros nessa org; 0 órfãos; API (service_role) não afetada.
[Doc](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view)

---

## 🟠 P2 — primeiras semanas

### P2.1 — Cap de sessões de chat por IP — ✅ RESOLVIDO (código; doc sync 2026-08-22)
Caps de chat **já enforced** em `conversar_site` via Redis `_cap_chat_estourado`:
sessões/IP/dia (`SITE_CHAT_SESSOES_IP_DIA`), turnos/projeto (`SITE_CHAT_TURNOS_PROJETO`),
degustação 1 ask/agente/IP/dia; Turnstile em nova sessão; fail-closed se Redis indisponível.
Cobertura: `tests/test_entitlement_caps.py`. Comentário stale em `site_agent.py` removido.
**Residual (não P2.1):** endurecer fail-open de `_searchapi_sem_folga`; testes HTTP de
`/analise` espelhando `test_explorar_api.py`.

### P2.2 — `/docs` e `/openapi.json` públicos — ✅ RESOLVIDO (2026-07-04)
A doc interativa do FastAPI estava aberta em produção — expunha a superfície inteira da API.
**Remediação aplicada:** `docs_url`/`redoc_url`/`openapi_url` gated pela env `EXPOSE_API_DOCS`
(default off → fechado em prod; dev liga com `EXPOSE_API_DOCS=1`). Teste `tests/test_http_hardening.py`.

### P2.3 — GraphQL (`pg_graphql`) expõe `gymsite`/`shared` para `anon`
~99 findings de `pg_graphql_anon_table_exposed` nos schemas do GymSite. O RLS segura a **leitura**
hoje, mas é superfície desnecessária se o front não usa a API GraphQL do Supabase.
**Remediação:** se GraphQL não é usado, remover `gymsite`/`shared` da lista de schemas expostos
do PostgREST/GraphQL — corta a superfície inteira de uma vez.

### P2.4 — `search_path` mutável + função SECURITY DEFINER executável por `anon` — ✅ RESOLVIDO (2026-07-04)
- `search_path` fixado (`= ''`) nas 3 funções (`marcar_pesquisa`, `trg_oportunidade_status_guard`,
  `sync_gymsite_oportunidade_to_prospect`) — refs já qualificadas, sem mudança de lógica.
- `EXECUTE` da `sync` (SECURITY DEFINER) revogado de PUBLIC/anon/authenticated. Era o vetor
  "anon executa função definer" — o grant vinha de PUBLIC (default do Postgres), não de `anon`
  direto. É trigger function → revogar não afeta o disparo (verificado: trigger GymSite→Vectra
  segue ativo). Migration `20260704_p2_4_function_search_path.sql` (em prod).

---

## 🟡 P3 — higiene / endurecimento

### P3.1 — Container roda como root — ✅ RESOLVIDO (2026-08-26)
`Dockerfile` rodava como root. Cloud Run rejeitava non-root (import fail); **Hetzner** validou canário.
**Remediação aplicada:** user `app` (uid 1000), `PLAYWRIGHT_BROWSERS_PATH` em `/app/.cache`, `USER app`.
Host: `chown 1000:1000 cno_data` (`bootstrap.sh` / `deploy.sh`). Smoke: `scripts/nonroot_canary_smoke.py`.

### P3.2 — Sem security headers — ✅ RESOLVIDO (2026-07-04)
A API não enviava HSTS, `X-Frame-Options`, `X-Content-Type-Options` nem `Referrer-Policy`.
**Remediação aplicada:** `SecurityHeadersMiddleware` em `api.py` injeta os 4 headers em toda
resposta (setdefault — não sobrescreve quem já define). CSP fica de fora por ora (a API serve
JSON; CSP mal configurado quebra o front servido pelo Cloudflare). Teste `tests/test_http_hardening.py`.

### P3.3 — Bucket `chat-attachments` permite listing
Advisor `public_bucket_allows_listing`. Confirmar se o bucket precisa ser público e listável; se
não, restringir.

### P3.4 — Proteção de senha vazada desligada
Advisor `auth_leaked_password_protection` off (global). Ligar a checagem HaveIBeenPwned no Supabase
Auth reduz senhas fracas no signup do MVP.

---

## Como reproduzir esta auditoria

```
# Advisors de segurança do projeto (via Supabase MCP ou dashboard)
#   get_advisors(project_id="epgedaiukjippepujuzc", type="security")
# Superfície de auth no código:
#   grep -n "Depends\|_require_authenticated\|_assert_.*access\|access_code" api.py
# Guardrails do endpoint público:
#   backend/routers/site_agent.py  (Turnstile, caps, entitlement)
```

## Nota de método

Cada item acima é postura, não exploit confirmado. Antes de fechar qualquer um: reproduzir o
comportamento (ou o finding do advisor), aplicar o fix numa branch, provar com teste quando
aplicável, e só então marcar resolvido — o mesmo ciclo do P1 (IDOR).
