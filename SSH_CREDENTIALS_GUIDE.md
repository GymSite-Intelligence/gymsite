# SSH Credentials & Deployment Guide — GymSite Intelligence

## 📍 Current Infrastructure Status

### ✅ **Local Development**
- **Status:** Running (localhost:8000)
- **Exposure:** Cloudflare Tunnel → `gymsite-api.vectracargo.com.br`
- **Database:** Local Docker Compose + Supabase Cloud
- **Kubernetes:** Docker Desktop (local)

### ❌ **VPS SSH Attempts**
- `64.181.167.248` — **OFFLINE** (Connection timeout)
- `136.248.92.230` — **OFFLINE** (Not tested, likely same)
- `147.15.57.98` — **OFFLINE** (Not tested, likely same)

---

## 🔑 SSH Credentials Found

### **Private Keys Available**
```
C:\Users\marce\.ssh\id_ed25519           ← Default (ED25519, no passphrase)
C:\Users\marce\.ssh\oracle_paperclip     ← Oracle Cloud (RSA)
```

### **SSH Hosts in known_hosts**
```
64.181.167.248    (ed25519)
136.248.92.230    (ed25519)
147.15.57.98      (ed25519 + rsa)
```

**Problem:** All 3 IPs are **offline** (port 22 not responding). These may be:
- Stopped instances
- Deleted / deprovisioned
- Behind firewall/NAT blocking SSH

---

## 🎯 For CI/CD Deployment (GitHub Actions)

Since your VPS is offline, here are the **3 deployment options**:

### **Option 1: Cloud Run (Google Cloud) — RECOMMENDED**
You already have GCP credentials:
```
Project: gen-lang-client-0106729343
Service Account: gymsite-pipeline@gen-lang-client-0106729343.iam.gserviceaccount.com
```

**Setup:**
```bash
gcloud run deploy gymsite-api \
  --image gcr.io/gen-lang-client-0106729343/gymsite-api:latest \
  --region southamerica-east1 \
  --memory 2G --cpu 2 \
  --env-vars-file .env.prod
```

**GitHub Actions Secret:**
```yaml
GCP_SA_KEY = <contents of C:\Users\marce\.gcp\gymsite-sa.json>
```

### **Option 2: Spin Up New VPS & SSH Deploy**
If you want to bring VPS back online:

1. **Create EC2 / DigitalOcean / Hetzner instance**
2. **Use existing SSH key for auth:**
   ```bash
   # Generate from your existing keys
   ssh-copy-id -i C:\Users\marce\.ssh\id_ed25519 ubuntu@NEW_VPS_IP
   ```

3. **Create GitHub Secret:**
   ```yaml
   SSH_HOST = NEW_VPS_IP
   SSH_USER = ubuntu (or root)
   SSH_PRIVATE_KEY = <contents of C:\Users\marce\.ssh\id_ed25519>
   ```

### **Option 3: Keep Cloudflare Tunnel (Current Setup)**
Your app already runs via Tunnel on localhost:8000:
```yaml
# .cloudflared/config.yml
tunnel: b6330747-06af-48bb-a429-12dea92c4dd7
ingress:
  - hostname: gymsite-api.vectracargo.com.br
    service: http://localhost:8000
```

**No SSH needed** — just keep your machine online and deploy locally:
```bash
git pull origin main
docker-compose up --build -d
```

---

## 📋 SSH Credentials Reference

### **For SSH CLI (Local Testing)**
```bash
# Using default key
ssh -i "C:\Users\marce\.ssh\id_ed25519" ubuntu@<NEW_VPS_IP>

# Using Oracle key
ssh -i "C:\Users\marce\.ssh\oracle_paperclip" opc@147.15.57.98
```

### **For GitHub Actions Secrets**
Create these in your repo:
```
Repository → Settings → Secrets and variables → Actions → New repository secret

SSH_HOST = <IP of your VPS>
SSH_USER = ubuntu (or your username)
SSH_PRIVATE_KEY = (copy full contents of id_ed25519 file — BEGIN to END)
```

### **GitHub Actions Deployment Workflow Example**
```yaml
name: Deploy to VPS

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /home/app/gymsite-api
            git pull origin main
            docker-compose down
            docker-compose up --build -d
            docker-compose exec api python -c "import api; print('✓ API started')"
```

---

## 🚀 Quick Actions

### **If you want to bring VPS back online:**
1. Check your cloud provider (AWS EC2, DigitalOcean, Hetzner, Oracle)
2. Start the instance (might just be stopped)
3. Get the new public IP
4. Update GitHub Secrets with new IP

### **If you prefer to stay with Cloudflare Tunnel:**
✅ No action needed — already working on `gymsite-api.vectracargo.com.br`

### **If you want to deploy to Google Cloud Run:**
```bash
# Install gcloud CLI
# Then:
gcloud auth activate-service-account --key-file=~/.gcp/gymsite-sa.json
gcloud config set project gen-lang-client-0106729343
gcloud run deploy gymsite-api \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated
```

---

## 📝 Summary

| Item | Status | Value |
|------|--------|-------|
| **SSH Keys** | ✅ Found | `id_ed25519`, `oracle_paperclip` |
| **VPS SSH** | ❌ Offline | 64.181.167.248, 136.248.92.230, 147.15.57.98 |
| **GCP Project** | ✅ Active | `gen-lang-client-0106729343` |
| **GitHub Repo** | ✅ Found | `github.com/Marcelo-Rosas/gymsite` |
| **Current Deployment** | ✅ Running | Cloudflare Tunnel (local machine) |
| **Recommended Next** | 🎯 | Migrate to Google Cloud Run OR spin up new VPS |

---

## ❓ Questions?

1. **Where is your primary deployment?** (GCP? VPS? Local?)
2. **Can you access the old VPS provider** (AWS/DigitalOcean/etc)?
3. **Do you want to bring the VPS back online or switch to Cloud Run?**
