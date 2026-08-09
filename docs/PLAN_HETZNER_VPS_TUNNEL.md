# Plano canônico — Hetzner VPS + Cloudflare Tunnel

> **Decisão de produto (2026-08-05):** substituir o **hospedeiro** Cloud Run (GCP) por VPS Hetzner + Cloudflare Tunnel, para a API e o worker do pipeline **não dependerem mais de faturamento Google Cloud**.
>
> **Gatilho:** incidente 503 com `billingEnabled: false` — ver [RUNBOOK_GCLOUD_503_BILLING.md](RUNBOOK_GCLOUD_503_BILLING.md).
>
> **Não é migração de dados.** Supabase, Redis externo (se houver), SearchAPI e front Cloudflare Pages **permanecem**.
>
> **Relacionados:** [CLOUDFLARED_CORS_SETUP.md](CLOUDFLARED_CORS_SETUP.md) · [DEPLOY_GCP_CLOUDFLARE.md](DEPLOY_GCP_CLOUDFLARE.md) (legado GCE — mesmo padrão de túnel) · skill `gymsite-devops`.
>
> **Free tier (teste sem pagar VPS):** Oracle Always Free Ampere — [`scripts/oracle/README.md`](../scripts/oracle/README.md). Mesmo compose + túnel; shape **A1.Flex**, nunca micro 1 GB.

---

## 1. O que muda / o que não muda

| Camada | Hoje | Depois |
|---|---|---|
| API FastAPI | Cloud Run `gymsite-api` | Container na Hetzner (`api`) |
| Worker pipeline | Cloud Run `gymsite-worker` | Container na mesma VPS (`worker`, `RUN_QUEUE_WORKER=1`) |
| Exposição pública | URL `*.run.app` / domínio via CF | **Só** Cloudflare Tunnel (sem porta 80/443 aberta) |
| Front | CF Pages | Igual |
| Banco | Supabase | Igual |
| Fila | Redis | Preferir Redis **na VPS** (compose) — mais barato e sem 2º billing |
| PDF WeasyPrint | Docker Cloud Run | Mesmo `Dockerfile` (pango/cairo já no image) |
| LLM pipeline | NVIDIA / Gemini API key | Igual (`.env`: `PIPELINE_LLM_PROVIDER=nvidia`) |
| BigQuery / Maps | Contas GCP | **Continuam no Google** (API keys / SA) — mas a **API sobe sem Cloud Run** |

**Regra de ouro:** “sair do billing cloud” = sair do **Cloud Run como hospedeiro**. Não significa apagar Google Maps nem BigQuery no dia 1.

---

## 2. Arquitetura alvo

```
Browser / app (getgymsite, gymsite.vectracargo…)
        │ HTTPS
        ▼
Cloudflare Edge  ──CNAME──►  Cloudflare Tunnel (cloudflared)
                                    │
                                    ▼  (rede Docker interna, sem IP público HTTP)
                         ┌──────────────────────────────┐
                         │  Hetzner VPS  /opt/gymsite   │
                         │  ├─ api:8000   (uvicorn)     │
                         │  ├─ worker     (mesma image) │
                         │  ├─ redis:6379               │
                         │  └─ cloudflared              │
                         └──────────────────────────────┘
                                    │
                    Supabase · SearchAPI · Gemini/NVIDIA · Maps (egress)
```

Hostnames a servir no túnel (mínimo):

| Hostname | Uso |
|---|---|
| `gymsite-api.vectracargo.com.br` | App / PDF / relatório (hoje em 503) |
| `api.vectracargo.com.br` | Já no `cloudflared/config.yml` |
| `api.getgymsite.com.br` | Canônico produto (adicionar no ingress + DNS) |

O `cloudflared/config.yml` do repo já aponta para `http://gymsite-api:8000` — alinhar o **nome do serviço** no compose ao que o túnel espera (`gymsite-api` ou ajustar o YAML).

---

## 3. Sizing Hetzner (recomendação)

Pipeline A0–A9 + Chromium/Playwright + Weasy + Redis na mesma caixa.

| Plano | Spec | Quando |
|---|---|---|
| **CX22** (~€5–8/mês) | 2 vCPU / 4 GB | Só smoke / staging |
| **CX32** (~€10–15/mês) ★ | 4 vCPU / 8 GB | **Produção inicial** |
| CX42 | 8 vCPU / 16 GB | Se 2+ pipelines paralelos ou OOM |

- Disco: **40–80 GB** SSD (imagem Docker ~1 GB + logs + CNO se montado).
- Região: **Falkenstein (FSN)** ou **Nuremberg (NBG)** — latência EU→BR ok via Cloudflare edge BR; não precisa de datacenter BR.
- SO: **Ubuntu 24.04** + Docker Engine + Compose plugin.
- Firewall Hetzner: **só SSH (22)** da(s) IP(s) do Marcelo; **não** abrir 80/443.

Custo estimado mensal: **€10–20** (VPS) vs Cloud Run + risco de corte por billing Google.

---

## 4. Fases do cutover

### Fase 0 — Pré-requisitos (você / conta)

1. Conta Hetzner Cloud + método de pagamento.
2. Criar VPS CX32 Ubuntu 24.04; anexar chave SSH.
3. Confirmar que o túnel Cloudflare `12675577-d94b-4a19-b1df-a86713dbaf80` (ou o ativo) ainda existe no Zero Trust; `credentials.json` **não** está no git — recuperar do backup / painel CF.
4. ~~Redis~~ → **na VPS** (decisão §8.2).

### Fase 1 — Artefatos no repo (código)

- [x] **`docker-compose.prod.yml`** criado (2026-08-05): serviços `api` (`RUN_QUEUE_WORKER=0`, alias de rede `gymsite-api` batendo com `cloudflared/config.yml`), `worker` (mesma imagem, `RUN_QUEUE_WORKER=1`), `redis` (AOF), `cloudflared`. Sem portas publicadas. Healthcheck via httpx.
- [x] `scripts/deploy.sh` (rolling API + rollback por health) e `scripts/setup-vm.sh` **já existiam** e são genéricos de VPS — servem Hetzner sem alteração.
- [x] `cloudflared/config.yml`: `api.getgymsite.com.br` + staging `api-hetzner.getgymsite.com.br` (rota DNS do túnel = Fase 2/3).
- [x] `scripts/hetzner/bootstrap.sh` + `scripts/hetzner/README.md` (Docker Ubuntu + checklist).
- [ ] Atualizar skill `gymsite-devops` + workflow `/deploy` apontando Hetzner (Cloud Run vira legado) — **após** cutover validado.
- [x] Link cruzado no [RUNBOOK_GCLOUD_503_BILLING.md](RUNBOOK_GCLOUD_503_BILLING.md).

> **Bring-up inicial** (na VPS, dentro de `/opt/gymsite`): `docker compose -f docker-compose.prod.yml up -d`. Depois, updates da API por `./scripts/deploy.sh [tag]`.

### Fase 2 — Bootstrap na VPS (sem DNS ainda)

1. SSH → instalar Docker.
2. Clonar / rsync código + `.env.production` + `cloudflared/credentials.json` para `/opt/gymsite`.
3. `docker compose -f docker-compose.prod.yml up -d`.
4. Health **só interno:** `curl http://127.0.0.1:8000/health`.
5. Smoke pipeline curto (ou reprocessar Pirapora) via CLI na VPS / enqueue Redis.
6. Túnel sobe, mas DNS ainda aponta para Cloud Run morto — ou criar hostname de staging (`api-hetzner.…`) para validar HTTPS antes do cutover.

### Fase 3 — Cutover DNS (janela curta)

1. No Cloudflare Zero Trust / DNS: rota do túnel para os hostnames (ou `cloudflared tunnel route dns`).
2. Remover / sobrescrever CNAME que apontava para Cloud Run.
3. Validar:
   ```powershell
   Invoke-RestMethod https://gymsite-api.vectracargo.com.br/health
   Invoke-RestMethod https://api.getgymsite.com.br/health
   ```
4. Abrir 1 relatório + PDF (Weasy) no browser logado.
5. **Não** apagar Cloud Run no mesmo dia — deixar parado 7 dias como rollback teórico (mesmo com billing off, a imagem fica).

### Fase 4 — Endurecimento

1. Fail2ban / SSH key-only.
2. `logrotate` + `docker system prune` semanal (cron).
3. Backup: `.env.production` e `credentials.json` em cofre (1Password), não só na VPS.
4. Monitor externo (UptimeRobot) em `/health`.
5. Alertas de disco > 80%.
6. Documentar deploy: push `main` → GHCR → SSH pull **ou** deploy manual até Actions estar pronto.

---

## 5. Variáveis de ambiente críticas na VPS

Copiar de `.env.production.example` + secrets reais. Atenção especial:

| Var | Valor na Hetzner |
|---|---|
| `REDIS_URL` | `redis://redis:6379/0` (serviço compose) |
| `RUN_QUEUE_WORKER` | `0` na API · `1` no worker |
| `PIPELINE_LLM_PROVIDER` | `nvidia` (evita Vertex se billing GCP continuar ruim) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `false` |
| `CORS_ORIGINS` | incluir `getgymsite.com.br`, `gymsite.vectracargo.com.br`, etc. |
| `GYMSITE_SCHEMA_SEP` | `1` |
| Maps / Supabase / SearchAPI | iguais à prod atual |

### BigQuery em runtime — AUDITADO 2026-08-05 (resolve decisão §8.4)

O caminho crítico do relatório **já lê Supabase, não BigQuery**:

| Tool runtime | Fonte primária | BQ | Falha billing off |
|---|---|---|---|
| Aluguel MRLR (A4) | `renda_bairro` + `municipio_pib` (Supabase) | não usa | ok |
| `censo_setor_tools.demografia_setor_censo` | espelho Supabase `censo_setor` | fallback `_agregar_bq` | degrada p/ `None`, **não quebra** |
| `perfil_sexo_idade_tools.perfil_sexo_publico_fitness` | espelho `municipio_publico_sexo` | fallback `run_query` | degrada p/ `None`, **não quebra** |
| CNO / CNPJ | tabelas Supabase (loader RFB mensal) | dormente | ok |

**Conclusão:** a API sobe na Hetzner **sem billing GCP** — nenhuma dessas quebra o pipeline; no pior caso uma sub-métrica vem vazia se o **município não estiver no espelho**. As chamadas BQ que sobram são **loaders offline** (`censo_setor_loader`, `cno_bigquery_loader`, `municipio_pib_loader`) — rodam sob demanda, fora do request.

**Ação dia 1:** garantir cobertura de espelho dos municípios-alvo (rodar loaders 1× enquanto billing estiver on, ou backfill). Google Maps continua exigindo chave válida — é o único item Google **realmente** no caminho do request. Ver resposta canônica: Supabase **substitui** o BQ em runtime; não substitui o BQ como warehouse de exploração livre (uso raro, fora do relatório).

---

## 6. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| OOM no pipeline | CX32; um job por vez; `PIPELINE_MAX_WALL_SEC` |
| Disco cheio (Playwright/logs) | prune semanal; volume dedicado logs |
| Túnel cai | `restart: unless-stopped` no cloudflared; alerta uptime |
| Perder `credentials.json` | backup offline; recriar tunnel no painel CF |
| Billing GCP off quebra BQ/Maps | separar “hospedeiro” de “APIs Google”; orçamento mínimo ou espelho |
| Deploy manual esquecido | GH Actions SSH (como doc GCE antigo) na Fase 4 |

---

## 7. Critérios de sucesso

- [ ] `GET /health` 200 em `gymsite-api.vectracargo.com.br` e `api.getgymsite.com.br`
- [ ] Gerar 1 relatório completo (A0–A9) e PDF Weasy
- [ ] Front logado abre relatório sem 503
- [ ] Cloud Run **não** recebe tráfego (DNS só túnel)
- [ ] Custo Hetzner < €25 no 1º mês
- [ ] Runbook + skill devops atualizados (path canônico = Hetzner)

---

## 8. Decisões (travadas 2026-08-05)

1. **VPS:** só preparar código/scripts agora; criar CX32 depois. → `scripts/hetzner/`
2. **Redis:** na VPS via compose (`REDIS_URL=redis://redis:6379/0`).
3. **Staging:** `api-hetzner.getgymsite.com.br` no ingress; cutover DNS só após HTTPS staging verde.
4. ~~**BigQuery:**~~ **RESOLVIDO** (ver §5): runtime é espelho-Supabase-first, degrada gracioso; só garantir cobertura de espelho dos municípios-alvo. Maps segue precisando de chave.

---

## 9. Ordem de execução sugerida (quando “go”)

```
[A] docker-compose.prod.yml + scripts/hetzner/* no repo     ← FEITO
[B] Criar CX32 + SSH + sudo bash scripts/hetzner/bootstrap.sh
[C] Copiar .env + credentials; up -d; health local
[D] Rota DNS staging api-hetzner… → smoke HTTPS
[E] Cutover DNS prod + smoke relatório + PDF
[F] Atualizar /deploy + skill devops; Cloud Run = legado
```
