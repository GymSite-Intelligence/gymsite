# A1 listing + MRLR + Top3 rank — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o A1 morto (POI) por candidatos de listing SearchAPI filtrados + MRLR, e rankear Top3 no A6 por geo+payback — tapa a lacuna sem reintroduzir alucinação.

**Architecture:** A1 BaseAgent chama só `buscar_candidatos_cascata`, aplica gate cidade/UF + área real, score por distância ao centróide do bairro, anexa MRLR. A6 usa módulo puro `candidato_viabilidade_rank` (spec Top3). Macro POI permanece fora do caminho.

**Tech Stack:** Python 3.11+, ADK BaseAgent, SearchAPI (`listing_cascata`), Supabase MRLR (`aluguel_mrlr`), pytest (`-q --tb=short -x`).

**Specs:**  
- `docs/superpowers/specs/2026-08-05-a1-listing-mrlr-design.md`  
- `docs/superpowers/specs/2026-08-04-top3-viabilidade-rank-design.md`

**Execution status (2026-08-05):** Tasks 1–7 implemented and verified. No commit created (not requested).

## Global Constraints

- Aluguel de decisão = **só** `aluguel_deterministico` (MRLR Tier 0) — nunca `price_raw`
- `analisar_pontos_comerciais_completo` **não** no happy path A1 / L1 chat
- Proibido `score_geoscout = 8.5` hardcoded
- Todo número exibido: carimbo valor · base · fonte · janela/área
- Verifier: `…\python.exe -m pytest <path> -q --tb=short -x` (exit 0 = ok)
- Commits só se Marcelo pedir

## File map

| File | Role |
|------|------|
| `tools/listing_candidato_normalize.py` (**novo**) | cascata row → candidato A1 + gate cidade/UF + score distância |
| `tools/candidato_viabilidade_rank.py` (**novo**) | payback_est, norms, rank composto (spec Top3) |
| `agents/a1_geoscout.py` | stub → fetch cascata + normalize + MRLR |
| `agents_site/tools_l1_dados.py` | `buscar_pontos_comerciais` → mesma lógica A1 (ou chama helper) |
| `agents/a6_report_consolidator.py` | Top3 via rank module; MD enriched |
| `tests/test_a1.py` | gate Steinberger: listing path / sem macro POI |
| `tests/tools/test_listing_candidato_normalize.py` | TDD gate + score |
| `tests/tools/test_candidato_viabilidade_rank.py` | TDD fórmulas Top3 |
| `docs/arquitetura/PIPELINE_AGENTES.md` | A1/A6 atualizado |
| `tests/agents/test_a1_pirapora_pontos_indeterminado.py` | manter evidência macro morta; **novo** teste listing Pirapora (integration) |

---

### Task 1: Normalize listing → candidato (TDD)

**Files:**
- Create: `tests/tools/test_listing_candidato_normalize.py`
- Create: `tools/listing_candidato_normalize.py`

- [ ] **Step 1: Write failing tests**

```python
def test_drop_fora_da_cidade():
    rows = [{"area_m2": 800, "endereco": "Centro, Diadema - SP", "url": "u", "titulo": "x"}]
    out = normalizar_listings(rows, cidade="Pirapora", uf="MG", bairro="Centro",
                              lat0=-17.35, lng0=-44.94)
    assert out == []

def test_score_distancia_zero_no_centroide():
    rows = [{"area_m2": 900, "endereco": "Centro, Pirapora - MG",
             "latitude": -17.35, "longitude": -44.94, "url": "u", "titulo": "Galpão"}]
    out = normalizar_listings(rows, cidade="Pirapora", uf="MG", bairro="Centro",
                              lat0=-17.35, lng0=-44.94)
    assert len(out) == 1
    assert out[0]["score_geoscout"] == 10.0
    assert out[0]["qualidade_sinal"] == "direto-listing-bairro"
    assert out[0].get("score_geoscout") != 8.5

def test_sem_area_drop():
    rows = [{"area_m2": None, "endereco": "Centro, Pirapora - MG", "url": "u", "titulo": "x"}]
    assert normalizar_listings(rows, cidade="Pirapora", uf="MG", bairro="Centro",
                               lat0=-17.35, lng0=-44.94) == []
```

- [ ] **Step 2: Run — expect fail**

```powershell
c:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/tools/test_listing_candidato_normalize.py -q --tb=short -x
```

- [ ] **Step 3: Implement `normalizar_listings` + `haversine` / gate UF**
  - Gate: `" - SP"` / cidade errada no endereço → drop; prefer match `uf` e `cidade` no endereço quando presente
  - `area_estimada_m2` = `area_m2` do listing (nome legado do schema A6)
  - Sem lat → `score_geoscout=0`, `geocoded=False`

- [ ] **Step 4: Run — expect pass**

- [ ] **Step 5: Commit** só se pedido

---

### Task 2: Rank viabilidade (TDD — spec Top3)

**Files:**
- Create: `tests/tools/test_candidato_viabilidade_rank.py`
- Create: `tools/candidato_viabilidade_rank.py`

- [ ] **Step 1: Failing tests** — limiares payback 12/48/999; composto 0.35/0.65; `price_raw` ignorado; ordenação

```python
def test_payback_norm_limites():
    assert score_payback_norm(12) == 1.0
    assert score_payback_norm(48) == 0.0
    assert score_payback_norm(999) == 0.0

def test_nunca_usa_price_raw(monkeypatch):
    # enrich com mock MRLR fixo; price_raw absurdo não muda aluguel_mrlr_mensal
    ...
```

- [ ] **Step 2: Run fail → implement → pass** (`-q --tb=short -x`)

---

### Task 3: A1 revive com cascata (gate Steinberger)

**Files:**
- Modify: `tests/test_a1.py` (novo contrato — permitido: mudança de produto, não “passar na marra”)
- Modify: `agents/a1_geoscout.py`
- Modify: `tools/test_a1_deterministico.py`

- [ ] **Step 1: Rewrite gate**

Contrato:
1. BaseAgent / sem model / name GeoScout  
2. **Não** chama `analisar_pontos_comerciais_completo`  
3. Chama helper de listing (mock) → grava 2 chaves  
4. `status` ∈ `ok` | `ok_vazio` (não `deprecated` no happy path listing)  
5. `qualidade_sinal` dos itens = `direto-listing-bairro` quando há candidatos  

- [ ] **Step 2: Run gate — fail**

```powershell
c:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/test_a1.py -q --tb=short -x
```

- [ ] **Step 3: Implement A1**

```text
cidade,uf,bairro = _loc_do_state
geo = geocode_endereco(f"{bairro}, {cidade}, {uf}, Brasil")  # + MAPS_FALLBACK ok
cascata = buscar_candidatos_cascata(cidade, bairro, uf, area_min, area_max)
cands = normalizar_listings(..., lat0, lng0)
cands = anexar_mrlr(cands, cidade, bairro)  # extrair de anchoring ou reusar _anexar_aluguel_mrlr
payload = {status, total_candidatos, candidatos, aviso?, fonte: "listing_cascata+mrlr"}
state_delta ambas chaves
```

area_min/max de `input_params` (defaults 500–5000 como hoje).

- [ ] **Step 4: Gate verde**

- [ ] **Step 5: Update** `.cursor/skills/steinberger-pipeline-loop/prompts/a1.md` + progress

---

### Task 4: L1 chat alinha com A1

**Files:**
- Modify: `agents_site/tools_l1_dados.py` (`buscar_pontos_comerciais`)
- Create/modify: `tests/agents_site/test_buscar_pontos_listing.py` (mock cascata)

- [ ] **Step 1: Test** — não chama macro POI; retorna shape listing ou `ok_vazio` + `aviso_usuario`
- [ ] **Step 2: Implement** — `asyncio.to_thread` no mesmo helper que A1 usa (DRY: `tools/a1_listing_pipeline.py` opcional se A1+L1 duplicarem >15 linhas)
- [ ] **Step 3: pytest** `-q --tb=short -x`

---

### Task 5: A6 Top3 enriched

**Files:**
- Modify: `agents/a6_report_consolidator.py` (`_rank_candidatos_for_top3`, MD Top3)
- Create: `tests/tools/test_a6_top3_mrlr_md.py` (ou em `tools/test_a6_*.py` existente)

- [ ] **Step 1: Test** — com A4 mid mock + 2 candidatos, MD contém `payback_est` / `MRLR` / `score_composto`; sem tabela só-score
- [ ] **Step 2: Wire** `rank_candidatos_viabilidade(...)` no consolidator
- [ ] **Step 3: Fallback** — A4 ausente → Top3 geo + banner “viabilidade indisponível” (spec)
- [ ] **Step 4: pytest** focado

---

### Task 6: Docs + evidência Pirapora listing

**Files:**
- Modify: `docs/arquitetura/PIPELINE_AGENTES.md` (A1 = listing+MRLR; A6 = rank)
- Create: `tests/agents/test_a1_pirapora_listing_integration.py` (`@pytest.mark.integration`)

- [ ] **Step 1: Integration Pirapora**

```text
A1 path (ou helper) Centro/Pirapora/MG
assert: nenhum endereço com cidade ≠ Pirapora (se len>0)
assert: status ok|ok_vazio
assert: macro POI não necessária
# se SEARCHAPI vazio → ok_vazio aceitável (não falha suite)
```

- [ ] **Step 2: Manter** `test_a1_pirapora_pontos_indeterminado.py` como prova da macro morta (chama macro direto)
- [ ] **Step 3: PIPELINE** §A1/A6 + state keys

---

### Task 7: Verifier suite fechada

- [ ] **Step 1: Rodar**

```powershell
c:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe -m pytest `
  tests/test_a1.py `
  tests/tools/test_listing_candidato_normalize.py `
  tests/tools/test_candidato_viabilidade_rank.py `
  tools/test_a1_deterministico.py `
  -q --tb=short -x
```

- [ ] **Step 2: Exit 0** → marcar progress A1 listing complete; só então A2 gate  
- [ ] **Step 3: Commit** se Marcelo pedir

---

## Ordem / risco

```
T1 normalize → T2 rank → T3 A1 gate → T4 L1 → T5 A6 → T6 docs/Pirapora → T7 suite
```

**Risco:** SearchAPI vazio em praça pequena → relatório sem Top3 (honesto). Aceitável vs Diadema falso.  
**Risco:** MRLR precisa `renda_bairro` resolvível — já regra canônica site_agent.

## Aceite produto (Marcelo)

Exemplo: relatório Pirapora Centro — ou **0 candidatos** com aviso claro, ou **só imóveis** com área do anúncio + aluguel MRLR + payback_est no Top3 — nunca supermercado de SP com 600 m² inventado.
