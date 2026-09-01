# Security Audit Toolkit

Automated security checks for SaaS APIs and web apps. **Run only on systems you are authorized to test.**

GymSite-specific mapping: **[GYMSITE_COHERENCIA.md](GYMSITE_COHERENCIA.md)** (paths, veredictos, gaps vs `SECURITY_REVIEW.md`).

## Requirements

- Python 3.10+
- `pip install -r tools/security_audit/requirements.txt`

## Quick start — GymSite API

```powershell
# From repo root (venv do projeto)
.\.venv\Scripts\python.exe -m tools.security_audit `
  --config tools/security_audit/audit-config.gymsite.json `
  --tests cors,clickjacking,rate_limit `
  --output artifacts/security/report

# Com JWT Supabase + IDOR (2 contas)
.\.venv\Scripts\python.exe -m tools.security_audit `
  --config tools/security_audit/audit-config.gymsite.json `
  --token $env:JWT `
  --user-b-token $env:JWT_B `
  --tests cors,jwt,idor `
  --output artifacts/security/report
```

Alvo canônico: `https://api.getgymsite.com.br` (Hetzner). Auth login **não** está na API — é Supabase client-side.

## Quick start — API genérica (template SaaS)

```bash
python -m tools.security_audit.security_audit \
  --target https://api.example.com \
  --output artifacts/security/report
```

## Config file

- **GymSite:** [`audit-config.gymsite.json`](audit-config.gymsite.json)
- **Template SaaS:** [`audit-config.example.json`](audit-config.example.json)

Campos GymSite-relevantes:

| Campo | Uso |
|-------|-----|
| `auth_mode` | `api` (default) — skip user_enum; `supabase` para probe Auth |
| `cors_probe_path` | Rota real (ex. `/health`) |
| `rate_limit_probe_path` / `rate_limit_probe_method` | Burst GET em `/health` |
| `profile_paths` | Rotas autenticadas para jwt/pii |
| `idor_paths` | `/api/relatorios/{id}`, etc. |
| `admin_probe_paths` | Escalada vertical |
| `sqli_endpoints` | Lista `{path, method, body?}` |

```bash
python -m tools.security_audit --config audit-config.gymsite.json --output report
```

## Tests

| ID | Coverage |
|----|----------|
| `rate_limit` | Burst, 429/403, X-RateLimit headers |
| `cors` | Malicious Origin reflection, preflight |
| `pii` | Passwords, hashes, CPF, API keys in JSON |
| `jwt` | alg=none, TTL, logout revocation, URL leakage |
| `user_enum` | Login timing/messages — **skip na API GymSite** (`auth_mode=api`) |
| `clickjacking` | X-Frame-Options, CSP frame-ancestors |
| `sqli` | Error/time-based probes (**critical stop**) |
| `idor` | Cross-user + admin paths (**critical stop**) |

## Outputs

- `report.json` — structured findings + request/response snippets
- `report.html` — executive + technical view
- `report.csv` — SIEM/GRC import
- `report_clickjacking_poc.html` — iframe PoC template

## CI/CD (GitHub Actions) — manual only

Workflow [`.github/workflows/security-audit.yml`](../../.github/workflows/security-audit.yml):

- **`workflow_dispatch` only** — Marcelo dispara quando quiser
- **Não** bloqueia merge; **não** substitui deploy Hetzner (`scripts/deploy.sh`)
- **Não** roda SQLi/IDOR destrutivo em prod automaticamente

Secrets (configure once):

```bash
python scripts/setup_github_security_audit_secrets.py --bootstrap
```

| Secret | Uso |
|--------|-----|
| `SECURITY_AUDIT_USER_A_EMAIL` | Conta Supabase A |
| `SECURITY_AUDIT_USER_A_PASSWORD` | Senha A (CI faz login fresh) |
| `SECURITY_AUDIT_USER_B_EMAIL` | Conta B (IDOR horizontal) |
| `SECURITY_AUDIT_USER_B_PASSWORD` | Senha B |
| `SECURITY_AUDIT_RELATORIO_USER_A` | UUID relatório org A (auto se existir) |

Repo já tem `SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` — workflow não precisa duplicar JWT.

## Cron (VPS)

```cron
0 3 * * 1 cd /opt/gymsite && .venv/bin/python -m tools.security_audit --config /etc/gymsite/audit-config.gymsite.json --output /var/log/gymsite/audit/report
```

## Webhook

```bash
python -m tools.security_audit --target https://api.getgymsite.com.br --webhook https://hooks.slack.com/services/XXX
```

## Legal

Unauthorized scanning may violate law and ToS. Obtain written approval before running against production.
