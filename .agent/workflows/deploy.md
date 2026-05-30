---
description: Deploy backend (Docker/Cloudflared) and frontend (Vite build) to production. Includes health checks and rollback procedure.
---

# Workflow: /deploy

Deploy the entire application stack.

## Steps

1. **Pre-deploy checks** // turbo
   ```bash
   pyrefly check . && echo "Python OK"
   cd frontend && npm run lint && echo "Frontend OK"
   ```

2. **Run database migrations**
   ```bash
   psql $DATABASE_URL -f db/migrations/*.sql
   ```

3. **Build and deploy backend**
   ```bash
   docker build -t gymsite-api:latest .
   docker stop gymsite-api-old || true
   docker run -d --name gymsite-api -p 8000:8000 --env-file .env gymsite-api:latest
   ```

4. **Health check**
   ```bash
   curl -s http://localhost:8000/api/health | jq .
   ```

5. **Build and deploy frontend**
   ```bash
   cd frontend && npm run build
   # Deploy dist/ to Vercel/Netlify
   ```

6. **Verify Cloudflared tunnel**
   ```bash
   cloudflared tunnel info <tunnel-name>
   ```

## Rollback

If health check fails:
```bash
docker stop gymsite-api
docker rename gymsite-api-old gymsite-api
docker start gymsite-api
```
