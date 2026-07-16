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
  - tools/bairro_renda_loader.py
  - tools/search_raw_cache.py
  - tools/cache_store.py
  - agents/specs/SPEC_A0_ContextBuilder.md
  - .agent/rules/auditoria-conformidade.md
diagramas:
  - agents/specs/SPEC_market_bundle_v2.mmd
---

## 1. Responsabilidade

**market_bundle v2** formaliza o desenho: dados de mercado **históricos** são compostos **1× no batch**; cada relatório **só carrega** (+ freshness barato). Não substitui A2/A3a/A4/A6 vivos onde a regra de fonte exige dado ao vivo ou LLM.

Dois armazéns distintos (não fundir):

| Store | Chave | Conteúdo | Consumidor hot-path |
|---|---|---|---|
| `market_bundles` (`market_store`) | slug cidade_bairro_UF | payload JSON (demografia snapshot, sector, legal, OSM resumo, …) | **A0** |
| SearchAPI histórico | `place_id` / `(engine, params_hash)` | reviews (`cache_reviews` + `search_raw`), maps raw, popular_times | **A3a** |

Renda canônica de **linha** = tabela `renda_bairro` via `bairro_renda_loader` — o bundle só **espelha** `demografia.bairro` no batch.

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
report: inject_market_bundle_context → A0 carregar_market_bundle (skip DR se fresco + ckan_bundle)
A3a: get reviews/maps from cache_reviews | search_raw → miss → SearchAPI 1× → upsert
```

Env **obrigatório no `gymsite-worker`** (não só API): `A0_CONTEXT_SOURCE=ckan_bundle`, `MARKET_BUNDLE_SUPABASE=1`, `PIPELINE_MAX_WALL_SEC`, `COMPETITOR_PLAYWRIGHT_ENRICH=0`.

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
