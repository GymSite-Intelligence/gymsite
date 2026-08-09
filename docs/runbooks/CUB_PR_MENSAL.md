# Runbook — PR mensal CUB estadual

**Objetivo:** manter `data/cub_pilot/cub_estadual_golden.json` fresco para CAPEX obra (A4, régua `OBRA_REGUA=cub`).

**Não fazer:** scrape automático SindusCon.

## Passo a passo

1. Coletar R$/m² CUB (ou média estadual) das 27 UFs — fonte SindusCon / CBIC / buscador curado.
2. Editar `data/cub_pilot/cub_estadual_golden.json`:
   - `cub_m2`, `periodo_ref` (ex. `agosto 2026`), `fonte_uf`
   - `data_coleta` = dia da curadoria (`YYYY-MM-DD`)
3. Se UF só tem proxy IBGE (sem CUB SindusCon), manter `fonte_uf` com a palavra **`proxy`** (ex. `IBGE SIDRA média (proxy CUB)`).
4. Validar:

```bash
.venv\Scripts\python.exe -m tools.cub_golden_validate
# ou sem ratio SINAPI:
.venv\Scripts\python.exe -m tools.cub_golden_validate --skip-ratio
```

5. Abrir PR com o JSON (+ só o necessário). CI / gate local deve passar.
6. Após merge: A4 lê via `tools/cub_indices.py` → `load_cub_snapshot()` (golden; cache `metrics/cache/cub_estadual.json` se existir).

## Gate (o que falha)

| Regra | Detalhe |
|---|---|
| 27 UFs | Lista fixa BR |
| `cub_m2` | > 0 |
| `periodo_ref` | Parseável (`mês YYYY`); idade ≤ **3 meses** vs hoje, **exceto** se `fonte_uf` contém `proxy` |
| Ratio CUB/SINAPI | Por UF ~1.04–1.10; média ~1.05–1.09 (se fixture SINAPI presente) |

## Se o gate acusar MS / PI velhos

Atualizar números reais **ou** (só se for proxy de fato) acrescentar `proxy` em `fonte_uf`. Não inventar mês novo sem fonte.

## Lembrete

Todo mês: este runbook. SINAPI continua automático no batch semanal; CUB = este PR.
