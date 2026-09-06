# ADR-008 — Produção = Hetzner/Tunnel; órfão GCP …0662901510 ignorar/desligar

| Campo | Valor |
|---|---|
| Status | **Accepted** |
| Data | 2026-09-06 |
| Decisores | GymSite / Marcelo · Opsera #5 |
| Relacionados | `.agent/workflows/deploy.md`, `.agent/skills/gymsite-devops/SKILL.md`, `docs/RUNBOOK_GCLOUD_503_BILLING.md`, `docs/PLAN_HETZNER_VPS_TUNNEL.md`, `.env.production.example` |

## Contexto

Dois projetos GCP `gen-lang-client-*` aparecem no histórico GymSite:

| Projeto | Nome no console (aprox.) | Papel |
|---|---|---|
| `gen-lang-client-0106729343` | "Navi Vectra" | Legado Cloud Run + billing Vertex/BQ (quando necessário) |
| `gen-lang-client-0662901510` | "GymSite" | **Órfão** — tinha `gymsite-api`; **nunca** é produção |

Agentes e templates ainda podiam apontar o órfão (ex.: `GOOGLE_CLOUD_PROJECT` em `.env.production.example`), o que fazia o projeto …0662901510 **parecer** prod.

A stack canônica de API+worker já é **Hetzner VPS + Cloudflare Tunnel** (`docker-compose.prod.yml` · `./scripts/deploy.sh`). Cloud Run está **deprecado** (billing off / 503).

## Decisão

1. **Única produção de API+worker:** Navi Vectra no sentido operacional = **Hetzner + Tunnel** (hosts `api.getgymsite.com.br` / staging `api-hetzner.getgymsite.com.br`). Front = Cloudflare Pages.
2. **Órfão `gen-lang-client-0662901510`:** **ignorar no repo** e **desligar no console GCP** (Marcelo). Não usar em env, scripts, CI defaults, nem `gcloud run deploy`.
3. **`gen-lang-client-0106729343`:** pode permanecer como project id de **Vertex / BigQuery / Discovery** quando o código ainda precisa de GCP client libs. **Não** é destino de deploy da API.
4. **Nunca** `gcloud run deploy` para GymSite. Scripts `deploy_cloud_run.ps1` / `cloudbuild.frontend.yaml` = legado.

### Opções rejeitadas

| Opção | Motivo |
|---|---|
| Migrar prod para o órfão …0662901510 | Confunde identidade; serviço órfão não é o path canônico |
| Redeploy Cloud Run no …0106729343 como "prod" | Billing/503 e cutover Hetzner já decididos |
| Apagar IDs do repo sem ADR | Risco de agente/humano reintroduzir o órfão |

## Consequências

### Positivas

- Critério Opsera #5 explícito: desligar/ignorar órfão; só Navi Vectra (Hetzner/tunnel) como prod.
- Template de env deixa de apontar o órfão como `GOOGLE_CLOUD_PROJECT`.
- Runbooks/skills existentes (`deploy.md`, `gymsite-devops`) ficam alinhados a um ADR numerado.

### Negativas / follow-up

- **Desligar o projeto órfão no GCP Console é ação manual do Marcelo** (billing/IAM/shutdown). O repo só documenta e remove refs stale.
- Docs antigas (`CLAUDE.md`, alguns workflows de debug) ainda mencionam Cloud Run no …0106729343 para logs — tratar como legado de diagnóstico, não como path de deploy.

## Checklist console (Marcelo — fora do repo)

1. GCP Console → selecionar projeto `gen-lang-client-0662901510` (confirmar nome "GymSite" / não "Navi Vectra").
2. Cloud Run → listar serviços (`gymsite-api` etc.) → **não** redeployar; se ainda ativos, **delete** serviços/revisões órfãs **ou** garantir tráfego zero.
3. APIs & Services → desabilitar APIs caras não usadas (Run, Cloud Build, Artifact Registry deste projeto) se seguro.
4. Billing → desvincular billing account deste projeto **ou** confirmar spend = 0.
5. IAM → remover contas de serviço / keys órfãs se existirem (sem colar secrets no chat/Notion).
6. Opcional: Project settings → **Shut down** o projeto inteiro após confirmar que nada de prod aponta para ele.

Verificação: `gcloud projects describe gen-lang-client-0662901510` deve mostrar lifecycle não ativo / sem billing útil; health prod continua em `api-hetzner` / `api.getgymsite`.