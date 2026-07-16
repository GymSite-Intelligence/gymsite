# SPEC — market_bundle v2 (store histórico)

---
id: spec-market-bundle-v2
dominio: market_data
versao: 2.0
data: 2026-07-16
constitution: C2.1, C6.1, fontes-deterministicas
relacionados:
  - tools/market_bundle.py
  - tools/market_store.py
  - tools/renda_bairro_loader.py
  - tools/bairro_renda_loader.py
  - tools/enrichment_cache.py
  - tools/search_raw_cache.py
  - tools/cache_store.py
  - agents/specs/SPEC_A0_ContextBuilder.md
  - .agent/rules/auditoria-conformidade.md
diagramas:
  - agents/specs/SPEC_market_bundle_v2.mmd
notas_diagrama: >
  L1 DFMEA checkpoints Chk1–5 (jul/2026); enrichment_cache legado no L1;
  writer renda_bairro_loader ≠ reader bairro_renda_loader.
---

## 0. Renda: dois arquivos, um pipeline

| Arquivo | Papel |
|---|---|
| `renda_bairro_loader.py` | **Writer** ETL — ZIP IBGE → JSON → upsert `renda_bairro` |
| `bairro_renda_loader.py` | **Reader** hot-path — SELECT tabela → CKAN 2010 → piloto |

Não duplicata: ingest vs consumo. Nome invertido = dívida naming.

`enrichment_cache.py` = FS `scripts/enrichment/cache` (TTL 7d), antecessor do bundle. `api.py` ainda chama `inject_cache_context` antes de `inject_market_bundle_context`.

## 1. Responsabilidade

**market_bundle v2** formaliza o desenho: dados de mercado **históricos** são compostos **1× no batch**; cada relatório **só carrega** (+ freshness barato). Não substitui A2/A3a/A4/A6 vivos onde a regra de fonte exige dado ao vivo ou LLM.

Dois armazéns distintos (não fundir):

| Store | Chave | Conteúdo | Consumidor hot-path |
|---|---|---|---|
| `market_bundles` (`market_store`) | slug cidade_bairro_UF | payload JSON (demografia snapshot, sector, legal, OSM resumo, …) | **A0** |
| SearchAPI histórico | `place_id` / `(engine, params_hash)` | reviews (`cache_reviews` + `search_raw`), maps raw, popular_times | **A3a** |

Renda canônica de **linha** = tabela `renda_bairro` (populada por `renda_bairro_loader`, lida por `bairro_renda_loader.enrich_demografia_bairro`) — o bundle só **espelha** `demografia.bairro` no batch.

## 2. Princípios

1. **Batch = armazenamento + validação pesada; relatório = carregamento** (+ `bundle_is_fresh` / TTL).
2. **Identidade ≠ demografia:** `local` (cidade/bairro/uf) separado de `demografia.*`.
3. **Bairro primário no parecer de renda:** `demografia.bairro.renda_media` + `fonte` (IBGE 2022). Município = contexto / fallback de score A2.
4. **Aluguel fora do bundle:** A4 MRLR.
5. **A3a não lê `competicao_local` do bundle** pra lista/reviews — usa SearchAPI + store por `place_id`.
6. **Playwright KP fora do hot-path prod** (`COMPETITOR_PLAYWRIGHT_ENRICH` default off).

## 3. Ciclo de vida

```
batch: build_market_bundles → save_market_bundle → market_store.upsert
report: inject_market_bundle_context → A0 carregar_market_bundle (bundle-only; DR/Kimi OFF)
A3a: get reviews/maps from cache_reviews | search_raw → miss → SearchAPI 1× → upsert
```

**Act-on A0 bundle-only (2026-07-16):** `rodar_deep_research` / `rodar_kimi_research` removidos das tools do A0. Bundle missing → `dados_nao_disponiveis` nos campos qualitativos; CNPJ/OSM seguem.

Env **obrigatório no `gymsite-worker`** (não só API): `A0_CONTEXT_SOURCE=ckan_bundle`, `MARKET_BUNDLE_SUPABASE=1`, `PIPELINE_MAX_WALL_SEC`, `COMPETITOR_PLAYWRIGHT_ENRICH=0`. `A0_RESEARCH_PROVIDER` pode ficar no env mas **não é mais consumido pelo A0**.

## 4. Contrato payload (resumo)

| Campo | Batch? | Hot-path lê? |
|---|---|---|
| `local` | sim | A0 título / slug |
| `demografia.bairro` | sim | A0 briefing |
| `demografia.municipio` | sim | A0 opcional; A2 recalcula vivo |
| `sector_benchmarks` / franquias / legal / bcb / capex | sim | A0 |
| `competicao_local` | semi | **só A0** |
| `stale` / `missing_fields` | sim | A0 skip DR |
| reviews / Places details / Playwright | **não no bundle** | A3a store SearchAPI |

## 5. Ganho de latência (alvo Cocó / auditoria `ed36ed08`)

| Etapa | Antes | Alvo store |
|---|---:|---:|
| A0 | ~766s (Kimi/DR) | &lt;90s (load bundle) |
| A3a | ~834s (Playwright+seq) | &lt;250s (cache SearchAPI + Playwright off) |
| A6 | ~478s | sem mudança via store |

## 6. Critérios de aceite

- [ ] Worker com `A0_CONTEXT_SOURCE=ckan_bundle` e bundle Cocó fresco → ContextBuilder &lt; 90s
- [ ] `_fetch_reviews_bundle` hit `cache_reviews` ou `search_raw` sem re-cobrar SearchAPI no 2º relatório mesma praça
- [ ] `COMPETITOR_PLAYWRIGHT_ENRICH` off → A3a não chama `enriquecer_concorrente_via_google`
- [ ] Diagrama `.mmd` alinhado a este SPEC; Preview local via MermaidChart
- [ ] Caso conformidade wall-clock atualizado (Corrective)

## 7. Fora de escopo v2

- Redesign A6 LLM
- Fundir `bairro_renda_loader` em `market_store.py`
- Meter reviews no JSON `market_bundle`

## 8. Ponte com auditoria (conformidade + tools)

O bundle **não é** o processo de auditoria — é **amostra + critério** quando o gap toca mercado/A0/deploy.

| Camada | Onde encaixa | Gatilho típico |
|---|---|---|
| **Primário** (batch→A0) | Conformidade domínio **Deploy/Fontes** | worker sem `A0_CONTEXT_SOURCE=ckan_bundle`; A0 &gt;90s; bundle ausente |
| **Secundário** (renda / place cache) | Conformidade **Fontes** + Tools se SKU | A2/A4 lendo fonte errada; A3a miss→SearchAPI dual |
| **Terciário** (stale / live / DR) | Tools se NC latência ou fallback | `compute_bundle_stale` ignora; A3a long-pole; A6 Places N |

**Checklist Evidence (pré-release bundle):**

1. UUID relatório + `etapas` wall A0 / A3a / A6
2. Env worker = API (`ckan_bundle`, `MARKET_BUNDLE_SUPABASE`, `PIPELINE_MAX_WALL_SEC`, PW off)
3. Ledger `relatorio_api_calls` (sem Places no caminho listing)
4. Payload: `gerado_em` fresco · `stale_reasons` · `missing_fields` vs `LIVE_TRAIL_FIELDS`
5. Se gap Tool → Draft `auditoria-tools` + 5 Whys `.mmd`; se gap env/deploy → ciclo `auditoria-conformidade`

Cookbook mental: Receita Mestra = §6 aceite; sprint Corrective = Act-on P-000; Retest = golden / e2e_gate.
