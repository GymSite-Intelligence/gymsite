---
name: gymsite-devops
description: Deploy e ops GymSite — Cloud Run (API+worker), Cloudflare Pages/Wrangler, env/secrets. Use ao publicar, sincronizar worker, health prod. NÃO use para lógica de negócio, endpoints REST ou UI. Path canônico = workflow /deploy (P-000 §7–§8).
---

# GymSite Intelligence — DevOps

> **Canônico:** [P-000 §7–§8](../../rules/P-000_REGRA_MESTRA_MUDANCA.md) · workflow [`.agent/workflows/deploy.md`](../../workflows/deploy.md) · [PLAN_HETZNER_VPS_TUNNEL.md](../../docs/PLAN_HETZNER_VPS_TUNNEL.md) · CLI VPS: [vps-cli-console.md](../../rules/vps-cli-console.md).
> **Cloud Run (GCP) está DEPRECADO** — billing off (`503`). **Não** `gcloud run deploy`. API+worker = **Hetzner VPS + Cloudflare Tunnel** (`docker-compose.prod.yml` + `./scripts/deploy.sh`). Staging: `api-hetzner.getgymsite.com.br`. Bootstrap: [`scripts/hetzner/`](../../scripts/hetzner/). Free teste: [`scripts/oracle/`](../../scripts/oracle/).
> **503 legado Cloud Run:** [RUNBOOK_GCLOUD_503_BILLING.md](../../docs/RUNBOOK_GCLOUD_503_BILLING.md) — **não** redeployar GCP.
> **Legado (não seguir como prod):** Cloud Run, Docker Compose local, Vercel/Netlify, `cloudbuild.frontend.yaml`, Actions `pages.yml`.

## Stack produção

| Camada | Destino |
|---|---|
| API | **Hetzner** `/opt/gymsite` · compose `api` · túnel CF → `api.getgymsite.com.br` / `gymsite-api.vectracargo.com.br` |
| Worker pipeline | **Mesma VPS** · compose `worker` (`RUN_QUEUE_WORKER=1`) |
| Front app logado | CF Pages projeto `gymsite` → `getgymsite.com.br` |
| Landing | CF `gym-insight-hub` → `gymsite.com.br` (repo separado) |
| Banco | Supabase `epgedaiukjippepujuzc` (`gymsite` / `shared`; `public` = views) |
| Fila | Redis **na VPS** (`redis://redis:6379/0`) |

**Órfão:** não usar projeto GCP `gen-lang-client-0662901510`.

## Deploy (resumo)

Detalhe: **`/deploy`**. Ordem:

1. Gate: `.venv` pytest + `frontend` `tsc --noEmit`
2. Migrations → `/migrate` (1 SQL)
3. API **Hetzner** (na VPS): `cd /opt/gymsite && ./scripts/deploy.sh` (imagem GHCR) **ou** `docker compose -f docker-compose.prod.yml up -d --build`. Worker sobe no mesmo compose — **não** Cloud Run.
4. Front app: `cd frontend; npm run build; npx wrangler pages deploy ./dist --project-name gymsite`
5. Landing: `cd gym-insight-hub; npm run build; npx wrangler pages deploy ./dist --project-name gym-insight-hub`
6. Health: `https://api-hetzner.getgymsite.com.br/health` (staging) · após cutover `https://api.getgymsite.com.br/api/health`

**Act-on:** mudou `agents/` · `tools/` · `api.py` → deploy **Hetzner** (compose api+worker). Só seed SQL → VPS **não**. **Nunca** `gcloud run deploy`.

## Env / secrets (nomes)

Backend/worker (`.env.production` na VPS): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SEARCHAPI_KEY`, `REDIS_URL`, `GEMINI_*` / `NVIDIA_API_KEY` (`PIPELINE_LLM_PROVIDER=nvidia`; Vertex off, `GOOGLE_GENAI_USE_VERTEXAI=false`), `GOOGLE_MAPS_API_KEY`, `GYMSITE_SCHEMA_SEP`, `PIPELINE_MAX_WALL_SEC`, `A0_*`, `RUN_QUEUE_WORKER` (worker=`1`; API=`0`, só enqueue).

Front build (`VITE_*`): `VITE_API_BASE`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (`sb_publishable_*` — não JWT legado). Ver P-000 gotcha CF Pages.

## Domínios

| Host | Papel |
|---|---|
| `getgymsite.com.br` | App logado |
| `gymsite.com.br` | Landing / degustação |
| `api.getgymsite.com.br` | API (Hetzner via Cloudflare Tunnel) |

## Health / logs

```powershell
Invoke-RestMethod https://api.getgymsite.com.br/api/version
Invoke-RestMethod https://api.getgymsite.com.br/api/health

# Logs na VPS (SSH) — API e worker rodam no compose:
ssh <user>@<vps> 'cd /opt/gymsite && docker compose -f docker-compose.prod.yml logs --tail=50 worker'
ssh <user>@<vps> 'cd /opt/gymsite && docker compose -f docker-compose.prod.yml ps'
```

Pipeline preso → Redis `processing` órfãos + `/debug`.

**503 no `/health`:** NÃO redeployar de imediato. Seguir [RUNBOOK_GCLOUD_503_BILLING.md](../../docs/RUNBOOK_GCLOUD_503_BILLING.md) — causa típica = `billingEnabled: false` (serviço `Ready` mas tráfego barrado).

## Anti-padrões

- ❌ Redeployar Cloud Run em 503 sem checar billing (`gcloud beta billing projects describe`)
- ❌ Deploy “prod” via Docker local / Cloudflared
- ❌ Atualizar API sem sync `gymsite-worker`
- ❌ Publicar monorepo no CF da landing (`gym-insight-hub`)
- ❌ Commitar `.env` / secrets
- ❌ Reaplicar `db/migrations/*.sql` em lote no deploy
- ❌ Usar projeto órfão `gen-lang-client-0662901510`

## Local (dev only)

Uvicorn **na raiz** `gymsite/` (nunca em `backend/` — `api.py` fica na raiz):

```powershell
cd C:\Users\marce\gymsite
& "C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe" -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Smoke: `http://127.0.0.1:8000/health`. Lê o mesmo Supabase de prod. **Não** é path de produção. Compose/Cloudflared = histórico handbook Part 4.
