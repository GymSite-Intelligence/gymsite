#!/usr/bin/env bash
# Deploy do backend GymSite (Cloud Run) com o git SHA CARIMBADO.
# Sem isso, prod não tem .git → /api/version mostra "unknown" e a detecção de stale
# fica cega em prod. Ver feedback memory restart-server-pós-código.
#
# Mecanismo primário: --update-env-vars GIT_SHA=<sha> (runtime, merge — NÃO apaga as
# outras env vars como --set-env-vars faria). Camada extra: arquivo VERSION bakeado na
# imagem (ARG/ENV no Dockerfile) — removido localmente no fim pra não mascarar o SHA
# do git no servidor de dev.
set -euo pipefail
cd "$(dirname "$0")/.."

SHA="$(git rev-parse --short HEAD)"
git diff --quiet || SHA="${SHA}-dirty"   # avisa se deployando árvore suja
echo "$SHA" > VERSION
trap 'rm -f VERSION' EXIT                 # VERSION é só pro build — não fica no dev

echo "[deploy] gymsite-api @ GIT_SHA=${SHA}"
gcloud run deploy gymsite-api \
  --source . \
  --region us-central1 \
  --no-use-buildpacks \
  --update-env-vars "GIT_SHA=${SHA}"

echo "[deploy] ok — confira a versão em prod:"
echo "  curl -s https://gymsite-api.vectracargo.com.br/api/version"
