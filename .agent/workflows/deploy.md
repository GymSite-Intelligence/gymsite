---
description: Deploy API+worker (Hetzner VPS + Tunnel) and frontend (Cloudflare Pages/Wrangler). Cloud Run deprecado.
---

# Workflow: /deploy

> **Canônico:** [P-000 §7–§8](../rules/P-000_REGRA_MESTRA_MUDANCA.md) · [REGRAS_USO_GLOBAL §3.5](../rules/REGRAS_USO_GLOBAL.md) · [CONVERGENCE_DEPLOY.md](../../docs/CONVERGENCE_DEPLOY.md) · skill `gymsite-devops` (alinhada a este workflow).
> **Não usar:** Docker local, Vercel, Cloudflared, `cloudbuild.frontend.yaml`, Actions `pages.yml`.
> **Migrations:** apontar para `/migrate` — nunca `psql -f db/migrations/*.sql` neste workflow.

Deploy produção GymSite (monorepo app logado). Ambiente shell: **PowerShell** (Windows).

## Constantes

| Item | Valor |
|---|---|
| API + worker | **Hetzner** `/opt/gymsite` · `docker-compose.prod.yml` · túnel CF |
| Staging API | `https://api-hetzner.getgymsite.com.br` |
| Front CF | projeto `gymsite` → `getgymsite.com.br` |
| Landing CF | projeto `gym-insight-hub` → `gymsite.com.br` |
| API URL (após cutover) | `https://api.getgymsite.com.br` |
| Cloud Run | **DEPRECADO** — billing off; não `gcloud run deploy` |
| Órfão GCP | `gen-lang-client-0662901510` (ignorar/desligar — [ADR-008](../../docs/arquitetura/ADR-008_PROD_HETZNER_ORPHAN_GCP.md)) |

## Steps

1. **Pre-check** // turbo
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -x --tb=line -q
   cd frontend; npx tsc --noEmit; cd ..
   ```
   Opcional: `pyrefly check .` se instalado. **Não** bloquear em `npm run lint` / Vitest fantasmas.

2. **Migrations pendentes**
   - Se há SQL novo → seguir `/migrate` (arquivo único).
   - Só seed `parametros_metodologia` no banco **não** substitui deploy Hetzner se código Python mudou.

3. **API + worker — Hetzner** (mesma VPS, compose). Na caixa:
   ```bash
   cd /opt/gymsite
   git pull   # ou rsync do working tree
   ./scripts/deploy.sh          # pull GHCR + rolling api
   # ou primeira vez / sem GHCR:
   docker compose -f docker-compose.prod.yml up -d --build
   ```
   Worker sobe no compose (`RUN_QUEUE_WORKER=1`). **Não** Cloud Run.

5. **Frontend — Cloudflare Pages**
   ```powershell
   cd frontend
   npm run build
   npx wrangler pages deploy ./dist --project-name gymsite
   cd ..
   ```
   Alt: redeploy CF Pages (painel/API) se build já está no Git. `VITE_*` no build — ver P-000 §7 gotcha.

6. **Health**
   ```powershell
   Invoke-RestMethod https://api-hetzner.getgymsite.com.br/health
   # após cutover DNS:
   Invoke-RestMethod https://api.getgymsite.com.br/api/health
   ```
   Front app: `https://getgymsite.com.br` · landing: `https://www.gymsite.com.br/explorar`

## Rollback

- **API/worker:** na VPS, `docker compose -f docker-compose.prod.yml rollback` / imagem anterior no `deploy.sh`; Cloud Run **não**.
- **Front:** redeploy deploy Pages anterior (histórico CF) — **não** `docker rename`.

## Checklist rápido

- [ ] Mudou `agents/` / `tools/` / `api.py`? → **Hetzner** compose api+worker
- [ ] Só SQL/seed? → `/migrate`; VPS só se runtime Python também mudou
- [ ] **Nunca** `gcloud run deploy`
- [ ] Domínio certo: app = `getgymsite.com.br` ≠ landing `gymsite.com.br`
