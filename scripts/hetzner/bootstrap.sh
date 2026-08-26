#!/usr/bin/env bash
# =============================================================================
# GymSite — Bootstrap Hetzner VPS (roda DENTRO da VM, Ubuntu 24.04)
# Instala Docker Engine + Compose plugin e prepara /opt/gymsite.
# Não cria a VPS (isso é no painel Hetzner). Ver README.md nesta pasta.
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/gymsite}"
REPO_URL="${GITHUB_REPO:-https://github.com/Marcelo-Rosas/gymsite_intelligence.git}"

GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m'
log()  { echo -e "${GRN}[hetzner]${NC} $*"; }
warn() { echo -e "${YEL}[hetzner]${NC} $*"; }

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Rode como root: sudo bash scripts/hetzner/bootstrap.sh"
  exit 1
fi

log "Atualizando apt..."
apt-get update -y
apt-get install -y ca-certificates curl git ufw fail2ban

# ─── Docker Engine (repo oficial) ───────────────────────────────────────────
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

# ─── Firewall: só SSH (túnel Cloudflare = sem 80/443) ───────────────────────
log "UFW: allow OpenSSH, deny resto..."
ufw allow OpenSSH
ufw --force enable || true

# ─── App dir + clone ────────────────────────────────────────────────────────
mkdir -p "$APP_DIR"
cd "$APP_DIR"
if [[ ! -d .git ]]; then
  log "Clonando $REPO_URL → $APP_DIR"
  git clone "$REPO_URL" .
else
  log "Repo já existe em $APP_DIR — pulando clone"
fi
mkdir -p cno_data cloudflared
chown 1000:1000 cno_data

log "Smoke Docker..."
docker run --rm hello-world >/dev/null

log ""
log "═══════════════════════════════════════════════════════════════"
log "Bootstrap Hetzner OK — $APP_DIR"
log "═══════════════════════════════════════════════════════════════"
log "Próximos (manuais — secrets NÃO estão no git):"
log "1. Copiar .env.production  → $APP_DIR/.env.production"
log "   (REDIS_URL=redis://redis:6379/0)"
log "2. Copiar credentials.json → $APP_DIR/cloudflared/credentials.json"
log "3. cd $APP_DIR && docker compose -f docker-compose.prod.yml up -d"
log "4. Health interno: docker compose -f docker-compose.prod.yml exec api \\"
log "     python -c \"import httpx; print(httpx.get('http://127.0.0.1:8000/health').text)\""
log "5. Rota DNS staging: cloudflared tunnel route dns <ID> api-hetzner.getgymsite.com.br"
log "6. Smoke: https://api-hetzner.getgymsite.com.br/health"
warn "NÃO cutover DNS de produção até staging verde."
