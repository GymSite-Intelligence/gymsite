# SPEC — A3a CompetitorSearch store histórico v2

---
id: spec-a3a-store-v2
agente: CompetitorSearch
versao: 2.0
data: 2026-07-16
pai: agents/specs/SPEC_A3a_CompetitorSearch.md
relacionados:
  - agents/a3a_competitor_search.py
  - tools/competitor_tools.py (analisar_concorrentes_a3a_completo)
  - agents/specs/SPEC_market_bundle_v2.md (nó A3a no diagrama)
  - .agent/rules/auditoria-tools.md
diagramas:
  - agents/specs/SPEC_a3a_store_v2.mmd
  - tools/a3a_competitor_search_5whys.mmd
---

## 1. Responsabilidade

A3a = **BaseAgent** fino ([`a3a_competitor_search.py`](../a3a_competitor_search.py)): só chama `analisar_concorrentes_a3a_completo` e grava `concorrentes_brutos`. Latência/custo vivem **100% na macro** (`tools/competitor_tools.py`), não no agente.

Retest Cocó `6bb90ff7`: A3a **1844s** (long-pole). Playwright já off — vilão = enrich **sequencial** + Places Details + caches que **não persistem** no Cloud Run.

## 2. Granularidade da macro (`_processar_um` × N)

| Passo | Função / SKU | Store hoje | Histórico batch? | Hot-path alvo |
|---|---|---|---|---|
| 1. Lista top-N | `buscar_concorrentes_balanceados` → Maps SearchAPI (+ Places dual ainda) | `search_raw` google_maps parcial | semi | SearchAPI-only + cache slug/bairro |
| 2. Filtro | `_eh_academia_tradicional` | — | sim (CPU) | igual |
| 3a. Reviews | `buscar_reviews_academia` → `_fetch_reviews_bundle` | `cache_reviews` + `search_raw` | **sim** TTL 7d | hit obrigatório 2ª praça |
| 3b. Piores notas | `_reviews_baixa_nota_searchapi` | pode **re-cobrar** mesmo place | sim | reusar bundle 3a |
| 3c. Playwright KP | `enriquecer_concorrente_via_google` | — | **não** (legado) | **off** (`COMPETITOR_PLAYWRIGHT_ENRICH=0`) |
| 3d. Atributos | `obter_atributos_place` → `places_details_new` | `cache_places_details`? | semi | skip se SearchAPI já tem telefone/site; senão cache SB |
| 3e. Pico | `pesquisar_horarios_pico` | **FS `competitor_cache/`** (some no CR) | deve ser SB | migrar TTL 7d → `cache_popular_times` / `search_raw` |
| 3f. Planos | `_planos_precos_searchapi` | fraco | sim | `search_raw` google_light |
| 3g. IG | `get_or_fetch_ig_intel` | `competidor_intel_cache` | **sim** | OK (já padrão store) |
| 4. Dores | card + topics; Gemini só se flag | — | CPU | Gemini off default |
| Loop | `for c in incluidos: await _processar_um` | — | — | seq por design; N↓ via `MAX_ENRIQUECIMENTO` |

Cap: `MAX_ENRIQUECIMENTO` default **3** (Act-on jul/2026; era 6) → até 3× (reviews+pico+planos) em série.

## 3. Evidência ledger `6bb90ff7` (A3a frio)

| tool / sku | calls | R$ | Nota latência |
|---|---:|---:|---|
| `descobrir_concorrentes_bairro` / `places_search_new` | 7 | 1,21 | dual-SKU ainda |
| `obter_atributos_place` / `places_details_new` | **6** | 0,65 | 1× por conc. enrich |
| reviews SearchAPI | 6 | 0,13 | frio |
| popular_times SearchAPI | 6 | 0,13 | FS cache inútil no CR |
| planos google_light | 6 | 0,13 | frio |

Soma API barata ≠ 1844s: tempo = **I/O seq + timeouts** (httpx 45s reviews, pico tiers, site scrape IG).

## 4. Princípios store (igual bundle v2)

1. **Batch / 1ª hit** grava por `place_id`; relatório seguinte **só carrega**.
2. **Não** meter reviews no `market_bundles` payload (chave errada = bairro).
3. Cloud Run: **proibir FS-only** pra pico/reviews — Supabase (`cache_*` / `search_raw`).
4. SearchAPI-primário; Places Details só miss de contato.
5. Agente A3a permanece determinístico zero-LLM.

## 5. Alvo latência

| Cenário | A3a s | Nota |
|---|---:|---|
| Baseline `ed36` | 834 | PW on |
| Retest `6bb90ff7` (PW off, cache frio) | **1844** | pior |
| Alvo cache quente + MAX=3 + details skip | **&lt;250** | SPEC_market_bundle_v2 |
| Alvo absoluto produto | **&lt;180** | stepper honesto |

## 6. Critérios de aceite

- [x] `popular_times` hit Supabase no worker (não só `competitor_cache/` local) — `_load_pico_cache` / `_save_pico_cache`
- [ ] 2º relatório mesma praça: `reviews_concorrente` calls ≈ 0 (só hit)
- [x] `obter_atributos_place` skip se listing já tem telefone/website (`A3A_FETCH_ATRIBUTOS=1` força)
- [x] `MAX_ENRIQUECIMENTO` default **3** (código + `.env.production.example`)
- [ ] Dual-SKU `descobrir_concorrentes` sem Places quando SearchAPI `[]` (mesmo padrão Maps Act-on)
- [ ] Diagrama `.mmd` + 5 Whys atualizados

## 7. Fora de escopo

- A3b análise agregada
- Redesign A6
- Voltar Playwright KP ao hot-path
