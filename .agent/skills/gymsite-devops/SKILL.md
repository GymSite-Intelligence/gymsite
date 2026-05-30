---
name: gymsite-devops
description: Infraestrutura, deploy, Docker e operações para GymSite Intelligence. Use ao configurar ambientes, containers, túneis Cloudflared, ou CI/CD. NÃO use para lógica de negócio, endpoints REST ou componentes UI.
---

# GymSite Intelligence — DevOps e Infraestrutura

## Contexto da Stack

- **Container:** Docker + Docker Compose
- **Reverse Proxy / Tunnel:** Cloudflared (cloudflare tunnel)
- **Frontend:** Vite build → Nginx (opcional) ou Vercel
- **Backend:** Uvicorn + FastAPI (porta 8000)
- **Banco:** Supabase (PostgreSQL hospedado) — NÃO roda local
- **Cache:** Redis (opcional, via Supabase ou local)

## Docker

### Dockerfile (Backend)

```dockerfile
FROM python:3.14-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./artifacts:/app/artifacts
      - ./competitor_cache:/app/competitor_cache
```

## Cloudflared Tunnel

```bash
# Configuração em cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: /app/cloudflared/credentials.json
ingress:
  - hostname: api.gymsite.app
    service: http://localhost:8000
  - service: http_status:404
```

### Comandos Úteis

```bash
# Iniciar túnel
cloudflared tunnel run <nome>

# Verificar status
cloudflared tunnel info <nome>

# Logs
cloudflared tunnel tail <nome>
```

## Variáveis de Ambiente Obrigatórias

```bash
# Backend
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_GYMSITE_ORG_ID=uuid-da-org
GEMINI_API_KEY=AIza...
GOOGLE_MAPS_API_KEY=AIza...
APOLLO_API_KEY=apk_...          # opcional

# Frontend
VITE_API_BASE_URL=https://api.gymsite.app
VITE_SUPABASE_URL=https://<ref>.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

## Deploy — Checklist

1. **Banco:** Rodar migrations em `db/migrations/`
2. **Backend:** Build Docker image → push → restart container
3. **Frontend:** `npm run build` → deploy dist/ (Vercel/Netlify)
4. **Cloudflared:** Verificar tunnel ativo
5. **Health check:** `GET /api/health` deve retornar 200

## Health Check

```python
@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
```

## Anti-padrões

- ❌ Nunca commite `.env` — use `.env.example` como template
- ❌ Não exponha porta 8000 diretamente — use Cloudflared ou Nginx
- ❌ Não use `python -m api` em produção — use `uvicorn` com workers
- ❌ Não ignore logs do Cloudflared — monitore erros de ingress

## Monitoramento

```bash
# Verificar consumo de memória
docker stats gymsite_api

# Logs em tempo real
docker logs -f gymsite_api

# Health check remoto
curl https://api.gymsite.app/api/health
```
