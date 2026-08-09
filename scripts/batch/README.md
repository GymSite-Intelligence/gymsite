# Batch — market data (Fase A+)

## Regra: teste após cada etapa

Ver **[`docs/MARKET_DATA_TEST_GATES.md`](../../docs/MARKET_DATA_TEST_GATES.md)**.

```bash
python scripts/batch/run_stage_tests.py --stage a1_ckan   # pytest + E2E acumulado
python scripts/batch/run_stage_tests.py --stage all       # antes de PR / wave
python scripts/batch/run_stage_tests.py --e2e-only        # só E2E completo
```

## Batch semanal (Supabase pg_cron → Cloud Run worker)

**Canônico (prod):** `pg_cron` domingo 06:00 UTC chama `pg_net` →
`POST /api/internal/cron/weekly-market-batch` no **gymsite-worker**
(header `X-Cron-Secret` = `MARKET_BATCH_CRON_SECRET`).

Migration: [`db/migrations/20260727_market_batch_supabase_cron.sql`](../../db/migrations/20260727_market_batch_supabase_cron.sql)

Pós-migrate (SQL editor, service_role):

```sql
update gymsite.cron_http_targets
   set url = 'https://<worker-host>/api/internal/cron/weekly-market-batch',
       secret = '<MARKET_BATCH_CRON_SECRET>',
       enabled = true
 where job_name = 'weekly_market_batch';
```

Manual local / smoke:

```bash
python scripts/batch/run_weekly_market_batch.py
python scripts/batch/run_weekly_market_batch.py --skip-enrichment
```

GitHub Actions `weekly-market-batch.yml` = **só workflow_dispatch** (fallback emergência).

Crontab VM legado: [`cron/weekly_market_batch.crontab`](cron/weekly_market_batch.crontab)

## Build manual (operacional)

```bash
python scripts/batch/update_benchmark_snapshots.py --fetch-cvm
python scripts/batch/update_capex_indices.py
python scripts/batch/update_benchmark_snapshots.py --skip-cvm
python scripts/batch/build_market_bundles.py --cidade Fortaleza --bairro Meireles --uf CE --skip-ckan
python scripts/batch/discover_ckan_catalog.py --cidade Fortaleza --uf CE
python scripts/batch/discover_ckan_catalog.py --mode macro --groups Habitação,Urbanismo
python scripts/batch/discover_ckan_catalog.py --mode org --orgs ibge,mcid,df --max-pages 4
python scripts/batch/discover_ckan_catalog.py --mode org --orgs bh --nome bairro --require-group
```

CKAN/dados.gov: `--mode auto` = city se `--cidade`; senão macro.
Federal = API pública + ORG_SEED (Action `/api/3` = 401). Precisa `CKAN_API_KEY`.

## Fase C

- [`docs/FASE_C_MARKET_DATA.md`](../../docs/FASE_C_MARKET_DATA.md)
- `python scripts/batch/golden_bundle_a0_gate.py --wave red`
- DAG: [`dags/gym_market_weekly_dag.py`](dags/gym_market_weekly_dag.py)
