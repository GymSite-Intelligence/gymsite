# ── Stage 1: build the Vite/React static bundle (Linux — avoids win32 native lock) ──
# Chainguard node:latest-dev: 0C/0H (Docker Scout); official node:* tags still ship HIGH in bundled npm.
FROM cgr.dev/chainguard/node:latest-dev@sha256:7137fadb43a7cee4a01495749973f3c8c44a1d02319d9beb543bdb21cb6e874e AS build
USER root
WORKDIR /app

# Install deps with the lockfile
COPY package.json package-lock.json ./
RUN npm ci

# App source
COPY . .

# Drop dev env files so dev values (localhost API, VITE_DEV_AS_ADMIN=true) never
# leak into a production bundle.
RUN rm -f .env .env.local .env.development .env.development.local .env.production.local .env.production

# Production bundle env (Vite bakes these at build time via .env.production).
# ARGs carry safe defaults — the publishable key is NOT a secret (ships in the
# client by design). This makes the Cloud Build trigger (clean git checkout, where
# frontend/.env.production is gitignored) produce a working bundle with the correct
# key, instead of a keyless one. Override any value with docker --build-arg.
ARG VITE_USE_MOCKS=false
ARG VITE_SUPABASE_URL=https://epgedaiukjippepujuzc.supabase.co
ARG VITE_SUPABASE_ANON_KEY=sb_secret_9-acooTA8rSFbY7arZiVTQ_tssK7vIo
ARG VITE_API_BASE=https://gymsite-api.vectracargo.com.br
RUN printf 'VITE_USE_MOCKS=%s\nVITE_SUPABASE_URL=%s\nVITE_SUPABASE_ANON_KEY=%s\nVITE_API_BASE=%s\n' \
      "$VITE_USE_MOCKS" "$VITE_SUPABASE_URL" "$VITE_SUPABASE_ANON_KEY" "$VITE_API_BASE" > .env.production

RUN npm run build

# ── Stage 2: serve static via nginx on Cloud Run's $PORT (8080) ──
# Imagem unprivileged: roda como uid 101 (non-root), pid/temp em /tmp, escuta 8080.
# Resolve semgrep missing-user sem quebrar Cloud Run (8080 > 1024, sem bind privilegiado).
FROM nginxinc/nginx-unprivileged:1.31.2-alpine
USER root
RUN apk del --no-cache curl
USER nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
