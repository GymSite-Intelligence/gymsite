#!/usr/bin/env bash
# =============================================================================
# GymSite Intelligence — Bootstrap + Deploy Completo na GCP
# Faz TUDO: cria VM, copia secrets, deploya a API.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ─── Config (sobrescreva via env vars se necessário) ────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0106729343}"
ZONE="${GCP_ZONE:-southamerica-east1-a}"
VM_NAME="${GCP_VM_NAME:-gymsite-api}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-e2-medium}"
DISK_SIZE="${GCP_DISK_SIZE:-50GB}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
SSH_KEY_PRIV="${SSH_KEY%.pub}"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/.env.production}"

GRN='\033[0;32m'
YEL='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GRN}[bootstrap]${NC} $*"; }
warn() { echo -e "${YEL}[bootstrap]${NC} $*"; }
err()  { echo -e "${RED}[bootstrap]${NC} $*"; }

# ─── Pré-requisitos ─────────────────────────────────────────────────────────
log "Verificando pré-requisitos..."

if ! command -v gcloud &>/dev/null; then
    err "gcloud CLI não encontrado. Instale: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v docker &>/dev/null; then
    err "Docker não encontrado."
    exit 1
fi

if [[ ! -f "$SSH_KEY" ]]; then
    err "Chave SSH pública não encontrada: $SSH_KEY"
    err "Gere com: ssh-keygen -t ed25519 -C 'gymsite' -f ~/.ssh/id_ed25519"
    exit 1
fi

if [[ ! -f "$SSH_KEY_PRIV" ]]; then
    err "Chave SSH privada não encontrada: $SSH_KEY_PRIV"
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    err "Arquivo de env não encontrado: $ENV_FILE"
    err "Copie de .env.production.example e preencha os secrets."
    exit 1
fi

if [[ ! -f "$PROJECT_DIR/cloudflared/credentials.json" ]]; then
    err "cloudflared/credentials.json não encontrado."
    err "Crie o tunnel: cloudflared tunnel create gymsite-api"
    exit 1
fi

log "Projeto: $PROJECT_ID | Zona: $ZONE | VM: $VM_NAME"
gcloud config set project "$PROJECT_ID" 2>/dev/null || true

# ─── 1. Criar VM (via bootstrap-gce.sh) ─────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════════════"
log "ETAPA 1/4 — Criando VM no GCP..."
log "═══════════════════════════════════════════════════════════════"

GCP_PROJECT_ID="$PROJECT_ID" \
GCP_ZONE="$ZONE" \
GCP_VM_NAME="$VM_NAME" \
GCP_MACHINE_TYPE="$MACHINE_TYPE" \
GCP_DISK_SIZE="$DISK_SIZE" \
SSH_KEY="$SSH_KEY" \
    bash "$SCRIPT_DIR/bootstrap-gce.sh"

# ─── Capturar IP ────────────────────────────────────────────────────────────
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

log ""
log "VM IP: $EXTERNAL_IP"

# ─── 2. Copiar secrets ──────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════════════"
log "ETAPA 2/4 — Copiando secrets para a VM..."
log "═══════════════════════════════════════════════════════════════"

log "Copiando .env.production..."
scp -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" \
    "$ENV_FILE" "ubuntu@$EXTERNAL_IP:/opt/gymsite/.env.production"

log "Copiando cloudflared/config.yml..."
scp -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" \
    "$PROJECT_DIR/cloudflared/config.yml" "ubuntu@$EXTERNAL_IP:/opt/gymsite/cloudflared/config.yml"

log "Copiando cloudflared/credentials.json..."
scp -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" \
    "$PROJECT_DIR/cloudflared/credentials.json" "ubuntu@$EXTERNAL_IP:/opt/gymsite/cloudflared/credentials.json"

log "Copiando docker-compose.prod.yml..."
scp -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" \
    "$PROJECT_DIR/docker-compose.prod.yml" "ubuntu@$EXTERNAL_IP:/opt/gymsite/docker-compose.prod.yml"

log "Copiando nginx/..."
scp -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" -r \
    "$PROJECT_DIR/nginx" "ubuntu@$EXTERNAL_IP:/opt/gymsite/"

log "Copiando scripts/deploy.sh..."
scp -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" \
    "$SCRIPT_DIR/deploy.sh" "ubuntu@$EXTERNAL_IP:/opt/gymsite/scripts/deploy.sh"

# ─── 3. Ajustar permissões ──────────────────────────────────────────────────
log ""
log "Ajustando permissões..."
ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" "ubuntu@$EXTERNAL_IP" \
    "chmod 600 /opt/gymsite/cloudflared/credentials.json && chmod +x /opt/gymsite/scripts/deploy.sh"

# ─── 4. Deploy inicial ──────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════════════"
log "ETAPA 3/4 — Deploy inicial..."
log "═══════════════════════════════════════════════════════════════"

ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" "ubuntu@$EXTERNAL_IP" \
    "cd /opt/gymsite && bash scripts/deploy.sh latest"

# ─── 5. Health check ────────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════════════"
log "ETAPA 4/4 — Validando API..."
log "═══════════════════════════════════════════════════════════════"

sleep 5

if ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_PRIV" "ubuntu@$EXTERNAL_IP" \
    "curl -sf http://localhost:8000/health >/dev/null 2>&1" ; then
    log "Health check: OK"
else
    warn "Health check ainda pendente. Aguarde mais alguns segundos e verifique manualmente."
fi

# ─── 6. Atualizar GitHub Secret (opcional, se gh CLI disponível) ────────────
if command -v gh &>/dev/null; then
    log ""
    log "Atualizando GitHub Secret SSH_HOST..."
    echo "$EXTERNAL_IP" | gh secret set SSH_HOST --repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)" 2>/dev/null || warn "Não foi possível atualizar secret via gh CLI. Atualize manualmente."
else
    warn "gh CLI não encontrado. Atualize o GitHub Secret SSH_HOST manualmente."
fi

# ─── Output final ───────────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════════════"
log "BOOTSTRAP + DEPLOY CONCLUÍDO!"
log "═══════════════════════════════════════════════════════════════"
log ""
log "IP externo:     $EXTERNAL_IP"
log "SSH:            ssh -i $SSH_KEY_PRIV ubuntu@$EXTERNAL_IP"
log "Health:         curl http://$EXTERNAL_IP:8000/health  (ou via Cloudflare Tunnel)"
log ""
log "PRÓXIMOS PASSOS:"
log "1. Verifique o tunnel no dashboard Cloudflare: https://one.dash.cloudflare.com/"
log "2. Teste o domínio: curl -s https://api.vectracargo.com.br/health"
log "3. GitHub Actions deploy automático já configurado (push na main)"
log ""
log "═══════════════════════════════════════════════════════════════"
