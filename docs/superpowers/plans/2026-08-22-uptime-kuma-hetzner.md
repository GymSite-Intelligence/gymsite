# Uptime Kuma Hetzner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Monitor externo de `/health` (staging + prod) via Uptime Kuma atrás do Cloudflare Tunnel, sem porta pública, sem mudar `api.py`/`deploy.sh` app logic.

**Architecture:** Serviço `uptime-kuma` na rede Docker `gymsite`; `cloudflared` ingress `status.getgymsite.com.br` → `http://uptime-kuma:3001`; DNS route no túnel existente.

**Tech Stack:** Docker Compose, Cloudflare Tunnel, louislam/uptime-kuma:1

**Spec:** [docs/superpowers/specs/2026-08-22-uptime-kuma-hetzner-design.md](../specs/2026-08-22-uptime-kuma-hetzner-design.md)

---

## File map

| File | Responsibility |
|------|----------------|
| `docker-compose.prod.yml` | Serviço + volume `uptime-kuma` |
| `cloudflared/config.yml` | Ingress hostname status |
| `scripts/hetzner/README.md` | Runbook curto (DNS + UI checks) |

---

### Task 1: Compose — serviço Uptime Kuma

**Files:**
- Modify: `docker-compose.prod.yml`

**Steps:**

1. Adicionar serviço `uptime-kuma` (image `louislam/uptime-kuma:1`, volume `uptime-kuma-data:/app/data`, `restart: unless-stopped`, **sem** `ports`).
2. Adicionar volume nomeado `uptime-kuma-data` ao bloco `volumes`.
3. Commit: `feat(ops): add uptime-kuma service to prod compose`

---

### Task 2: Tunnel — ingress status

**Files:**
- Modify: `cloudflared/config.yml`

**Steps:**

1. Inserir bloco `hostname: status.getgymsite.com.br` / `service: http://uptime-kuma:3001` **antes** do catch-all `- service: http_status:404`.
2. Manter `originRequest` no mesmo estilo dos hosts da API (`http2Origin: false`, `noTLSVerify: true`).
3. Commit: `feat(ops): tunnel ingress for status.getgymsite.com.br`

---

### Task 3: Docs runbook Hetzner

**Files:**
- Modify: `scripts/hetzner/README.md`

**Steps:**

1. Seção “Uptime Kuma”: DNS `tunnel route dns … status.getgymsite.com.br`, bring-up `docker compose -f docker-compose.prod.yml up -d uptime-kuma cloudflared`, checks staging/prod com keyword `"status":"ok"`.
2. Commit: `docs(ops): uptime-kuma status hostname runbook`

---

### Task 4: Deploy na VPS (manual / SSH)

**Steps:**

1. `ssh` na VPS → `cd /opt/gymsite` → `git pull` (branch com Tasks 1–3).
2. `docker compose -f docker-compose.prod.yml up -d uptime-kuma`
3. `docker compose -f docker-compose.prod.yml up -d cloudflared` (reload config) **ou** recreate cloudflared.
4. DNS (uma vez):  
   `cloudflared tunnel route dns 12675577-d94b-4a19-b1df-a86713dbaf80 status.getgymsite.com.br`  
   (rodar onde a CLI cloudflared está autenticada — painel CF Zero Trust Tunnels também serve).
5. Abrir `https://status.getgymsite.com.br` → criar senha admin forte.
6. Criar 2 monitors (60s, keyword `"status":"ok"`):
   - `https://api-hetzner.getgymsite.com.br/health`
   - `https://api.getgymsite.com.br/health`
7. Verificar aceite da spec (ps Up, HTTPS login, sem :3001 no host, monitors verdes).

**Done when:** usuário responde `KUMA NO AR`.

---

### Task 5 (opcional, depois): Cloudflare Access + Discord

Só se Marcelo pedir. Não bloqueia Task 4.

- Zero Trust Application em `status.getgymsite.com.br`.
- Notification Discord no Kuma (webhook).

---

## Test plan

| Check | Como |
|-------|------|
| Container Up | `docker compose -f docker-compose.prod.yml ps uptime-kuma` |
| Sem porta host | `docker port uptime-kuma` vazio / sem 3001 |
| HTTPS | browser `https://status.getgymsite.com.br` |
| Health keyword | monitors mostram Up após 2–3 min |
| Regressão API | `Invoke-RestMethod https://api.getgymsite.com.br/health` ainda `ok` |
