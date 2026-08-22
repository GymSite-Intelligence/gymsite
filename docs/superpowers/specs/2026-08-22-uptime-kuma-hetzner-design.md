# Design: Uptime Kuma na Hetzner + Cloudflare Tunnel

**Data:** 2026-08-22  
**Status:** aprovado (Marcelo) — Access Cloudflare opcional  
**Relacionado:** `docs/PLAN_HETZNER_VPS_TUNNEL.md`, `docker-compose.prod.yml`, `cloudflared/config.yml`

## Problema

Health `/health` confirma “API no ar agora”. Não acumula downtime mensal (error budget / SLO). Monitor externo precisa sobreviver se a API cair e não abrir porta pública na VPS.

## Decisão

Rodar **Uptime Kuma** no mesmo Compose de produção (rede `gymsite`), sem `ports:` no host. Expor só via Cloudflare Tunnel em `status.getgymsite.com.br` → `http://uptime-kuma:3001`.

Auth em camadas:

1. **Obrigatório:** senha admin do próprio Kuma (setup no 1º acesso).
2. **Opcional (fase 2):** Cloudflare Access (Zero Trust) no hostname — **não** é o login React `/admin/*`.

## Arquitetura

```text
Browser → Cloudflare Edge (status.getgymsite.com.br)
       → Tunnel (cloudflared no compose)
       → http://uptime-kuma:3001  (rede Docker gymsite)

Kuma polls (egress HTTPS):
  → https://api-hetzner.getgymsite.com.br/health
  → https://api.getgymsite.com.br/health
```

Mesmo padrão da API: cloudflared fala com hostname Docker (`gymsite-api:8000` / `uptime-kuma:3001`), nunca `localhost` dentro do container do túnel.

## Mudanças de arquivo

### `docker-compose.prod.yml`

Adicionar serviço + volume:

```yaml
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    volumes:
      - uptime-kuma-data:/app/data
    restart: unless-stopped
    # sem ports: — só rede interna gymsite

volumes:
  redis-data:
  uptime-kuma-data:
```

Rede default do compose já se chama `gymsite` — Kuma entra nela automaticamente.

### `cloudflared/config.yml`

Inserir **antes** do catch-all `http_status:404`:

```yaml
  - hostname: status.getgymsite.com.br
    service: http://uptime-kuma:3001
    originRequest:
      connectTimeout: 30s
      http2Origin: false
      noTLSVerify: true
```

### DNS (manual na VPS / CF)

```bash
cloudflared tunnel route dns 12675577-d94b-4a19-b1df-a86713dbaf80 status.getgymsite.com.br
```

(ID do túnel já no `cloudflared/config.yml`.)

### Docs

- Nota em `scripts/hetzner/README.md`: hostname status + checks.
- Este arquivo em `docs/superpowers/specs/`.

## Configuração UI (pós-deploy, humano)

| Check | URL | Intervalo | Critério |
|-------|-----|-----------|----------|
| API staging | `https://api-hetzner.getgymsite.com.br/health` | 60s | HTTP 200 + keyword `"status":"ok"` |
| API prod | `https://api.getgymsite.com.br/health` | 60s | HTTP 200 + keyword `"status":"ok"` |

SLO alvo: **99.9%** uptime (~43 min downtime/mês). Alerta Discord/Telegram quando budget ~**80%** usado (config no Kuma, não no app).

## Aceite (testável)

1. `docker compose -f docker-compose.prod.yml ps` mostra `uptime-kuma` Up.
2. `https://status.getgymsite.com.br` responde tela de login/setup do Kuma (HTTPS).
3. Nenhum `0.0.0.0:3001` publicado no host (`ss -tlnp` / `docker ps` sem 3001).
4. Dois monitors verdes após ~2–3 ciclos (≤3 min).
5. API e worker inalterados; `deploy.sh` health+rollback intacto.

## Fora de escopo

- Endpoint `/admin/error-budget` em FastAPI / token na query.
- Card error-budget no React admin.
- Expor `:3001` no host.
- Cloudflare Access (fase 2, se quiser segundo cadeado).
- Mudança de código app (`api.py`, frontend).
- Proxy Pages → API via `wrangler` routes.

## Self-review

**Data:** 2026-08-22  

| Check | Resultado |
|-------|-----------|
| Placeholder | Nenhum TBD aberto; Access marcado fase 2 opcional |
| Consistência | Origin `uptime-kuma:3001` alinhado ao padrão `gymsite-api:8000` |
| Escopo | Um plano: compose + tunnel + DNS + UI checks |
| Ambiguidade | Auth = senha Kuma; Access ≠ React admin |
| Aceite | 5 critérios pass/fail |
| Fora | Lista explícita |

**Resultado:** ok.
