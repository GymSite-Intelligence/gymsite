# Batch — market data (Fase A+)

## Regra: teste após cada etapa

Ver **[`docs/MARKET_DATA_TEST_GATES.md`](../../docs/MARKET_DATA_TEST_GATES.md)**.

```bash
python scripts/batch/run_stage_tests.py --stage a1_ckan   # pytest + E2E acumulado
python scripts/batch/run_stage_tests.py --stage all       # antes de PR / wave
python scripts/batch/run_stage_tests.py --e2e-only        # só E2E completo
```

## Batch semanal (cron VM)

Orquestra CVM + SINAPI + benchmarks + bundles de todas as linhas em `data/market_waves.csv`:

```bash
python scripts/batch/run_weekly_market_batch.py
python scripts/batch/run_weekly_market_batch.py --skip-enrichment   # sem Playwright/OSM refresh
```

Crontab de exemplo: [`cron/weekly_market_batch.crontab`](cron/weekly_market_batch.crontab)

```cron
0 3 * * 0 cd /opt/gymsite_intelligence && python3 scripts/batch/run_weekly_market_batch.py --skip-enrichment >> /var/log/gym_market_batch.log 2>&1
```

## Build manual (operacional)

```bash
python scripts/batch/update_benchmark_snapshots.py --fetch-cvm
python scripts/batch/update_capex_indices.py
python scripts/batch/update_benchmark_snapshots.py --skip-cvm
python scripts/batch/build_market_bundles.py --cidade Fortaleza --bairro Meireles --uf CE --skip-ckan
python scripts/batch/discover_ckan_catalog.py --cidade Fortaleza --uf CE
```

Variáveis API: `A0_CONTEXT_SOURCE=auto|ckan_bundle|deep_research_fallback`

## Fase C

- [`docs/FASE_C_MARKET_DATA.md`](../../docs/FASE_C_MARKET_DATA.md)
- `python scripts/batch/golden_bundle_a0_gate.py --wave red`
- DAG: [`dags/gym_market_weekly_dag.py`](dags/gym_market_weekly_dag.py)
