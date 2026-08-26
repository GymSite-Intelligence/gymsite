#!/usr/bin/env bash
# =============================================================================
# GymSite Intelligence — Production Deploy Script
# Uso: ./scripts/deploy.sh [tag]
#   tag: opcional (default: latest). Ex: ./scripts/deploy.sh v1.2.3
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.production"
TAG="${1:-latest}"
GHCR_IMAGE="${GHCR_IMAGE:-ghcr.io/marcelo-rosas/gymsite}"
HEALTH_RETRIES=12
HEALTH_INTERVAL=5

# ─── Colors ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m' # No Color

log()  { echo -e "${GRN}[deploy]${NC} $*"; }
warn() { echo -e "${YEL}[deploy]${NC} $*"; }
err()  { echo -e "${RED}[deploy]${NC} $*"; }

# ─── Pre-flight checks ──────────────────────────────────────────────────────
log "Pre-flight checks..."

if ! command -v docker &>/dev/null; then
    err "Docker não encontrado"; exit 1
fi

if ! docker compose version &>/dev/null && ! docker-compose version &>/dev/null; then
    err "docker compose não encontrado"; exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    err "Arquivo .env.production não encontrado em $ENV_FILE"
    err "Copie de .env.production.example e preencha os secrets"
    exit 1
fi

# Detect docker compose command
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# ─── GHCR Login ─────────────────────────────────────────────────────────────
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    log "Login no GHCR..."
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "${GITHUB_USER:-$USER}" --password-stdin
fi

# ─── Export tag override ────────────────────────────────────────────────────
export GHCR_IMAGE="${GHCR_IMAGE}:${TAG}"

cd "$PROJECT_DIR"

# Bind mount cno_data precisa ser gravável pelo user app (uid 1000) no container.
mkdir -p "$PROJECT_DIR/cno_data"
if [[ "$(stat -c '%u' "$PROJECT_DIR/cno_data")" != "1000" ]]; then
    log "Ajustando ownership cno_data → 1000:1000 (container non-root)..."
    chown 1000:1000 "$PROJECT_DIR/cno_data"
fi

# ─── Pull ───────────────────────────────────────────────────────────────────
log "Pulling image ${GHCR_IMAGE}..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" pull api

# ─── Deploy (rolling update) ────────────────────────────────────────────────
log "Deploying tag=${TAG}..."

# Capture pre-deploy container ID for rollback
OLD_CONTAINER=$($DOCKER_COMPOSE -f "$COMPOSE_FILE" ps -q api 2>/dev/null || true)

# Start new container alongside old (start-first strategy)
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d --no-deps --scale api=2 api

# ─── Health check ───────────────────────────────────────────────────────────
log "Aguardando health check (max $((HEALTH_RETRIES * HEALTH_INTERVAL))s)..."

HEALTH_OK=false
for ((i=1; i<=HEALTH_RETRIES; i++)); do
    NEW_CONTAINER=$($DOCKER_COMPOSE -f "$COMPOSE_FILE" ps -q api | tail -1)
    
    if docker exec "$NEW_CONTAINER" python -c \
        "import httpx; r=httpx.get('http://127.0.0.1:8000/health', timeout=5); assert r.status_code==200" 2>/dev/null; then
        HEALTH_OK=true
        log "Health check OK (tentativa $i)"
        break
    fi
    
    warn "Health check pendente (tentativa $i/$HEALTH_RETRIES)..."
    sleep "$HEALTH_INTERVAL"
done

if [[ "$HEALTH_OK" != true ]]; then
    err "Health check FALHOU — iniciando rollback"
    
    # Remove new container
    if [[ -n "${NEW_CONTAINER:-}" ]]; then
        docker stop "$NEW_CONTAINER" || true
        docker rm "$NEW_CONTAINER" || true
    fi
    
    # Ensure old container is running
    if [[ -n "${OLD_CONTAINER:-}" ]]; then
        docker start "$OLD_CONTAINER" || true
    fi
    
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d --no-deps --scale api=1 api
    err "Rollback concluído. Deploy abortado."
    exit 1
fi

# ─── Scale down to single replica ───────────────────────────────────────────
log "Removendo container antigo..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d --no-deps --scale api=1 api

# ─── Cleanup ────────────────────────────────────────────────────────────────
log "Limpando imagens antigas..."
docker system prune -af --filter "until=168h" || true

log "Deploy concluído com sucesso!"
log "Tag: ${TAG}"
log "Containers ativos:"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
