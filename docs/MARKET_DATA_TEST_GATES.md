# Gates de teste — pipeline de dados (Market Atlas)

**Regra:** após cada etapa de código → gate da etapa → **E2E incremental** (default ligado).

## Comandos

```bash
python scripts/batch/run_stage_tests.py --list

# Uma etapa: pytest + artefatos + E2E acumulado ate essa etapa
python scripts/batch/run_stage_tests.py --stage a4_bundle

# Tudo (unit + E2E apos cada secao)
python scripts/batch/run_stage_tests.py --stage all

# So pytest, sem E2E
python scripts/batch/run_stage_tests.py --stage a4_bundle --no-e2e

# So E2E completo
python scripts/batch/run_stage_tests.py --e2e-only
python scripts/batch/test_e2e_market_pipeline.py --stage a6_e2e

# Rebuild bundle + batch + E2E (rede)
python scripts/batch/run_stage_tests.py --stage all --with-batch
```

## Mapa etapa → gate → E2E acumulado

| Etapa | Unit gate | E2E apos passar |
|-------|-----------|-----------------|
| **a1_ckan** | `test_ckan_client.py` | queries CKAN |
| **a2_cvm** | `test_cvm_listed_metrics.py` | + SMFT3 snapshot |
| **a3_benchmarks** | artefatos JSON | + `obter_benchmarks_setoriais` |
| **a4_bundle** | `test_market_bundle.py` | + bundle + **DR skip &lt;5s** |
| **a5_integration** | imports + pytest conjunto | + inject cache/bundle + viabilidade 3 cenarios |
| **a6_e2e** | `test_e2e_market_pipeline.py` | suite completa |

Implementacao E2E: [`scripts/batch/e2e_gate.py`](../scripts/batch/e2e_gate.py)

## Artefatos esperados (Fase A)

| Arquivo | Validação |
|---------|-----------|
| `metrics/cache/benchmark_snapshots.json` | `setorial` + `sector_listed` |
| `metrics/cache/sector_listed.json` | `empresas[]` |
| `data/market_bundles/fortaleza_meireles_CE.json` | `gerado_em`, `codigo_ibge_municipio` |

## E2E vs relatório API completo

O gate E2E **nao** substitui `run_market_wave --mode api` (ADK 30–60 min). Valida:

- `market_bundle` carrega e gera briefing
- `rodar_deep_research` retorna em &lt;5s com `skip_deep_research` (sem agente 20 min)
- `calcular_viabilidade_3_cenarios` com benchmarks do snapshot

Smoke API (manual, pos-`all` PASS):

```bash
python scripts/run_market_wave.py --wave red --dry-run
python scripts/run_market_wave.py --id fortaleza_parangaba_red_w1 --mode api --limit 1
```

## Fase B

| Etapa | Gate |
|-------|------|
| **b1_bairro** | `test_bairro_renda_loader.py` + bundle sem `renda_media_bairro` em missing (Meireles) |
| **b2_cvm** | `test_cvm_fetch.py` + SMFT3 via ITR (`--fetch-cvm` no batch) |
| **b3_sinapi** | `test_sinapi_indices.py` + `metrics/cache/capex_indices.json` |

```bash
python scripts/batch/run_weekly_market_batch.py --skip-enrichment
python scripts/batch/run_stage_tests.py --stage b1_bairro --with-batch
python scripts/batch/run_stage_tests.py --stage b2_cvm --with-batch
python scripts/batch/run_stage_tests.py --stage b3_sinapi --with-batch
python scripts/enrichment/smoke_test_real.py --use-bundle --cidade Fortaleza --bairro Meireles --uf CE
```

## Fase C

| Etapa | Gate |
|-------|------|
| **c1_golden_bundle_a0** | `test_fase_c.py` + `golden_bundle_a0_gate.py --wave red` |
| **c2_curadoria** | franquias + `legal_fees_pilot` |
| **c3_airflow_dag** | import DAG |

Ver [`FASE_C_MARKET_DATA.md`](./FASE_C_MARKET_DATA.md).

```bash
python scripts/batch/golden_bundle_a0_gate.py --wave red
python eval/run_eval.py --bundle-a0-gate
A0_CONTEXT_SOURCE=ckan_bundle python scripts/run_market_wave.py --id fortaleza_meireles_red_w1 --mode local
```
