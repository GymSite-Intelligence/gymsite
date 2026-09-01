# GymSite — Coerência do toolkit `security_audit`

> Mapeamento do toolkit de auditoria HTTP contra a API GymSite real (2026-08).
> Cross-link: [`docs/SECURITY_REVIEW.md`](../../docs/SECURITY_REVIEW.md) · [`tests/test_relatorio_idor.py`](../../tests/test_relatorio_idor.py)

## Stack alvo (2026-08)

| Camada | Host / artefato |
|--------|-----------------|
| API FastAPI | `https://api.getgymsite.com.br` (Hetzner + Cloudflare Tunnel) |
| Auth | Supabase client-side — JWT validado em `api.py` via `sb.auth.get_user()` |
| Rate limit | [`tools/redis_rate_limit.py`](../redis_rate_limit.py) — headers `X-RateLimit-Limit`, `X-RateLimit-Remaining` |
| Front | Cloudflare Pages `www.gymsite.com.br` — clickjacking/CSP em `frontend/public/_headers` (escopo separado) |

**Deploy:** mudanças neste toolkit **não** exigem rebuild Hetzner. Ver P-000 §7.

---

## Conformidade P-000

| Regra | Aplicação |
|-------|-----------|
| §1 Minimalismo | Só `tools/security_audit/` + smoke test; PR `chore/security-audit-gymsite` |
| §2 Ler fonte | Rotas validadas em `api.py`, `backend/routers/`, `redis_rate_limit.py`, `test_relatorio_idor.py` |
| §4 Lazy imports | Toolkit standalone; não importar em `api.py`/agents |
| §7 Deploy | Scan manual opcional; deploy API = `./scripts/deploy.sh` |
| §8 Domínios | Alvo API = `api.getgymsite.com.br` |

Fora de escopo: `data_lineage.md`, pipeline A0–A9, schema Supabase.

---

## Módulos core

| Arquivo | Função |
|---------|--------|
| `security_audit.py` | CLI — multi-target, exit code 1 se critical |
| `config.py` | `AuditConfig` — paths, tokens, `auth_mode`, probes GymSite |
| `http_client.py` | `RateLimitedClient` (httpx async + throttle interno) |
| `models.py` | `Finding`, `AuditReport`, severidades OWASP/CVSS default |
| `reporter.py` | JSON, HTML, CSV, PoC clickjacking, webhook Slack |
| `logger.py` | Log verbose opcional |
| `scanners/__init__.py` | Registry `SCANNERS` + `run_scanners` (critical stop em sqli/idor) |

---

## Scanners — o que fazem e paths GymSite

### `cors`

- **O que faz:** OPTIONS + GET com `Origin` malicioso; detecta reflexão ACAO / wildcard + credentials.
- **Paths GymSite:** `cors_probe_path` → default `/health` (não `/auth/login` — inexistente na API).
- **Severidades:** CRITICAL (reflect + credentials), HIGH (reflect GET), INFO (ok).

### `clickjacking`

- **O que faz:** Verifica `X-Frame-Options` e CSP `frame-ancestors` em paths configurados.
- **Paths GymSite:** `/`, `/health` via `clickjacking_paths`.
- **Nota:** API JSON raramente serve HTML; front Pages tem `_headers` próprio.

### `jwt`

- **O que faz:** Decode header/payload (alg=none, TTL > 24h), probe rota autenticada, logout revocation.
- **Paths GymSite:** primeiro `profile_paths` (ex. `/api/relatorios`); `logout_path` vazio → skip revocation (Supabase gerencia sessão).
- **Requer:** `--token` JWT Supabase válido.

### `rate_limit`

- **O que faz:** Burst de requests; espera 429/403 e headers `X-RateLimit-*`.
- **Paths GymSite:** GET `/health` (`rate_limit_probe_method=GET`); 404 → INFO skip (sem falso HIGH).
- **Fonte:** [`redis_rate_limit.py`](../redis_rate_limit.py) — `/health` = 30 RPM.

### `pii`

- **O que faz:** Regex em JSON de rotas autenticadas (password, hash, CPF, API keys).
- **Paths GymSite:** `/api/relatorios`, `/api/assistente/conversar` (config `profile_paths`).
- **Requer:** `--token`.

### `user_enum`

- **O que faz:** Timing/mensagem em login, register, forgot-password.
- **Veredicto GymSite:** **Descartar na API** — login é Supabase `{SUPABASE_URL}/auth/v1/token`, não FastAPI.
- **Comportamento:** `auth_mode=api` → finding INFO skip (sem falso positivo 404).

### `sqli`

- **O que faz:** Payloads error/time-based em params configurados.
- **Paths GymSite:** `/api/geocode/bairro`, `/api/municipios/bairros`, `POST /api/places-autocomplete`.
- **Params:** `bairro`, `cidade`, `municipio`, `input`, `q`.
- **Critical stop:** sim — para no primeiro CRITICAL.

### `idor`

- **O que faz:** Horizontal (token A vs B), sequential IDs, vertical (admin paths).
- **Paths GymSite:** `/api/relatorios/{id}`, `/pdf`, `/mapa-mercado`; admin `/api/prospeccao/oportunidades`, `/api/admin/llm-config`.
- **Requer:** `--user-a-token`, `--user-b-token`, UUIDs reais em `user_a_id`/`user_b_id`.
- **Complementa:** `tests/test_relatorio_idor.py` (unitário `_assert_relatorio_access`).

---

## Tabela válida / adaptar / descartar

| ID | Veredicto | Motivo |
|----|-----------|--------|
| `cors` | **Adaptar** | Probe `/health` — feito via `cors_probe_path` |
| `clickjacking` | **Válida (API)** | `/health` + `/` |
| `jwt` | **Adaptar** | Probe `profile_paths[0]`; skip logout |
| `rate_limit` | **Adaptar** | GET burst `/health`; skip se 404 |
| `pii` | **Adaptar** | Paths relatório/assistente |
| `user_enum` | **Descartar API** | Skip em `auth_mode=api` |
| `sqli` | **Adaptar** | Endpoints geocode/places |
| `idor` | **Válida se config** | 2 JWTs + UUIDs |
| CLI/core/reporter | **Manter** | Infra |

---

## Rotas relevantes (evidência gate P-000)

**Públicas / probe-safe:**

- `GET /health` — health + rate limit
- `GET /api/geocode/bairro?bairro=&cidade=&uf=`
- `GET /api/municipios/bairros?municipio=&uf=&q=`
- `POST /api/places-autocomplete` — body `{input, municipio, uf}`

**Autenticadas (JWT):**

- `GET /api/relatorios`, `GET /api/relatorios/{id}`, `/pdf`, `/mapa-mercado`
- `POST /api/assistente/conversar`

**Admin (`require_admin`):**

- `GET /api/prospeccao/oportunidades`
- Rotas em `backend/routers/llm_admin.py` → `/api/admin/llm-config`

**Inexistentes na API (template SaaS — não usar):**

- `/auth/login`, `/auth/logout`, `/users/me`, `/search`

---

## Gaps vs SECURITY_REVIEW.md

| Item | Status | Nota |
|------|--------|------|
| IDOR relatório | Resolvido PR #48 | Testes unitários + scanner IDOR complementar |
| Admin prospecção | Resolvido PR #52 | Scanner vertical em `/api/prospeccao/*` |
| Rate limit chat/IP | Resolvido | Middleware global; burst `/health` valida headers |
| user_enum Supabase | Fora escopo API | Modo `auth_mode=supabase` futuro |
| Pen-test Burp | Fora escopo | Este toolkit é smoke automatizado |

---

## Como rodar

### Config template

[`audit-config.gymsite.json`](audit-config.gymsite.json) — sem tokens commitados.

### Scan básico (sem JWT)

```powershell
.\.venv\Scripts\python.exe -m tools.security_audit `
  --config tools/security_audit/audit-config.gymsite.json `
  --tests cors,clickjacking,rate_limit `
  --output artifacts/security/smoke
```

### Scan autenticado

```powershell
$env:JWT = "<supabase-access-token>"
.\.venv\Scripts\python.exe -m tools.security_audit `
  --config tools/security_audit/audit-config.gymsite.json `
  --token $env:JWT `
  --tests cors,jwt,pii,idor `
  --output artifacts/security/full
```

### IDOR (2 contas)

Secrets GitHub (manual workflow): `SECURITY_AUDIT_TOKEN`, `SECURITY_AUDIT_USER_B_TOKEN`.
Config: UUIDs reais de relatório em `user_a_id` / `user_b_id`.

### Linter

```powershell
.\.venv\Scripts\python.exe -m basedpyright tools/security_audit
```

Resultado 2026-08-26: **0 errors, 0 warnings**.

---

## Legal

Scan só com autorização escrita. Produção = Marcelo/proprietário. Não confundir com deploy Hetzner.
