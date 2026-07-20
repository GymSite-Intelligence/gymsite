---
name: gymsite-devops
description: Deploy e ops GymSite — Cloud Run (API+worker), Cloudflare Pages/Wrangler, env/secrets. Use ao publicar, sincronizar worker, health prod. NÃO use para lógica de negócio, endpoints REST ou UI. Path canônico = workflow /deploy (P-000 §7–§8).
---

# GymSite Intelligence — DevOps

> **Canônico:** [P-000 §7–§8](../../rules/P-000_REGRA_MESTRA_MUDANCA.md) · [REGRAS §3.5](../../rules/REGRAS_USO_GLOBAL.md) · workflow [`.agent/workflows/deploy.md`](../../workflows/deploy.md).
> **Legado (não seguir como prod):** Docker Compose local, Cloudflared tunnel, Vercel/Netlify, `cloudbuild.frontend.yaml`, Actions `pages.yml`.

## Stack produção

| Camada | Destino |
|---|---|
| API | Cloud Run `gymsite-api` · GCP `gen-lang-client-0106729343` · `us-central1` |
| Worker pipeline | Cloud Run `gymsite-worker` — **mesma imagem** da API (não auto-deploya) |
| Front app logado | CF Pages projeto `gymsite` → `getgymsite.com.br` |
| Landing | CF `gym-insight-hub` → `gymsite.com.br` (repo separado) |
| Banco | Supabase `epgedaiukjippepujuzc` (`gymsite` / `shared`; `public` = views) |
| Fila | Redis (`gymsite:queue`) |

**Órfão:** não usar projeto GCP `gen-lang-client-0662901510`.

## Deploy (resumo)

Detalhe: **`/deploy`**. Ordem:

1. Gate: `.venv` pytest + `frontend` `tsc --noEmit`
2. Migrations → `/migrate` (1 SQL)
3. API Cloud Run (Build em `main` ou `gcloud run deploy`)
4. **Sync worker imagem** (obrigatório após API):
   ```powershell
   $IMG = gcloud run services describe gymsite-api --region=us-central1 --project=gen-lang-client-0106729343 --format="value(spec.template.spec.containers[0].image)"
   gcloud run services update gymsite-worker --region=us-central1 --project=gen-lang-client-0106729343 --image $IMG
   ```
5. Front: `cd frontend; npm run build; npx wrangler pages deploy ./dist --project-name gymsite`
6. Health: `https://api.getgymsite.com.br/api/version` + `/api/health`

**Act-on:** mudou `agents/` · `tools/` · `api.py` · `parametros_metodologia.py` → Cloud Run **sim** + worker. Só seed SQL → Cloud Run **não**.

## Env / secrets (nomes)

Backend/worker (Secret Manager / Cloud Run env): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SEARCHAPI_KEY`, `REDIS_URL`, `GEMINI_*` / Vertex, `GOOGLE_MAPS_API_KEY`, `GYMSITE_SCHEMA_SEP`, `PIPELINE_MAX_WALL_SEC`, `A0_*`, `RUN_QUEUE_WORKER` (worker=`1`; API preferível `0` se só enqueue).

Front build (`VITE_*`): `VITE_API_BASE`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (`sb_publishable_*` — não JWT legado). Ver P-000 gotcha CF Pages.

## Domínios

| Host | Papel |
|---|---|
| `getgymsite.com.br` | App logado |
| `gymsite.com.br` | Landing / degustação |
| `api.getgymsite.com.br` | API Cloud Run |

## Health / logs

```powershell
Invoke-RestMethod https://api.getgymsite.com.br/api/version
Invoke-RestMethod https://api.getgymsite.com.br/api/health

gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="gymsite-worker"' --project=gen-lang-client-0106729343 --limit=20 --freshness=1h
```

Pipeline preso → Redis `processing` órfãos + `/debug`.

## Anti-padrões

- ❌ Deploy “prod” via Docker local / Cloudflared
- ❌ Atualizar API sem sync `gymsite-worker`
- ❌ Publicar monorepo no CF da landing (`gym-insight-hub`)
- ❌ Commitar `.env` / secrets
- ❌ Reaplicar `db/migrations/*.sql` em lote no deploy

## Local (dev only)

Uvicorn local + `.env` ok para smoke de endpoint. **Não** é path de produção. Compose/Cloudflared = histórico handbook Part 4.
