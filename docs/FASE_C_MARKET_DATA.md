# Fase C — Market data (opcional)

Complementa Fase A/B: curadoria, degradação explícita, eval sem Deep Research, DAG Airflow.

## Componentes

| Item | Caminho | Função |
|------|---------|--------|
| Franquias curadas | `data/franchise_curated/fitness_br.json` | Referência ticket/investimento (não substitui OSM) |
| Legal fees piloto | `data/legal_fees_pilot/{cidade}_{uf}.json` | Faixas alvará/CAU (Fortaleza, Curitiba) |
| `stale` no bundle | `tools/market_bundle.compute_bundle_stale` | CVM/SINAPI/OSM/aluguel degradados |
| Alertas A4 vs SMFT3 | `tools/financial_tools._alertas_vs_sector_listed` | Payback/margem vs CVM |
| Golden A0 sem DR | `scripts/batch/golden_bundle_a0_gate.py` | `A0_CONTEXT_SOURCE=ckan_bundle` |
| DAG Airflow | `scripts/batch/dags/gym_market_weekly_dag.py` | Batch semanal + gate |

## Comandos

```bash
# Gate Fase C (onda red)
python scripts/batch/golden_bundle_a0_gate.py --wave red

# Via eval
python eval/run_eval.py --bundle-a0-gate

# Testes
python scripts/batch/run_stage_tests.py --stage c1_golden_bundle_a0
python scripts/batch/run_stage_tests.py --stage c2_curadoria
python scripts/batch/run_stage_tests.py --stage c3_airflow_dag
python scripts/batch/run_stage_tests.py --stage all
```

## API

```env
A0_CONTEXT_SOURCE=ckan_bundle   # proíbe DR quando bundle fresco
A0_CONTEXT_SOURCE=auto          # default: bundle completo → skip DR
```

## Airflow na VM

```bash
cp scripts/batch/dags/gym_market_weekly_dag.py /opt/airflow/dags/
# Ajustar REPO_ROOT dentro do arquivo
```

## Próximo (fora do escopo C)

- DataStore CKAN municipal → `demografia.bairro` automático
- Scrape franquias (ToS) — manter curadoria
- Golden eval completo pós-rerun sem DR (`scripts/rerun_golden_for_eval.py` + `A0_CONTEXT_SOURCE=ckan_bundle`)
