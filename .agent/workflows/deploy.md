---
description: Deploy API+worker (Cloud Run) and frontend (Cloudflare Pages/Wrangler). Sync worker image after API rebuild.
---

# Workflow: /deploy

> **Canônico:** [P-000 §7–§8](../rules/P-000_REGRA_MESTRA_MUDANCA.md) · [REGRAS_USO_GLOBAL §3.5](../rules/REGRAS_USO_GLOBAL.md) · [CONVERGENCE_DEPLOY.md](../../docs/CONVERGENCE_DEPLOY.md) · skill `gymsite-devops` (alinhada a este workflow).
> **Não usar:** Docker local, Vercel, Cloudflared, `cloudbuild.frontend.yaml`, Actions `pages.yml`.
> **Migrations:** apontar para `/migrate` — nunca `psql -f db/migrations/*.sql` neste workflow.

Deploy produção GymSite (monorepo app logado). Ambiente shell: **PowerShell** (Windows).

## Constantes

| Item | Valor |
|---|---|
| GCP projeto | `gen-lang-client-0106729343` |
| Região | `us-central1` |
| API | `gymsite-api` |
| Worker | `gymsite-worker` (mesma imagem da API; **não** auto-deploya) |
| Front CF | projeto `gymsite` → `getgymsite.com.br` |
| API URL | `https://api.getgymsite.com.br` |
| Órfão (ignorar) | `gen-lang-client-0662901510` |

## Steps

1. **Pre-check** // turbo
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -x --tb=line -q
   cd frontend; npx tsc --noEmit; cd ..
   ```
   Opcional: `pyrefly check .` se instalado. **Não** bloquear em `npm run lint` / Vitest fantasmas.

2. **Migrations pendentes**
   - Se há SQL novo → seguir `/migrate` (arquivo único).
   - Só seed `parametros_metodologia` no banco **não** substitui Cloud Run se código Python mudou.

3. **API — Cloud Run**
   - Preferência: push/`merge` `main` dispara Cloud Build `gymsite-api`, **ou**
   ```powershell
   gcloud run deploy gymsite-api `
     --region=us-central1 `
     --project=gen-lang-client-0106729343 `
     --source .
   ```
   (ou o fluxo de imagem já usado no repo — não inventar Dockerfile “local prod”).

4. **Worker — sync imagem (obrigatório após API)**
   ```powershell
   $IMG = gcloud run services describe gymsite-api `
     --region=us-central1 `
     --project=gen-lang-client-0106729343 `
     --format="value(spec.template.spec.containers[0].image)"
   gcloud run services update gymsite-worker `
     --region=us-central1 `
     --project=gen-lang-client-0106729343 `
     --image $IMG
   ```
   Confirmar `GIT_SHA` / revisão em ambos se setado via env.

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
   Invoke-RestMethod https://api.getgymsite.com.br/api/version
   Invoke-RestMethod https://api.getgymsite.com.br/api/health
   ```
   Front: abrir `https://getgymsite.com.br` (não localhost).

## Rollback

- **API/worker:** Cloud Run → revisão anterior (`gcloud run services update … --image <digest-anterior>` ou UI Revisions).
- **Front:** redeploy deploy Pages anterior (histórico CF) — **não** `docker rename`.

## Checklist rápido

- [ ] Mudou `agents/` / `tools/` / `api.py`? → Cloud Run **sim** + worker sync
- [ ] Só SQL/seed? → `/migrate` ou seed; Cloud Run só se runtime Python também mudou
- [ ] Domínio certo: app = `getgymsite.com.br` ≠ landing `gymsite.com.br`
