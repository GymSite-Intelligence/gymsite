# Branch protection — GymSite Intelligence

Configure uma vez no GitHub (repo **Marcelo-Rosas/gymsite** ou o nome atual).

## `main` — regras recomendadas

| Regra | Valor |
|-------|--------|
| Require pull request | Sim |
| Required check | **Frontend CI** → job **Build & Lint** |
| Required check | **Pipeline Gate** → job **Pipeline Gate** |
| Require up to date | Sim |
| Restrict pushes | Apenas maintainers (opcional) |

## O que NÃO marcar como required no PR

- **Deploy Frontend (Cloudflare Pages)** — só executa após merge; exigir no PR deixaria check eternamente pendente em PRs sem deploy.

## API / backend

- **Pipeline Gate** (`.github/workflows/pipeline-gate.yml`) — contratos A0–A9 / MRLR / HTML, allowlist em `ci/pipeline-gate.txt`. Sem LLM, sem rede. **Marcar como required.**
- Workflow **CI/CD** (`.github/workflows/ci-cd.yml`) cobre Docker/API. Pode adicionar como required check separado se quiser bloquear merge com imagem quebrada. Pytest decorativo (`|| true`) foi removido daí.

Sem o clique de required check no GitHub, o job **Pipeline Gate** corre no PR mas o merge não bloqueia.

## Limpar checks antigos

- Actions → filtrar workflow → **Cancel workflow** em runs `queued`/`in_progress` obsoletos  
- Os workflows usam `cancel-in-progress: true` para novos pushes no mesmo branch/PR
