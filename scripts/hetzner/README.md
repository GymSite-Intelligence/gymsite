# Hetzner VPS — bootstrap (pré-cutover)

Canônico: [`docs/PLAN_HETZNER_VPS_TUNNEL.md`](../../docs/PLAN_HETZNER_VPS_TUNNEL.md).

## Decisões travadas (2026-08-05)

| # | Escolha |
|---|---|
| 1 | Preparar código/scripts **antes** de criar a VPS |
| 2 | **Redis na VPS** (`redis://redis:6379/0` no compose) |
| 3 | Validar em **staging** `api-hetzner.getgymsite.com.br` antes do cutover DNS |

## Quando você criar a CX32

No painel Hetzner Cloud:

1. Server type **CX32**, image **Ubuntu 24.04**, região FSN ou NBG.
2. SSH key do Marcelo; firewall cloud: **só TCP 22** (não abrir 80/443).
3. Anotar o IPv4 público.

Na VPS:

```bash
# Como root (ou sudo)
curl -fsSL https://raw.githubusercontent.com/Marcelo-Rosas/gymsite_intelligence/main/scripts/hetzner/bootstrap.sh \
  | bash
# Ou, se já clonou:
sudo bash /opt/gymsite/scripts/hetzner/bootstrap.sh
```

Depois (secrets locais — nunca commit):

```bash
# Do seu PC (PowerShell / scp)
scp .env.production root@IP_VPS:/opt/gymsite/.env.production
scp cloudflared/credentials.json root@IP_VPS:/opt/gymsite/cloudflared/credentials.json

# Na VPS
cd /opt/gymsite
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

## Staging HTTPS (antes de mexer em produção)

1. Confirmar túnel `12675577-d94b-4a19-b1df-a86713dbaf80` no Zero Trust.
2. Ingress já tem `api-hetzner.getgymsite.com.br` em `cloudflared/config.yml`.
3. Criar rota DNS (uma vez):

   ```bash
   cloudflared tunnel route dns 12675577-d94b-4a19-b1df-a86713dbaf80 api-hetzner.getgymsite.com.br
   ```

4. Smoke:

   ```powershell
   Invoke-RestMethod https://api-hetzner.getgymsite.com.br/health
   ```

5. Só então: Fase 3 cutover (`gymsite-api.vectracargo.com.br` / `api.getgymsite.com.br`).

## Deploy rolling (já existente)

```bash
cd /opt/gymsite
./scripts/deploy.sh [tag]   # usa docker-compose.prod.yml + GHCR
```

## Checklist pré-VPS (repo)

- [x] `docker-compose.prod.yml` (api + worker + redis + cloudflared)
- [x] Ingress staging + prod em `cloudflared/config.yml`
- [x] `scripts/hetzner/bootstrap.sh`
- [x] `REDIS_URL=redis://redis:6379/0` no `.env.production.example`
- [ ] Criar CX32 + copiar secrets
- [ ] Rota DNS staging
- [ ] Cutover DNS prod (Fase 3)
