# ── Stage 1: build the Vite/React static bundle (Linux — avoids win32 native lock) ──
FROM node:22-alpine AS build
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
ARG VITE_SUPABASE_ANON_KEY=sb_publishable_fj4Ioi3YX8gI-h3lrcb45w_FZa9UzhD
ARG VITE_API_BASE=https://gymsite-api.vectracargo.com.br
RUN printf 'VITE_USE_MOCKS=%s\nVITE_SUPABASE_URL=%s\nVITE_SUPABASE_ANON_KEY=%s\nVITE_API_BASE=%s\n' \
      "$VITE_USE_MOCKS" "$VITE_SUPABASE_URL" "$VITE_SUPABASE_ANON_KEY" "$VITE_API_BASE" > .env.production

RUN npm run build

# ── Stage 2: serve static via nginx on Cloud Run's $PORT (8080) ──
# Imagem unprivileged: roda como uid 101 (non-root), pid/temp em /tmp, escuta 8080.
# Resolve semgrep missing-user sem quebrar Cloud Run (8080 > 1024, sem bind privilegiado).
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
