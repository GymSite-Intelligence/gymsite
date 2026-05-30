#!/usr/bin/env bash
# =============================================================================
# GymSite Intelligence — Bootstrap GCE VM (Google Compute Engine)
# Cria VM no projeto GCP existente, instala Docker e prepara pra deploy.
# =============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0106729343}"
ZONE="${GCP_ZONE:-southamerica-east1-a}"
VM_NAME="${GCP_VM_NAME:-gymsite-api}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-e2-medium}"   # 2 vCPU, 4 GB — ajuste conforme carga
DISK_SIZE="${GCP_DISK_SIZE:-50GB}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519.pub}"

GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GRN}[gce]${NC} $*"; }
warn() { echo -e "${YEL}[gce]${NC} $*"; }

# ─── Pré-requisitos ─────────────────────────────────────────────────────────
log "Verificando gcloud..."
if ! command -v gcloud &>/dev/null; then
    echo "gcloud CLI não encontrado. Instale: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

log "Projeto: $PROJECT_ID | Zona: $ZONE | VM: $VM_NAME"
gcloud config set project "$PROJECT_ID" 2>/dev/null || true

# ─── Upload SSH key pro projeto ─────────────────────────────────────────────
if [[ -f "$SSH_KEY" ]]; then
    log "Importando chave SSH pública pro GCP..."
    gcloud compute project-info add-metadata \
        --metadata "ssh-keys=$(whoami):$(cat "$SSH_KEY")"
else
    warn "Chave SSH pública não encontrada em $SSH_KEY"
    warn "Gere com: ssh-keygen -t ed25519 -C 'gymsite' -f ~/.ssh/id_ed25519"
    exit 1
fi

# ─── Firewall: SSH (22) ─────────────────────────────────────────────────────
log "Configurando firewall rules..."
if ! gcloud compute firewall-rules list --filter="name=allow-ssh" --format="value(name)" | grep -q "allow-ssh"; then
    gcloud compute firewall-rules create allow-ssh \
        --allow tcp:22 \
        --source-ranges="0.0.0.0/0" \
        --target-tags=gymsite-api \
        --description="Allow SSH access"
fi

# ─── Criar VM ───────────────────────────────────────────────────────────────
EXISTS=$(gcloud compute instances list --filter="name=$VM_NAME" --format="value(name)" 2>/dev/null || true)

if [[ -n "$EXISTS" ]]; then
    warn "VM '$VM_NAME' já existe. Pulando criação."
else
    log "Criando VM $VM_NAME ($MACHINE_TYPE, $DISK_SIZE)..."
    gcloud compute instances create "$VM_NAME" \
        --zone="$ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --image-family=ubuntu-2204-lts \
        --image-project=ubuntu-os-cloud \
        --boot-disk-size="$DISK_SIZE" \
        --boot-disk-type=pd-ssd \
        --tags=gymsite-api \
        --metadata-from-file startup-script=<(cat <<'EOF'
#!/bin/bash
# Startup script — roda na primeira inicialização
set -e

export DEBIAN_FRONTEND=noninteractive

# Atualiza sistema
apt-get update && apt-get upgrade -y

# Instala Docker
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker ubuntu

# Instala utilitários
apt-get install -y git htop jq

# Cria diretório da aplicação
mkdir -p /opt/gymsite
chown ubuntu:ubuntu /opt/gymsite

# Log de conclusão
echo "Startup script concluído em $(date)" > /opt/startup-done.txt
EOF
)
fi

# ─── Aguardar VM ficar acessível ────────────────────────────────────────────
log "Aguardando VM ficar acessível via SSH..."
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

for i in {1..30}; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "${SSH_KEY%.pub}" "ubuntu@$EXTERNAL_IP" "echo ok" 2>/dev/null; then
        log "VM acessível em $EXTERNAL_IP"
        break
    fi
    echo -n "."
    sleep 5
done

# ─── Rodar setup remoto ─────────────────────────────────────────────────────
log "Rodando setup remoto na VM..."
scp -o StrictHostKeyChecking=no -i "${SSH_KEY%.pub}" \
    "$(dirname "$0")/setup-vm.sh" "ubuntu@$EXTERNAL_IP:/tmp/setup-vm.sh"

ssh -o StrictHostKeyChecking=no -i "${SSH_KEY%.pub}" "ubuntu@$EXTERNAL_IP" \
    "bash /tmp/setup-vm.sh"

# ─── Output ─────────────────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════════════"
log "VM criada e configurada!"
log "───────────────────────────────────────────────────────────────"
log "IP externo:     $EXTERNAL_IP"
log "SSH:            ssh -i ~/.ssh/id_ed25519 ubuntu@$EXTERNAL_IP"
log "Projeto GCP:    $PROJECT_ID"
log "Zona:           $ZONE"
log "───────────────────────────────────────────────────────────────"
log "Próximo passo:"
log "1. Copie .env.production pra VM:"
log "   scp -i ~/.ssh/id_ed25519 .env.production ubuntu@$EXTERNAL_IP:/opt/gymsite/.env.production"
log "2. Atualize GitHub Secret SSH_HOST=$EXTERNAL_IP"
log "3. Faça push na main → deploy automático"
log "═══════════════════════════════════════════════════════════════"
