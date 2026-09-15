---
name: deploy
description: "Deploy Hetzner VPS (API+worker) + Wrangler Pages (canônico P-000 / ADR-008)"
---

# /deploy

Seguir **à letra** o workflow:

`.agent/workflows/deploy.md`

API e worker rodam na Hetzner via Docker Compose + Cloudflare Tunnel. Frontend no Cloudflare Pages via Wrangler. Cloud Run está deprecado (ADR-008).

