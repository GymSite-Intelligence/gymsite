#!/usr/bin/env bash
# =============================================================================
# GymSite Intelligence — Setup Google Maps API no novo projeto GCP
# Ativa APIs e configura restricoes da chave. Billing precisa ser habilitado
# manualmente no console primeiro: https://console.cloud.google.com/billing
# =============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0106729343}"
KEY_NAME="gymsite-maps-key"

GRN='\033[0;32m'
YEL='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GRN}[maps-setup]${NC} $*"; }
warn() { echo -e "${YEL}[maps-setup]${NC} $*"; }
err()  { echo -e "${RED}[maps-setup]${NC} $*"; }

log "Projeto: $PROJECT_ID"
gcloud config set project "$PROJECT_ID" 2>/dev/null || true

# ─── 1. Verificar billing ───────────────────────────────────────────────────
log ""
log "=== 1. Verificando Billing ==="
BILLING=$(gcloud billing projects describe "$PROJECT_ID" --format="value(billingEnabled)" 2>/dev/null || echo "false")

if [[ "$BILLING" != "True" ]]; then
    err "BILLING NAO HABILITADO no projeto $PROJECT_ID"
    err ""
    err "SIGA ESTES PASSOS MANUAIS:"
    err "1. Acesse: https://console.cloud.google.com/billing/enable?project=$PROJECT_ID"
    err "2. Clique em 'Link a billing account' (ou crie uma nova)"
    err "3. Aceite os termos e adicione um cartao de credito"
    err "4. Aguarde 2-3 minutos"
    err "5. Rode este script novamente"
    err ""
    exit 1
fi

log "Billing: ✅ ATIVO"

# ─── 2. Ativar APIs ─────────────────────────────────────────────────────────
log ""
log "=== 2. Ativando APIs do Google Maps ==="

APIS=(
    "geocoding-backend.googleapis.com"
    "places.googleapis.com"
    "maps-backend.googleapis.com"
    "static-maps-backend.googleapis.com"
    "directions-backend.googleapis.com"
    "distance-matrix-backend.googleapis.com"
)

for API in "${APIS[@]}"; do
    log "Ativando $API..."
    gcloud services enable "$API" --project="$PROJECT_ID" || warn "Falha ao ativar $API (pode ja estar ativa)"
done

# ─── 3. Criar ou listar chave de API ────────────────────────────────────────
log ""
log "=== 3. API Keys ==="

EXISTING_KEYS=$(gcloud services api-keys list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null || true)

if [[ -n "$EXISTING_KEYS" ]]; then
    log "Chaves existentes:"
    gcloud services api-keys list --project="$PROJECT_ID" --format="table(displayName, name, createTime)" 2>/dev/null || true
else
    warn "Nenhuma chave de API encontrada."
fi

log ""
log "Para criar uma nova chave via console:"
log "  https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
log ""
log "Recomendado: restrinja a chave para estas APIs:"
log "  - Geocoding API"
log "  - Places API (New)"
log "  - Maps JavaScript API (se usar no frontend)"
log "  - Distance Matrix API"
log ""
log "Copie a chave para o campo GOOGLE_MAPS_API_KEY no .env.production"

# ─── 4. Verificar quotas ────────────────────────────────────────────────────
log ""
log "=== 4. Quotas atuais ==="
gcloud services quota list --service=places.googleapis.com --project="$PROJECT_ID" --format="table(metric,limit)" 2>/dev/null | head -5 || warn "Nao foi possivel listar quotas"

# ─── Output ─────────────────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════════════"
log "SETUP MAPS CONCLUIDO (APIs ativas)"
log "═══════════════════════════════════════════════════════════════"
log ""
log "PROXIMOS PASSOS MANUAIS (se ainda nao fez):"
log "1. Crie/obtenha a API Key no console GCP"
log "2. Adicione GOOGLE_MAPS_API_KEY=<sua-chave> no .env.production"
log "3. Reinicie a API: docker compose -f docker-compose.yml restart api"
log "4. Teste: curl https://api.vectracargo.com.br/health/maps"
log ""
log "URLs UTEIS:"
log "  Credenciais: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
log "  Billing:     https://console.cloud.google.com/billing?project=$PROJECT_ID"
log "  Quotas:      https://console.cloud.google.com/apis/api/places.googleapis.com/quotas?project=$PROJECT_ID"
log "═══════════════════════════════════════════════════════════════"
