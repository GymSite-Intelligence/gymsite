#!/usr/bin/env bash
# =============================================================================
# GymSite Intelligence — Setup Service Account GCP (gen-lang-client-0106729343)
# Roda UMA vez no terminal do usuário (precisa estar logado no gcloud)
# =============================================================================
set -euo pipefail

PROJECT_ID="gen-lang-client-0106729343"
SA_NAME="gymsite-pipeline"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="gymsite-pipeline-sa-key.json"

GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m'
log()  { echo -e "${GRN}[gcp-sa]${NC} $*"; }
warn() { echo -e "${YEL}[gcp-sa]${NC} $*"; }

log "Projeto: $PROJECT_ID"
log "Service Account: $SA_EMAIL"

# ─── 1. Criar Service Account (idempotente) ─────────────────────────────────
if gcloud iam service-accounts list --project="$PROJECT_ID" --format="value(email)" | grep -q "^${SA_EMAIL}$"; then
    warn "Service account $SA_EMAIL já existe. Pulando criação."
else
    log "Criando service account $SA_NAME..."
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="GymSite CI/CD Pipeline" \
        --project="$PROJECT_ID"
fi

# ─── 2. Atribuir Roles ──────────────────────────────────────────────────────
log "Atribuindo permissões..."

ROLES=(
    "roles/compute.instanceAdmin.v1"
    "roles/compute.osAdminLogin"
    "roles/iam.serviceAccountUser"
    "roles/logging.logWriter"
    "roles/monitoring.metricWriter"
)

for ROLE in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$ROLE" \
        --condition=None >/dev/null 2>&1 || true
done

# ─── 3. Gerar Chave JSON ────────────────────────────────────────────────────
log "Gerando chave JSON: $KEY_FILE"

if [[ -f "$KEY_FILE" ]]; then
    warn "Arquivo $KEY_FILE já existe. Renomeando para ${KEY_FILE}.bak"
    mv "$KEY_FILE" "${KEY_FILE}.bak"
fi

gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$SA_EMAIL" \
    --project="$PROJECT_ID"

log ""
log "═══════════════════════════════════════════════════════════════"
log "Service Account configurada com sucesso!"
log "───────────────────────────────────────────────────────────────"
log "Email:    $SA_EMAIL"
log "Key file: $(pwd)/$KEY_FILE"
log ""
log "PRÓXIMO PASSO — GitHub Secret:"
log "1. Acesse: https://github.com/Marcelo-Rosas/gymsite_intelligence/settings/secrets/actions"
log "2. Clique em 'New repository secret'"
log "3. Name:  GCP_SA_KEY"
log "4. Value: Cole TODO o conteúdo do arquivo $(pwd)/$KEY_FILE"
log ""
log "OUTROS SECRETS NECESSÁRIOS:"
log "   GCP_VM_NAME = gymsite-api"
log "   GCP_PROJECT_ID = $PROJECT_ID"
log "   GCP_ZONE = southamerica-east1-a"
log "═══════════════════════════════════════════════════════════════"
