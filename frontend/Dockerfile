# ── Stage 1: build the Vite/React static bundle (Linux — avoids win32 native lock) ──
FROM node:22-alpine AS build
WORKDIR /app

# Install deps with the lockfile
COPY package.json package-lock.json ./
RUN npm ci

# App source
COPY . .

# Drop dev env files so dev values (localhost API, VITE_DEV_AS_ADMIN=true) never
# leak into a production bundle. Vite loads .env.production (copied above) in
# production mode — it already targets gymsite-api.vectracargo.com.br and omits
# VITE_DEV_AS_ADMIN (which would grant admin to every visitor).
RUN rm -f .env .env.local .env.development .env.development.local .env.production.local

RUN npm run build

# ── Stage 2: serve static via nginx on Cloud Run's $PORT (8080) ──
# Imagem unprivileged: roda como uid 101 (non-root), pid/temp em /tmp, escuta 8080.
# Resolve semgrep missing-user sem quebrar Cloud Run (8080 > 1024, sem bind privilegiado).
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
