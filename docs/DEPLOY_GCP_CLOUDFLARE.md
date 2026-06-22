# Deploy GymSite Intelligence — GCP + Cloudflare Tunnel

> Arquitetura: **GitHub Actions** → **GHCR** → **GCE VM** → **Docker Compose** → **Cloudflare Tunnel** → **Internet**
>
> A VM não expõe portas públicas (exceto SSH). O Cloudflare Tunnel entrega o tráfego de forma segura.

---

## 0. Pré-requisitos

- [ ] Conta GCP com projeto ativo (ex: `<GCP_PROJECT_ID>`)
- [ ] `gcloud` CLI instalado e autenticado
- [ ] Conta Cloudflare com domínio configurado (ex: `vectracargo.com.br`)
- [ ] Chave SSH `~/.ssh/id_ed25519` (gerar: `ssh-keygen -t ed25519 -C 'gymsite'`)
- [ ] Repositório clonado localmente

---

## 1. Cloudflare Tunnel

### 1.1 Criar o tunnel (localmente, uma única vez)

```bash
# Instale o cloudflared (se ainda não tiver)
# https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

cloudflared tunnel create gymsite-api
# Anote o UUID exibido (ex: dbad2419-...)
```

### 1.2 Credenciais

O comando acima cria `~/.cloudflared/dbad2419-....json`. Copie para o projeto:

```bash
cp ~/.cloudflared/dbad2419-....json cloudflared/credentials.json
```

### 1.3 DNS

```bash
cloudflared tunnel route dns gymsite-api api.vectracargo.com.br
cloudflared tunnel route dns gymsite-api gymsite-api.vectracargo.com.br
```

### 1.4 Verifique `cloudflared/config.yml`

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
      http2Origin: false
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

> **IMPORTANTE:** `credentials.json` NUNCA deve ser commitado. Já está no `.gitignore`.

---

## 2. GCP VM — Bootstrap

### 2.1 Variáveis de ambiente (local)

```bash
export GCP_PROJECT_ID=<GCP_PROJECT_ID>
export GCP_ZONE=southamerica-east1-a
export GCP_VM_NAME=gymsite-api
export GCP_MACHINE_TYPE=e2-medium   # 2 vCPU, 4 GB
export GCP_DISK_SIZE=50GB
```

### 2.2 Criar VM

```bash
./scripts/bootstrap-gce.sh
```

O script faz:
- Importa sua chave SSH pública para o projeto
- Cria firewall rule `allow-ssh` (porta 22)
- Cria VM Ubuntu 22.04 com Docker pré-instalado
- Executa `scripts/setup-vm.sh` remotamente

Ao final, o script exibe o **IP externo** da VM.

---

## 3. Secrets na VM

### 3.1 Copiar arquivos

```bash
VM_IP=<IP_EXTERNO_DA_VM>

# 1. Env de produção
scp -i ~/.ssh/id_ed25519 .env.production ubuntu@$VM_IP:/opt/gymsite/.env.production

# 2. Cloudflare credentials
scp -i ~/.ssh/id_ed25519 -r cloudflared/ ubuntu@$VM_IP:/opt/gymsite/

# 3. CNO data (se houver)
scp -i ~/.ssh/id_ed25519 -r cno_data/ ubuntu@$VM_IP:/opt/gymsite/
```

> **Dica:** Use `frontend/.env.production` como referência para montar o backend `.env.production`. O template está em `.env.production.example`.

### 3.2 Ajustar permissões

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@$VM_IP \
  "sudo chown -R ubuntu:ubuntu /opt/gymsite && chmod 600 /opt/gymsite/cloudflared/credentials.json"
```

---

## 4. Deploy Inicial

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@$VM_IP

cd /opt/gymsite

# Login no GitHub Container Registry (opcional na primeira vez)
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USER --password-stdin

# Deploy
./scripts/deploy.sh latest
```

O script:
- Faz pull da imagem `ghcr.io/marce/gymsite_intelligence:latest`
- Executa rolling deploy com health check
- Faz rollback automático se o health falhar

Verifique os logs:

```bash
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml ps
```

---

## 5. GitHub Actions — Deploy Automático

Configure os seguintes **Repository Secrets** no GitHub (`Settings > Secrets and variables > Actions`):

| Secret | Descrição |
|--------|-----------|
| `GCP_SA_KEY` | JSON da service account GCP (opcional, se usar GCE deploy) |
| `GCP_VM_NAME` | Nome da VM (`gymsite-api`) |
| `GCP_PROJECT_ID` | `<GCP_PROJECT_ID>` |
| `GCP_ZONE` | `southamerica-east1-a` |
| `SSH_HOST` | IP externo da VM (para deploy VPS) |
| `SSH_USER` | `ubuntu` |
| `SSH_PRIVATE_KEY` | Conteúdo de `~/.ssh/id_ed25519` |
| `GITHUB_TOKEN` | Já existe automaticamente |

A partir daí, todo push na `main` ou tag `v*`:
1. Builda e testa a imagem
2. Publica no GHCR
3. Faz deploy automático na VM via SSH

---

## 6. Validação

### 6.1 Health check local (dentro da VM)

```bash
curl -s http://localhost:8000/health | jq
```

### 6.2 Health check via Cloudflare (público)

```bash
curl -s https://api.vectracargo.com.br/health | jq
```

Esperado:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### 6.3 Verificar canal de pesquisa

```bash
curl -s -X POST https://api.vectracargo.com.br/api/canais/status \
  -H "Content-Type: application/json" | jq
```

### 6.4 Métricas (restrito a rede interna)

```bash
# Na VM apenas
curl -s http://localhost:8000/api/metrics
```

---

## 7. Comandos Úteis

```bash
# Restart manual
docker compose -f docker-compose.prod.yml restart api

# Escalar para 2 réplicas (momentaneamente)
docker compose -f docker-compose.prod.yml up -d --scale api=2 api

# Ver logs em tempo real
docker compose -f docker-compose.prod.yml logs -f --tail=100 api

# Atualizar imagem forçadamente
docker compose -f docker-compose.prod.yml pull api && docker compose -f docker-compose.prod.yml up -d api

# Liberar espaço
docker system prune -af --filter "until=168h"
```

---

## 8. Troubleshooting

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `curl: (6) Could not resolve host` | DNS não propagou | Aguarde 1-5 min; verifique no dashboard Cloudflare |
| `502 Bad Gateway` | API não subiu ou saudável | `docker compose ps` e `docker logs gymsite-api` |
| `tunnel not found` | `credentials.json` errado ou faltando | Verifique UUID em `cloudflared/config.yml` e o arquivo JSON |
| Deploy travado em "health check" | Container crashando | Verificar `.env.production` (faltando `SUPABASE_URL`, `GOOGLE_API_KEY`, etc.) |
| Sem acesso SSH | Firewall ou chave | `gcloud compute firewall-rules list --filter="name=allow-ssh"` |
| Porta 8000 exposta na internet | Tags http-server/https-server na VM | Recriar VM sem essas tags (ou remover regras de firewall) |

---

## 9. Arquitetura de Rede

```
Usuário
   │ HTTPS
   ▼
Cloudflare Edge (TLS terminado)
   │ Cloudflare Tunnel
   ▼
VM GCP (porta 22 apenas)
   │ Docker network (172.28.0.0/16)
   ├─► cloudflared ──► api:8000 (FastAPI)
   ├─► redis:6379
   └─► nginx:80/443 (opcional, profile=nginx)
```

- A VM **não expõe** porta 80, 443 ou 8000 para a internet.
- Todo tráfego entra pelo Cloudflare Tunnel.
- O nginx existe como profile opcional para casos de proxy local direto (sem tunnel).
