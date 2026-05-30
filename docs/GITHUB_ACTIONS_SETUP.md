# CI/CD — GitHub Actions + GHCR + Deploy

Pipeline completo: **Build → Test → Push → Deploy**

Suporta 2 targets de deploy:
1. **VPS genérico** (DigitalOcean, Hetzner, AWS EC2, etc) — SSH direto
2. **Google Compute Engine (GCE)** — VM no projeto GCP `gen-lang-client-0106729343`

---

## Arquivos

| Arquivo | Propósito |
|---------|-----------|
| `.github/workflows/ci-cd.yml` | Workflow GitHub Actions |
| `docker-compose.prod.yml` | Stack de produção (API + Redis + nginx + cloudflared) |
| `scripts/deploy.sh` | Deploy manual/rollback no servidor |
| `scripts/bootstrap-gce.sh` | Cria VM no GCP com Docker pré-instalado |
| `scripts/setup-vm.sh` | Setup interno da VM (clone, permissões) |
| `nginx/nginx.conf` | Reverse proxy com rate limit, gzip, logs JSON |
| `.env.production.example` | Template de variáveis de produção |

---

## Opção A: Deploy em VPS Genérico (SSH)

### 1. Secrets do GitHub

| Secret | Descrição |
|--------|-----------|
| `SSH_HOST` | IP ou hostname do servidor |
| `SSH_USER` | Usuário SSH (com acesso ao Docker) |
| `SSH_PRIVATE_KEY` | Chave privada SSH (sem passphrase) |
| `SSH_PORT` | Porta SSH (default: 22) |
| `SLACK_WEBHOOK_URL` | (Opcional) Webhook pra notificações |

### 2. Setup no servidor

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
# Relogue

git clone https://github.com/marce/gymsite_intelligence.git ~/gymsite_intelligence
cd ~/gymsite_intelligence
cp .env.production.example .env.production
nano .env.production  # preencha os secrets
```

---

## Opção B: Deploy no Google Compute Engine (RECOMENDADO)

Você já tem projeto GCP ativo: `gen-lang-client-0106729343`

### 1. Bootstrap da VM (rode localmente)

```bash
cd gymsite_intelligence

# Requisito: gcloud CLI instalado e autenticado
# https://cloud.google.com/sdk/docs/install

# Cria a VM no GCP (2 vCPU, 4 GB, 50 GB SSD)
bash scripts/bootstrap-gce.sh
```

O script faz tudo automaticamente:
- Cria VM `gymsite-api` na zona `southamerica-east1-a`
- Instala Docker + docker-compose-plugin
- Configura firewall rule pra SSH (porta 22)
- Importa sua chave `~/.ssh/id_ed25519.pub`
- Roda `setup-vm.sh` dentro da VM

**Output esperado:**
```
IP externo:     34.95.xxx.xxx
SSH:            ssh -i ~/.ssh/id_ed25519 ubuntu@34.95.xxx.xxx
```

### 2. Copiar secrets pra VM

```bash
VM_IP=34.95.xxx.xxx  # substitua pelo IP real

# .env.production
scp -i ~/.ssh/id_ed25519 .env.production ubuntu@$VM_IP:/opt/gymsite/.env.production

# Cloudflared (se usar tunnel)
scp -i ~/.ssh/id_ed25519 -r .cloudflared/* ubuntu@$VM_IP:/opt/gymsite/cloudflared/
```

### 3. Secrets do GitHub (para deploy automático)

| Secret | Valor |
|--------|-------|
| `SSH_HOST` | IP externo da VM (ex: `34.95.xxx.xxx`) |
| `SSH_USER` | `ubuntu` |
| `SSH_PRIVATE_KEY` | Conteúdo completo de `~/.ssh/id_ed25519` |
| `GCP_SA_KEY` | (Opcional) Conteúdo de `.gcp/gymsite-sa.json` pra deploy via gcloud |
| `GCP_VM_NAME` | `gymsite-api` |
| `GCP_ZONE` | `southamerica-east1-a` |
| `SLACK_WEBHOOK_URL` | (Opcional) |

---

## Estratégia de Deploy (Rolling Update)

O workflow usa **rolling update** com health check:

1. Pull da nova imagem no GHCR
2. Sobe novo container lado a lado com o antigo (`--scale api=2`)
3. Executa health check no novo container (`/health`)
4. Se saudável: remove o antigo (`--scale api=1`)
5. Se falhar: **rollback automático** — mata o novo, mantém o antigo

```
   [Old Container]          [New Container]
        │    (running)    │    (health check)
        │         │       │         │
        │    (scale=2)    │         │
        │         │       │    (health OK)
        │    (stop)       │    (scale=1)
        ▼                 ▼
                    [New Container]
```

---

## Tags Docker

| Evento | Tags geradas |
|--------|-------------|
| Push `main` | `latest`, `sha-abc1234` |
| Tag `v1.2.3` | `1.2.3`, `1.2`, `latest` |
| PR | `pr-42` |

---

## Comandos Úteis

### Local (sua máquina)
```bash
# SSH na VM
ssh -i ~/.ssh/id_ed25519 ubuntu@<VM_IP>

# Re-rodar bootstrap se necessário
bash scripts/bootstrap-gce.sh
```

### Na VM (produção)
```bash
# Logs em tempo real
cd /opt/gymsite && docker compose -f docker-compose.prod.yml logs -f api

# Métricas Prometheus
curl http://localhost:8000/api/metrics

# Redis CLI
docker compose -f docker-compose.prod.yml exec redis redis-cli

# Deploy manual (tag específica)
cd /opt/gymsite && bash scripts/deploy.sh v1.2.3

# Rollback manual (para imagem anterior)
docker compose -f docker-compose.prod.yml pull api
docker compose -f docker-compose.prod.yml up -d api

# Status do stack
docker compose -f docker-compose.prod.yml ps
```

---

## Arquitetura de Produção

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Cloudflare                                │
│                         (DNS + Tunnel)                              │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                         GCE VM                                      │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │   nginx     │────▶│  FastAPI    │────▶│    Redis    │           │
│  │  (reverse   │     │   (8000)    │     │   (cache)   │           │
│  │   proxy)    │     │             │     │             │           │
│  └─────────────┘     └─────────────┘     └─────────────┘           │
│         │                                                          │
│  ┌──────▼──────┐                                                   │
│  │ cloudflared │  (tunnel de saída — não precisa de IP público    │
│  │             │   exposto nas portas 80/443)                      │
│  └─────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     ┌─────────────┐
                     │  Supabase   │
                     │   (Cloud)   │
                     └─────────────┘
```

### Por que GCE em vez de Cloud Run?

| Critério | Cloud Run | GCE VM |
|----------|-----------|--------|
| Background tasks | ❌ Mortos após response | ✅ Rodem livremente |
| Playwright cold start | ❌ 30-60s | ✅ Zero (cached) |
| Redis | ❌ Memorystore ($) | ✅ Local gratuito |
| Timeout pipeline | ⚠️ Max 60min | ✅ Ilimitado |
| Custo baixo carga | ✅ Paga por request | ⚠️ VM ligada 24/7 |

**Para o GymSite, GCE é mais adequado** porque o pipeline ADK roda em background com timeout de 7 min e usa Playwright + Redis local.

---

## Troubleshooting

### VM não responde SSH
```bash
# Verifique se a VM está rodando
gcloud compute instances list --filter="name=gymsite-api"

# Se STOPPED, inicie:
gcloud compute instances start gymsite-api --zone=southamerica-east1-a

# Verifique firewall:
gcloud compute firewall-rules list --filter="name=allow-ssh"
```

### Deploy falha no health check
```bash
# Na VM, verifique logs
docker logs gymsite-api

# Verifique se .env.production existe
cat /opt/gymsite/.env.production

# Teste health manualmente
curl -v http://localhost:8000/health
```

### Imagem não pulla do GHCR
```bash
# Na VM, faça login manual
echo $GITHUB_TOKEN | docker login ghcr.io -u <user> --password-stdin

# Verifique se a imagem é pública
# GitHub → Package Settings → Change visibility → Public
```
