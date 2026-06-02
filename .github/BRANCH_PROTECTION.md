# Branch protection — GymSite Intelligence

Configure uma vez no GitHub (repo **Marcelo-Rosas/gymsite** ou o nome atual).

## `main` — regras recomendadas

| Regra | Valor |
|-------|--------|
| Require pull request | Sim |
| Required check | **Frontend CI** → job **Build & Lint** |
| Require up to date | Sim |
| Restrict pushes | Apenas maintainers (opcional) |

## O que NÃO marcar como required no PR

- **Deploy Frontend (Cloudflare Pages)** — só executa após merge; exigir no PR deixaria check eternamente pendente em PRs sem deploy.

## API / backend

Workflow **CI/CD** (`.github/workflows/ci-cd.yml`) cobre Docker/API. Pode adicionar como required check separado se quiser bloquear merge com API quebrada.

## Limpar checks antigos

- Actions → filtrar workflow → **Cancel workflow** em runs `queued`/`in_progress` obsoletos  
- Os workflows usam `cancel-in-progress: true` para novos pushes no mesmo branch/PR
