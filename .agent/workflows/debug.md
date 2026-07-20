---
description: Systematic debugging — isolate API vs worker, Cloud Run logs, fontes/Places. Root-cause first.
---

# Workflow: /debug

> **Skill:** conforme domínio. **Regras:** P-000 §2 (ler fonte) · [REGRAS §3.5](../rules/REGRAS_USO_GLOBAL.md).
> **Não confundir:** `/audit` · `/review`. Pipeline ADK = **`gymsite-worker`**; API enfileira Redis.
> **Não existe:** `docs/KNOWN_ISSUES.md` (não criar stub vazio — documentar no PR/caso auditoria).

## Triagem rápida (prod)

| Sintoma | Onde olhar primeiro |
|---|---|
| POST ok, `status=queued` eterno | Redis `gymsite:queue` / worker up / `RUN_QUEUE_WORKER` |
| `running` + `etapa_atual` vazia/travada | Worker logs + `gymsite:queue:processing` órfãos |
| A3a lento / Places caro | ledger `api_sku` · log `fallback Places` |
| Aluguel “errado” | `fonte_aluguel` MRLR vs listing |
| Front 200 API 5xx | `api.getgymsite.com.br` vs Pages; CORS/`VITE_API_BASE` |
| Split API≠worker | imagem/`GIT_SHA`/`PIPELINE_MAX_WALL_SEC` nos **dois** serviços |

GCP: `gen-lang-client-0106729343` · `us-central1`.

## Steps

1. **Reproduce**
   - Erro exato, UUID `relatorio_id`, horário UTC
   - Ambiente: local / prod Cloud Run (não “docker” como path canônico)
   - `git log --oneline -5` no branch relevante

2. **Isolate API vs worker**
   ```powershell
   gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="gymsite-api" AND textPayload:"RELATORIO_ID"' --project=gen-lang-client-0106729343 --limit=30 --freshness=2h
   gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="gymsite-worker" AND textPayload:"RELATORIO_ID"' --project=gen-lang-client-0106729343 --limit=50 --freshness=2h
   ```
   Enqueue/WS → API. A0–A9 / enrich → **worker**.

3. **Redis / fila** (se pipeline preso)
   - `LLEN gymsite:queue` · `HGETALL gymsite:queue:processing`
   - Pós-deploy SIGTERM: jobs órfãos em `processing` — drain + fail stuck + re-smoke

4. **Hypothesize** (≤3 causas, rank)
   - Ler código/tool antes de “achismo” (P-000 §2)
   - Fontes: SearchAPI 401? Places fallback? MRLR inputs cidade/bairro?

5. **Test**
   ```powershell
   .\.venv\Scripts\python.exe -m pytest path\to\test_repro.py -x --tb=short
   Invoke-RestMethod https://api.getgymsite.com.br/api/version
   Invoke-RestMethod https://api.getgymsite.com.br/api/health
   ```
   SB: `relatorios` / `relatorio_api_calls` / `relatorio_outputs` schema `gymsite`.

6. **Fix**
   - Causa raiz + teste que falhava antes
   - Se `agents/`/`tools/`: Cloud Run API **+** sync worker (`/deploy`)

7. **Document**
   - PR / caso `/audit` se conformidade
   - Não inventar `KNOWN_ISSUES.md`

## Comandos úteis

```powershell
# Versão / health prod
Invoke-RestMethod https://api.getgymsite.com.br/api/version

# Status relatório
Invoke-RestMethod "https://api.getgymsite.com.br/api/relatorios/<UUID>/status"

# Imagem API (p/ sync worker)
gcloud run services describe gymsite-api --region=us-central1 --project=gen-lang-client-0106729343 --format="value(spec.template.spec.containers[0].image)"
```
