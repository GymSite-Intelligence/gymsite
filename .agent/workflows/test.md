---
description: Gate mínimo de testes — pytest no venv do projeto + tsc no frontend. Sem scripts fantasmas.
---

# Workflow: /test

> **Canônico:** [REGRAS_USO_GLOBAL §2#9](../rules/REGRAS_USO_GLOBAL.md) · [CLAUDE.md](../../CLAUDE.md) · skill `gymsite-testing` se existir.
> **Não usar:** `pytest` solto (Python global 3.13 sem deps) · `npm run test:run` / Vitest / Playwright **como gate** (scripts ausentes ou não canônicos neste monorepo).

Ambiente: **PowerShell**, raiz do repo `gymsite_intelligence`.

## Gate mínimo (obrigatório — fecha a etapa)

Esteira de pipeline (allowlist, o mesmo do CI **Pipeline Gate**):

```powershell
$paths = Get-Content ci/pipeline-gate.txt | Where-Object { $_ -and $_ -notmatch '^\s*#' }
.\.venv\Scripts\python.exe -m pytest -q --tb=short -m "not integration and not e2e" @paths
cd frontend; npx tsc --noEmit; cd ..
```

Critério de sucesso: exit code **0** nos dois.

`pytest` largo (fora da allowlist) é opcional — não é o gate de PR.

### Escopo focável

```powershell
# só um arquivo
.\.venv\Scripts\python.exe -m pytest tools\test_aluguel_mrlr.py -x --tb=short
.\.venv\Scripts\python.exe -m pytest tests\test_pipeline_deps.py -x --tb=short -q
```

`pytest.ini` deve ter `asyncio_mode = auto` — sem isso, `async def test_*` falha em modo strict.

## Coverage (opcional, não bloqueia merge)

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=tools --cov=agents --cov-report=term-missing -q
```

Alvos históricos (≥60% tools) = aspiração, não gate hard.

## Frontend — quando existir

| Script | Status no monorepo |
|---|---|
| `npx tsc --noEmit` | **Gate** |
| `npm run test:run` / Vitest | Só se `frontend/package.json` tiver o script — senão **pular** |
| Playwright E2E | Só se config + specs existirem — senão **pular** |

Não inventar Vitest/Playwright como passo bloqueante.

## Anti-padrões

- ❌ `pytest` / `python -m pytest` sem `.venv\Scripts\`
- ❌ `npm run build` / `npm run dev` “pra testar”
- ❌ Assumir que pre-commit rodou os mesmos gates

## Saída

Relatar: quantos testes ok/fail, arquivo que quebrou, `tsc` limpo ou lista de erros. Fix → **re-rodar o gate** antes de commit/deploy.
