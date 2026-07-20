---
description: Run CNPJ×CNO prospecting engine for a city. Project venv only.
---

# Workflow: /prospect

> **Skill:** `gymsite-prospecting`. **Regras:** P-000 · REGRAS (Python = `.venv`).
> **Não confundir:** `/report` (pipeline A0–A9 viabilidade). Prospecção = `prospecting/` + tabela oportunidades.
> Entrypoint: `python -m prospecting.cli` (não `prospecting.engine` direto na CLI).

## Prerequisites

- `.venv` com deps do projeto
- `SUPABASE_*` (service) válidos
- `GOOGLE_MAPS_API_KEY` / SearchAPI se enrich Maps ativo
- CNO: `CNO_DATA_DIR` ou `--cno-dir` apontando extract com `cno.csv` (senão match CNO fraco / skip)

## Steps

1. **Validate inputs**
   - cidade + UF (default Fortaleza/CE)
   - Confirmar org se `--org-id` necessário

2. **Dry-run primeiro** (recomendado)
   ```powershell
   .\.venv\Scripts\python.exe -m prospecting.cli --cidade Fortaleza --uf CE --dias 90 --dry-run --json
   ```

3. **Run persistente** (só com ok explícito em prod)
   ```powershell
   .\.venv\Scripts\python.exe -m prospecting.cli --cidade Fortaleza --uf CE --dias 90
   ```
   Opções: `--limit 200` · `--cno-dir PATH` · `--webhook-url URL` · `--org-id UUID`

4. **Validate output**
   - Stats CLI: `persistidos`, `qualificados`, webhooks
   - SB `oportunidades_prospeccao` (schema via `tbl` / `gymsite` se SEP): novos rows, `score_match` ∈ [0,1], status esperado
   - Sem dump de secrets nos logs

5. **Summary**
   - Total match / qualificados / persistidos
   - Top scores; falhas webhook

## Safety

- ⚠️ Persiste no banco + pode disparar webhook — **confirmar prod** antes do passo 3
- ⚠️ Maps/SearchAPI = custo; `--limit` em smoke
- ⚠️ Sempre `.venv\Scripts\python.exe` — nunca `python` global

## Anti-padrões

- ❌ `python -m prospecting.engine …` como CLI (use `prospecting.cli`)
- ❌ `rm -rf metrics/cache` bash-only sem necessidade
- ❌ Rodar prod sem `--dry-run` prévio
