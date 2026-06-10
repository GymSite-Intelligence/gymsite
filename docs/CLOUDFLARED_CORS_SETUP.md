# Cloudflared + CORS — Setup de Produção

Guia completo para expor o GymSite Intelligence via Cloudflare Tunnel com CORS seguro e preflight robusto.

---

## 1. Arquitetura

```
┌─────────────────────────────┐      ┌─────────────────────────────┐
│   Browser (app.vectracargo) │ ──►  │  Cloudflare Edge (HTTPS)    │
└─────────────────────────────┘      └─────────────────────────────┘
                                              │
                                              ▼
                                     ┌─────────────────────────────┐
                                     │  cloudflared container      │
                                     │  (túnel seguro)             │
                                     └─────────────────────────────┘
                                              │
                                              ▼
                                     ┌─────────────────────────────┐
                                     │  FastAPI (uvicorn)          │
                                     │  porta 8000                 │
                                     └─────────────────────────────┘
```

---

## 1.1 Dev local — tunnel desligado (menos ruído no Docker)

Por padrão, `docker compose up -d` sobe **só a API** (`http://localhost:8000`). O `cloudflared` está no profile `tunnel`.

```powershell
# API local, sem logs do tunnel / probes da borda Cloudflare
docker compose up -d api

# Parar tunnel se ainda estiver rodando de antes
docker compose stop cloudflared

# Expor gymsite-api.vectracargo.com.br (frontend Pages em produção)
docker compose --profile tunnel up -d
```

Com o tunnel parado, o site em **Pages** ainda abre, mas chamadas a `https://gymsite-api.vectracargo.com.br` falham até subir o profile `tunnel` (ou VM de produção).

---

## 2. Arquivos

### 2.1 `cloudflared/config.yml`

```yaml
tunnel: dbad2419-2271-42e1-840f-40864fa53298
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: api.vectracargo.com.br
    service: http://api:8000
    originRequest:
      connectTimeout: 30s
      keepAliveTimeout: 90s
      keepAliveConnections: 100
      http2Origin: false        # evita inconsistências com preflight/headers
      noTLSVerify: true

  - hostname: gymsite-api.vectracargo.com.br
    service: http://api:8000
    originRequest:
      connectTimeout: 30s
      keepAliveTimeout: 90s
      keepAliveConnections: 100
      http2Origin: false
      noTLSVerify: true

  - service: http_status:404
```

> **Nota:** `http2Origin: false` remove variáveis de HTTP/2 para origin que podem quebrar preflight.

---

### 2.2 `docker-compose.yml`

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: gymsite-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ${CNO_DATA_DIR_HOST}:/data/cno:ro
    env_file:
      - .env
    environment:
      DEEP_RESEARCH_AGENT: deep-research-preview-04-2026
      DEEP_RESEARCH_TIMEOUT_SEC: "420"
      CNPJ_ENRIQUECER_MAX: "3"
    command: >
      uvicorn api:app
      --host 0.0.0.0
      --port 8000
      --proxy-headers
      --forwarded-allow-ips='*'
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8000/health"]
      interval: 30s
      timeout: 5s
      start_period: 40s
      retries: 3
    networks:
      - appnet

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: gymsite-tunnel
    restart: unless-stopped
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflared:/etc/cloudflared:ro
    depends_on:
      api:
        condition: service_healthy
    networks:
      - appnet

networks:
  appnet:
    driver: bridge
```

---

### 2.3 `Dockerfile` (relevante)

```dockerfile
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
```

---

### 2.4 CORS no `api.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

_cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

# Preflight catch-all — garante 204 mesmo se o router nao capturar
@app.options("/{path:path}")
async def preflight_catchall(path: str) -> None:
    return None
```

Configure no `.env`:
```
CORS_ORIGINS=https://app.vectracargo.com.br,https://gymsite.vectracargo.com.br
```

---

## 3. Validação

### 3.1 Build e subir

```bash
docker compose up -d --build
```

### 3.2 Testar preflight (OPTIONS)

```bash
curl -i -X OPTIONS "https://api.vectracargo.com.br/api/auth/login" \
  -H "Origin: https://app.vectracargo.com.br" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization"
```

**Esperado:** status `200` ou `204` com header `access-control-allow-origin: https://app.vectracargo.com.br`

### 3.3 Testar GET real

```bash
curl -i "https://api.vectracargo.com.br/health" \
  -H "Origin: https://app.vectracargo.com.br"
```

**Esperado:** status `200` com header `access-control-allow-origin` presente.

---

## 4. Troubleshooting

| Sintoma | Causa provável | Solução |
|---|---|---|
| `CORS error` no browser | `allow_origins` não contém o domínio do frontend | Adicionar ao `.env` `CORS_ORIGINS` |
| `403` no OPTIONS | Cloudflared ou proxy bloqueando preflight | Verificar `http2Origin: false`, adicionar `@app.options` catch-all |
| `301/302` no OPTIONS | Redirect de HTTP→HTTPS no origin | Garantir que `service:` aponta direto para o container, não para um proxy externo |
| `Connection refused` | Porta do backend errada no `config.yml` | Verificar se FastAPI está realmente na porta declarada (`8000`) |

---

## 5. Checklist de Deploy

- [ ] `credentials.json` do Cloudflared está em `./cloudflared/`
- [ ] `.env` contém `CORS_ORIGINS` com o domínio do frontend
- [ ] `config.yml` aponta `service:` para a porta correta do backend
- [ ] `docker-compose.yml` tem `--proxy-headers --forwarded-allow-ips='*'`
- [ ] Teste de preflight (`curl -X OPTIONS`) retorna 200/204 com headers CORS
- [ ] Teste de GET real retorna 200 com `access-control-allow-origin`
