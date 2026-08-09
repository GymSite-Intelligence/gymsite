#!/usr/bin/env bash
# =============================================================================
# GymSite — Bootstrap Oracle Always Free Ampere (roda DENTRO da VM, Ubuntu)
# Instala Docker + Compose e prepara /opt/gymsite. Ver README.md nesta pasta.
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/gymsite}"
REPO_URL="${GITHUB_REPO:-https://github.com/Marcelo-Rosas/gymsite_intelligence.git}"

GRN='\033[0;32m'
YEL='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GRN}[oracle]${NC} $*"; }
warn() { echo -e "${YEL}[oracle]${NC} $*"; }
err()  { echo -e "${RED}[oracle]${NC} $*"; }

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Rode como root: sudo bash scripts/oracle/bootstrap.sh"
  exit 1
fi

ARCH="$(uname -m)"
log "Arch host: $ARCH"
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
  warn "Esperado Ampere aarch64. Em x86 micro (1GB) o pipeline NÃO cabe."
fi

log "Atualizando apt..."
apt-get update -y
apt-get install -y ca-certificates curl git ufw fail2ban

if ! command -v docker &>/dev/null; then
  log "Instalando Docker Engine..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  log "Docker já instalado: $(docker --version)"
fi

docker compose version >/dev/null

log "UFW: allow OpenSSH, deny resto..."
ufw allow OpenSSH
ufw --force enable || true

mkdir -p "$APP_DIR"
cd "$APP_DIR"
if [[ ! -d .git ]]; then
  log "Clonando $REPO_URL → $APP_DIR"
  git clone "$REPO_URL" .
else
  log "Repo já existe em $APP_DIR — pulando clone"
fi
mkdir -p cno_data cloudflared

log "Smoke Docker..."
docker run --rm hello-world >/dev/null

log ""
log "═══════════════════════════════════════════════════════════════"
log "Bootstrap Oracle OK — $APP_DIR (arch=$ARCH)"
log "═══════════════════════════════════════════════════════════════"
log "Próximos (manuais — secrets NÃO estão no git):"
log "1. Copiar .env.production  → $APP_DIR/.env.production"
log "   (REDIS_URL=redis://redis:6379/0)"
log "2. Copiar credentials.json → $APP_DIR/cloudflared/credentials.json"
log "3. cd $APP_DIR && docker compose -f docker-compose.prod.yml up -d"
log "   Se GHCR sem arm64: docker compose -f docker-compose.prod.yml up -d --build"
log "4. Health interno via compose exec api → http://127.0.0.1:8000/health"
log "5. Rota DNS staging: api-hetzner.getgymsite.com.br"
log "6. Smoke: https://api-hetzner.getgymsite.com.br/health"
warn "NÃO cutover DNS de produção até staging verde."
warn "NÃO usar shape E2.1.Micro (1GB)."
