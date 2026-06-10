# Market Atlas — Plano mestre de construção

Documento único que integra: ondas vermelho → transição → azul, VM GCP, enrichment cache e frontend estratégico.

## Arquitetura alvo (fase 1)

- **VM GCE** (`southamerica-east1`): API + Redis + cloudflared + volumes (CNO, cache, Playwright)
- **Supabase**: Postgres + Auth + RLS (sem migração para Cloud SQL/Firestore nesta fase)
- **GCS** (opcional fase A): CNO, PDFs, exports Atlas
- **Gemini** (A0–A9): produção; local/fine-tune só após golden ≥30

## Duas lentes na UI

| Lente | Fonte | Pergunta |
|-------|--------|----------|
| Viabilidade do ponto | A6 `veredito` | Abro aqui? |
| Estratégia de mercado | A9 `veredito_posicionamento` | Low-cost ou premium? |

## Ondas de relatórios

Catálogo: [`data/market_waves.csv`](../data/market_waves.csv)

| Wave | Objetivo | Exemplos golden |
|------|----------|-----------------|
| `red` | Credibilidade em mercado saturado | Parangaba, Meireles, Aldeota, Batel |
| `transition` | Escape capital → RM | Eusébio ↔ Fortaleza |
| `blue` | Primeiro premium / interior | Anápolis, Altamira, Eusébio |

## Fases operacionais

1. **F0** — VM + Redis + `market_waves.csv` + migration view
2. **F1** — 8 relatórios vermelho (eval PASS) + alertas de viabilidade vs benchmarks estáticos (ver abaixo)
3. **F2** — 4 pares transição
4. **F3** — 6 relatórios azul (cache enrichment antes — ver nota técnica)
5. **F4** — Market Atlas v1 publicável + benchmarks dinâmicos (CVM/batch) conforme [`ARQUITETURA_DADOS_MERCADO_E_LATENCIA.md`](./ARQUITETURA_DADOS_MERCADO_E_LATENCIA.md) fase A/C
6. **Fase C** — curadoria + eval A0 sem DR + DAG — [`FASE_C_MARKET_DATA.md`](./FASE_C_MARKET_DATA.md)

### Nota técnica F3 — Enrichment cache (determinístico)

Na wave `blue`, **pré-aquecer** o contexto local **antes** do ADK:

| Bloco | Fonte | Onde no repo |
|-------|--------|----------------|
| Concorrência (raio) | OSM / Overpass | `tools/local_market_facts` → `scripts/enrichment/cache_enrichment.py` |
| Aluguel comercial | Portais (OLX, Zap, Viva) | `tools/aluguel_municipio_portais` (Playwright em thread no Windows) |
| Macro imobiliário | BCB Olinda | `tools/bcb_imobiliario_olinda` |
| Demografia | IBGE direto + **CKAN só como catálogo** (descoberta de pacotes municipais) | `tools/ibge_tools` (A2); batch CKAN → ver arquitetura de dados |
| Compressão | Prompt &lt; ~1k tokens para smoke LLM | `scripts/enrichment/prompt_compressor.py` |

**Regras:** não rodar scraping síncrono de portais/OSM **dentro** do loop ADK; injetar via `tools/enrichment_cache.py` / futuro `market_bundle` no `api.py` (TTL 7 dias). Smoke validado: ~26 s / ~442 tokens (`scripts/enrichment/production_run_metrics.json`) — não confundir com pipeline A0–A9 completo.

### F1 — Benchmarks na wave vermelha (antes do CVM dinâmico)

Mesmo com fetch CVM na F4, a F1 deve validar projeções contra benchmarks **já no código**:

- `tools/financial_tools.py` — payback, margem, `CAPEX_DETALHADO_BASE`, cenários Smart Fit/Bluefit nas premissas
- `tools/benchmarks_tool.py` — ticket/inadimplência (grounding ou `fallback_acad_2024`)

**DoD F1:** relatórios red wave exibem alertas quando payback ou margem divergem dos thresholds setoriais (ex.: payback &gt; 48 meses, projeção &lt; 70% benchmark Smart Fit realista). Eval golden compara números A4/A6.

### CKAN — papel no Market Atlas

**CKAN = catálogo federado** (dados.gov + portais municipais): descoberta de datasets, metadados, links e DataStore. **Não** hospeda dados proprietários GymSite.

Uso principal nesta fase:

1. Achar pacotes **demografia macro / bairro** (IPECE, SIMDA, secretarias) → ETL batch → `market_bundle`
2. Apontar recursos que redirecionam para **IBGE SIDRA**, CVM, BCB — consumo na **API oficial**, não só Solr

Trilha **CVM / Smart Fit (SMFT3)** é separada: benchmarks de rede listada → `sector_benchmarks` no bundle (ver doc de arquitetura).

## Frontend (este repo)

- `/market-atlas` — KPIs oceano + distribuição + tabela por wave
- Dashboard — faixa KPI oceano (A9)
- Viewer — `DualVereditoStrip` (A6 + A9)
- Listagem — coluna oceano quando view exposta

## Dados, latência e batch (CKAN / CVM / bundle)

- Documento único: [`ARQUITETURA_DADOS_MERCADO_E_LATENCIA.md`](./ARQUITETURA_DADOS_MERCADO_E_LATENCIA.md) — CKAN como catálogo, trilha CVM (Smart Fit), `market_bundle`, A0 loader, PRDs benchmarks/CAPEX, cron VM.

## Metodologia

- ERRC + 5 GAPs: `docs/metodologia/`
- A9 spec: `docs/metodologia/POSITIONING_FRAMEWORK.md`
- Qwen (taxonomia) + Bailian RAG (piloto): [`docs/QWEN_BAILIAN_RAG.md`](./QWEN_BAILIAN_RAG.md)

## Próximo passo imediato

### Pré-voo (antes de `--mode api`)

1. `.env` da API: `PIPELINE_MAX_WALL_SEC=3600` (e Redis URL se fila ativa)
2. VM: Redis acessível; worker/API no mesmo ambiente de cache
3. Credenciais: Supabase service role + `GOOGLE_API_KEY` / Vertex na VM
4. **Fase A/B (batch):** ver [`scripts/batch/README.md`](../scripts/batch/README.md)
   ```bash
   python scripts/batch/run_weekly_market_batch.py --skip-enrichment
   # ou manual:
   python scripts/batch/update_benchmark_snapshots.py --fetch-cvm
   python scripts/batch/update_capex_indices.py
   python scripts/batch/build_market_bundles.py --cidade Fortaleza --bairro Meireles --uf CE --skip-ckan
   ```
5. (Opcional) `A0_CONTEXT_SOURCE=auto` na API — bundle fresco pula Deep Research no pipeline
6. **Gate de testes:** `python scripts/batch/run_stage_tests.py --stage all` (pytest + **E2E apos cada secao**) — ver [`MARKET_DATA_TEST_GATES.md`](./MARKET_DATA_TEST_GATES.md)

```bash
# Listar onda vermelho (F1)
python scripts/run_market_wave.py --wave red --dry-run

# Disparar via API (Redis + worker ativos)
python scripts/run_market_wave.py --wave red --mode api --limit 1

# Ou pipeline local (sem depender da API pública)
python scripts/run_market_wave.py --id fortaleza_parangaba_red_w1 --mode local
```

Log: `data/market_waves_runs/runs_YYYYMMDD.jsonl`

### Timeout 30 min (`Root node GymSiteIntelligence was cancelled`)

O API cancela o ADK após `PIPELINE_MAX_WALL_SEC` (default **1800**). No `.env` da API:

```env
PIPELINE_MAX_WALL_SEC=3600
```

Reinicie a API e rode de novo. Relatório `failed` pode ser reprocessado pela UI («Gerar novamente») ou:

```bash
python scripts/run_market_wave.py --id fortaleza_parangaba_red_w1 --mode api --limit 1
```
