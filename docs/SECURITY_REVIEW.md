# Security Review — GymSite Intelligence

> Auditoria de **postura** de segurança feita em 2026-07-04, antes do lançamento do MVP.
> **Não é pen-test:** baseia-se em leitura de código, dos Supabase security advisors e da
> configuração de infra — não em ataque ao sistema rodando. Os itens são hipóteses de risco
> priorizadas; confirmar cada um contra o comportamento real antes de tratar como fato.

## Escopo e contexto

- **Backend:** FastAPI (`api.py` + `backend/routers/`), roda no Cloud Run com `service_role`
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

### P1.2 — `public.v_relatorios_resumo` é SECURITY DEFINER
Único ERROR de advisor que toca o GymSite. A view roda com permissões do criador (postgres),
ignorando o RLS de `relatorios` para quem a consulta.
**Remediação:** recriar com `security_invoker = on` (fix de 1 linha).
[Doc](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view)

---

## 🟠 P2 — primeiras semanas

### P2.1 — Cap de sessões de chat por IP não é enforced
`backend/routers/site_agent.py` admite em comentário que o cap de **novas sessões** por IP/dia
ainda não é aplicado (só há Turnstile na 1ª mensagem + cap global/dia). Com tráfego do Instagram
chegando, é custo de LLM aberto a abuso.
**Remediação:** aplicar cap por IP/dia nas novas sessões, espelhando `_cap_estourado`.

### P2.2 — `/docs` e `/openapi.json` públicos
A doc interativa do FastAPI está aberta em produção — expõe a superfície inteira da API a quem
sondar.
**Remediação:** `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` em produção (ou gate
por env/admin).

### P2.3 — GraphQL (`pg_graphql`) expõe `gymsite`/`shared` para `anon`
~99 findings de `pg_graphql_anon_table_exposed` nos schemas do GymSite. O RLS segura a **leitura**
hoje, mas é superfície desnecessária se o front não usa a API GraphQL do Supabase.
**Remediação:** se GraphQL não é usado, remover `gymsite`/`shared` da lista de schemas expostos
do PostgREST/GraphQL — corta a superfície inteira de uma vez.

### P2.4 — `search_path` mutável + função SECURITY DEFINER executável por `anon`
- `search_path` não fixado em: `gymsite.marcar_pesquisa`, `gymsite.trg_oportunidade_status_guard`,
  `public.sync_gymsite_oportunidade_to_prospect` (risco de hijack via schema).
- `public.sync_gymsite_oportunidade_to_prospect` é SECURITY DEFINER **executável por `anon`**.

**Remediação:** `ALTER FUNCTION ... SET search_path = ''` (qualificar refs) nas três; revisar o
GRANT de execução da `sync_*` para remover `anon`.

---

## 🟡 P3 — higiene / endurecimento

### P3.1 — Container roda como root
`Dockerfile` não define `USER` — o processo roda como root na imagem.
**Remediação:** criar usuário não-privilegiado e `USER app` antes do `CMD`.

### P3.2 — Sem security headers
API não envia HSTS, `X-Frame-Options`, `X-Content-Type-Options` nem CSP.
**Remediação:** middleware de headers (ou configurar no proxy/Cloud Run à frente).

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
