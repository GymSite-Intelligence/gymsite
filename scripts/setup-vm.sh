#!/usr/bin/env bash
# =============================================================================
# GymSite Intelligence — VM Setup Script (roda DENTRO da VM)
# Instala dependências, configura Docker, cria estrutura de diretórios.
# =============================================================================
set -euo pipefail

APP_DIR="/opt/gymsite"
REPO_URL="${GITHUB_REPO:-https://github.com/Marcelo-Rosas/gymsite_intelligence.git}"

GRN='\033[0;32m'
NC='\033[0m'
log() { echo -e "${GRN}[vm-setup]${NC} $*"; }

log "Iniciando setup da VM..."

# ─── Docker já deve estar instalado pelo startup-script ─────────────────────
if ! command -v docker &>/dev/null; then
    log "Docker não encontrado. Em Hetzner: sudo bash scripts/hetzner/bootstrap.sh"
    log "Legado GCE: scripts/bootstrap-gce.sh"
    exit 1
fi

# ─── Criar diretório da app ─────────────────────────────────────────────────
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# ─── Clone do repo (se não existir) ─────────────────────────────────────────
if [[ ! -d ".git" ]]; then
    log "Clonando repositório..."
    git clone "$REPO_URL" .
else
    log "Repositório já existe. Pulando clone."
fi

# ─── Diretórios auxiliares ──────────────────────────────────────────────────
mkdir -p cno_data cloudflared nginx/ssl

# ─── Permissões ─────────────────────────────────────────────────────────────
chown -R "$(whoami):$(whoami)" "$APP_DIR"

# ─── Docker Compose plugin check ────────────────────────────────────────────
if ! docker compose version &>/dev/null; then
    log "Instalando docker-compose-plugin..."
    apt-get update && apt-get install -y docker-compose-plugin
fi

# ─── Smoke test ─────────────────────────────────────────────────────────────
log "Testando Docker..."
docker run --rm hello-world >/dev/null 2>&1 && log "Docker OK"

log ""
log "═══════════════════════════════════════════════════════════════"
log "Setup da VM concluído!"
log "Diretório: $APP_DIR"
log "═══════════════════════════════════════════════════════════════"
log ""
log "Próximos passos MANUAIS:"
log "1. Copie .env.production para $APP_DIR/.env.production"
log "2. Copie cloudflared/config.yml e credentials.json para $APP_DIR/cloudflared/"
log "3. Execute: cd $APP_DIR && ./scripts/deploy.sh"
