# Roteiro local — API GymSite no PC (R$0 host)

Quando Cloud Run 503 / Oracle Ampere sem capacidade / Hetzner não pago.
Canônico ops: skill `gymsite-devops` · staging futuro: `scripts/oracle/` · `scripts/hetzner/`.

## O que sobe

| Peça | Onde |
|---|---|
| API FastAPI + worker pipeline | `uvicorn` na raiz `gymsite/` |
| Redis (fila) | Docker `redis:7` local **ou** Redis já no `.env` |
| Front | opcional: `VITE_API_BASE=http://127.0.0.1:8000` |
| URL pública | **não** — só `127.0.0.1` (PC ligado) |

`RUN_QUEUE_WORKER` default = **on** → um único processo API **já consome** a fila. Não precisa segundo container worker.

## Pré-requisitos

1. Secrets em `.env` na raiz `C:\Users\marce\gymsite` (copiar de `.env.production.example` se faltar). Mínimo: `SUPABASE_*`, `SEARCHAPI_KEY`, Maps, `PIPELINE_LLM_PROVIDER=nvidia` + `NVIDIA_API_KEY` (Vertex off).
2. Python do projeto (preferir):
   `C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe`
3. Docker Desktop **ligado** se Redis for local.

## Passo a passo (PowerShell)

### 1) Redis local

```powershell
docker run -d --name gymsite-redis -p 6379:6379 redis:7-alpine
```

No `.env`:

```
REDIS_URL=redis://127.0.0.1:6379/0
```

(Se Redis Cloud/Upstash no `.env` já funciona — pula o docker.)

### 2) API

```powershell
cd C:\Users\marce\gymsite
$env:RUN_QUEUE_WORKER = "1"
& "C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe" -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

**Nunca** rodar de dentro de `backend/` — `api.py` fica na raiz.

### 3) Smoke

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/version
```

### 4) Front (opcional)

No `frontend/.env.local` (não commit):

```
VITE_API_BASE=http://127.0.0.1:8000
```

Depois `npm run dev` no `frontend/`.

### 5) Relatório CLI (sem browser)

```powershell
cd C:\Users\marce\gymsite
& "C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe" tools/run_relatorio_cli.py --help
```

(Usa mesmo `.env` / Supabase.)

## PDF no browser

App logado apontando pra API local → abrir relatório → PDF. Auth JWT / access token como em prod.

## Parar

- Terminal: `Ctrl+C` no uvicorn
- Redis: `docker stop gymsite-redis`

## Limites

- PC dormiu / desligou → API morre
- `getgymsite.com.br` prod **não** usa essa API (ainda 503 no Cloud Run)
- Não substitui Oracle/Hetzner pra cliente real

## Próximo quando Ampere/Hetzner voltar

Mesmo `.env` → `scripts/oracle` ou `scripts/hetzner` + staging `api-hetzner.getgymsite.com.br`.
