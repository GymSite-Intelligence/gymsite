# Oracle Cloud Always Free — bootstrap (pré-cutover)

Canônico Hetzner (pago): [`docs/PLAN_HETZNER_VPS_TUNNEL.md`](../../docs/PLAN_HETZNER_VPS_TUNNEL.md).  
Este path = **R$0** no host (Ampere A1). Mesmo `docker-compose.prod.yml` + túnel Cloudflare.

## Por que Ampere (não “VM.Standard.E2.1.Micro”)

| Shape Always Free | RAM | Serve GymSite? |
|---|---|---|
| **VM.Standard.A1.Flex** (Ampere ARM) | até **24 GB** / 4 OCPU | **sim** — use isto |
| VM.Standard.E2.1.Micro (AMD) | **1 GB** | **não** — OOM garantido |

Imagem GHCR: CI já publica `linux/amd64,linux/arm64` (ver `.github/workflows/ci-cd.yml`). Na Ampere o pull pega **arm64**.

## Fase 0 — Conta (você no browser)

1. Abrir https://cloud.oracle.com → **Sign Up** (Always Free elegível).
2. Cartão: Oracle **valida** e pode cobrar R$0 — não é Hetzner; ainda exige cartão na maioria dos países.
3. Home region: escolha **uma** e não troque (capacidade Ampere some fácil). Preferir região com vaga (ex. experimente `sa-saopaulo-1` ou `us-ashburn-1` se SP lotado).
4. Se “Out of capacity” no create: mudar AD / shape OCPU / região home (nova conta) — comum.

## Fase 1 — Criar compute Ampere

Console → **Compute → Instances → Create**:

| Campo | Valor |
|---|---|
| Name | `gymsite-api` |
| Image | **Canonical Ubuntu 24.04** (ou 22.04) |
| Shape | **Ampere** → `VM.Standard.A1.Flex` |
| OCPUs | **2** (começar; sobe pra 4 se precisar) |
| Memory | **12 GB** (ou 24 se 4 OCPU) |
| Networking | VCN default; assign **public IPv4** |
| SSH keys | colar chave pública do Marcelo |
| Boot volume | ≥ **50 GB** (Always Free boot tem limite; 50 GB ok no free) |

**Firewall Oracle (obrigatório):**

- VCN → Subnet → **Security List** (ou NSG): ingress **TCP 22** só do teu IP (não abrir 80/443 — tráfego via Cloudflare Tunnel).
- No Ubuntu: `ufw` no `bootstrap.sh` também só SSH.

Anotar **Public IP**.

## Fase 2 — Bootstrap na VM

```bash
ssh ubuntu@IP_PUBLICO   # ou opc@ conforme image

# root
curl -fsSL https://raw.githubusercontent.com/Marcelo-Rosas/gymsite_intelligence/main/scripts/oracle/bootstrap.sh \
  | sudo bash
# ou, se já clonou:
sudo bash /opt/gymsite/scripts/oracle/bootstrap.sh
```

Secrets (do PC):

```powershell
scp .env.production ubuntu@IP:/opt/gymsite/.env.production
scp cloudflared/credentials.json ubuntu@IP:/opt/gymsite/cloudflared/credentials.json
```

Na VM:

```bash
cd /opt/gymsite
# garantir REDIS_URL=redis://redis:6379/0 no .env.production
docker compose -f docker-compose.prod.yml up -d --build
# se GHCR arm64 já existir: omitir --build e usar pull
docker compose -f docker-compose.prod.yml ps
```

Health interno:

```bash
docker compose -f docker-compose.prod.yml exec api \
  python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/health').text)"
```

## Fase 3 — Staging HTTPS (mesmo do Hetzner)

Ingress já tem `api-hetzner.getgymsite.com.br`.

```bash
cloudflared tunnel route dns 12675577-d94b-4a19-b1df-a86713dbaf80 api-hetzner.getgymsite.com.br
```

Smoke:

```powershell
Invoke-RestMethod https://api-hetzner.getgymsite.com.br/health
```

## Riscos Oracle (ler antes)

- **Capacity:** create falha “Out of host capacity” → retry outro AD / menos OCPU / outra home region.
- **Cartão:** signup Always Free ainda pede cartão na prática BR.
- **Idle reclaim:** conta free sem uso pode ser reclamada — manter instância up + billing alerts.
- **arm64:** se `docker pull` só achar amd64, build **na VM**: `docker compose -f docker-compose.prod.yml build` (lento 1ª vez).
- **Não** use micro AMD 1 GB.

## Checklist

- [ ] Conta Always Free + home region
- [ ] Instance A1.Flex (2 OCPU / 12 GB+) Ubuntu + SSH
- [ ] Security List: só TCP 22
- [ ] `scripts/oracle/bootstrap.sh`
- [ ] `.env` + `credentials.json` + compose up
- [ ] Staging `api-hetzner.getgymsite.com.br` verde
- [ ] Cutover prod = depois (mesmo plano Hetzner Fase 3)
