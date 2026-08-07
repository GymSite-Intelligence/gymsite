# Matriz Demo × Saturação → Modelo Adequado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deterministic quadrant (Oceano Azul / Armadilha / Guerra / Deserto) from A2 demography × A3 mix on the same spatial base, with A9/PDF copy and A4 Premium veto on Armadilha.

**Architecture:** Pure compute in `tools/matriz_demo_saturacao.py`. A9 attaches result to positioning state. PDF renders a short section. A4 reads `quadrante` when choosing `modelo_recomendado`. W3 only adds CNPJ modifiers.

**Tech Stack:** Python 3.11+, pytest, `param()` / `parametros_metodologia`, Jinja PDF, existing A3/A9/A4 wiring.

**Spec:** `docs/superpowers/specs/2026-08-07-matriz-demo-saturacao-modelo-design.md`

## Global Constraints

- Matriz **não** vive em A0/A2 — só `tools/matriz_demo_saturacao.py`
- Precedência: **Armadilha vence** headroom `OCEANO_AZUL` se `mix.premium ≥ matriz_premium_min_armadilha`
- Spatial: prefer Spec C polígono (`gate_espacial=poligono_ibge_bairro` / ring); else `fonte_espacial=raio_fallback`
- Números = tool; LLM só veste
- Limiares só via `param()` (valores seed abaixo)
- Verifier: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Commits **só se Marcelo pedir**
- Preview: `docs/superpowers/previews/` antes de ok humano
- Conferência: `.agent/rules/conferencia-fontes-pipeline.md` + `pipeline-fontes-deterministicas.md`

### Param seeds (W1 — gravar em `parametros_metodologia.py`)

| Key | Value | Meaning |
|---|---|---|
| `matriz_n_per_10k_baixo` | `2.0` | N/10k &lt; isto → densidade competitiva baixa |
| `matriz_n_per_10k_alto` | `4.0` | N/10k ≥ isto → saturação geral / guerra |
| `matriz_premium_min_armadilha` | `2` | ≥2 Premium no polígono + alta renda → Armadilha |
| `matriz_rating_fraco_max` | `4.0` | rating médio &lt; isto conta como “oferta fraca” (Oceano mesmo com N&gt;0) |
| `matriz_ticket_low_max` | `150.0` | ticket ≤ → low |
| `matriz_ticket_premium_min` | `250.0` | ticket ≥ → premium (se não rede known) |
| `matriz_renda_alta_percentil` | `0.75` | = `renda_percentil_premium` (reuse se já no state; senão proxy renda_pc) |
| `matriz_renda_pc_alta_min` | `3500.0` | fallback se sem percentil |

### Redes known (tier fixo)

```python
REDES_TIER = {
    "smart fit": "low", "smartfit": "low", "selfit": "low", "bluefit": "low",
    "blue fit": "low", "skyfit": "low", "sky fit": "low",
    "bodytech": "premium", "body tech": "premium", "bio ritmo": "premium",
    "bioritmo": "premium", "cia athletica": "premium", "competition": "premium",
}
```

---

## File map

| File | Role |
|------|------|
| `tools/matriz_demo_saturacao.py` | Compute + tier + quadrante |
| `tools/test_matriz_demo_saturacao.py` | TDD W1 |
| `tools/parametros_metodologia.py` | Param seeds |
| `agents/a9_positioning_strategist.py` | Attach matriz to parsed/state |
| `pdf/html_builder.py` | Seção Modelo Adequado |
| `pdf/test_matriz_modelo_html.py` | Assert seção / Armadilha copy |
| `docs/superpowers/previews/2026-08-07-matriz-w1.html` | Preview |
| `docs/arquitetura/PIPELINE_AGENTES.md` | A9/A4 bullets |
| `.agent/rules/conferencia-fontes-pipeline.md` | Fonte matriz |
| `tools/financial_tools.py` (W2) | Veto premium |
| `tools/test_a4_matriz_veto.py` (W2) | TDD veto |
| `tools/matriz_demo_saturacao.py` (W3) | Modifiers CNPJ |

---

# Wave 1 — Matriz + A9/PDF

### Task 1: Params + `classificar_tier_concorrente` + mix

**Files:**
- Create: `tools/matriz_demo_saturacao.py`
- Create: `tools/test_matriz_demo_saturacao.py`
- Modify: `tools/parametros_metodologia.py` (seed keys above)

**Interfaces:**
- Produces:
  - `classificar_tier_concorrente(c: dict) -> Literal["low","mid","premium","nicho","desconhecido"]`
  - `contar_mix(concorrentes: list[dict]) -> dict[str,int]`
- Consumes: nome/title, `ticket_medio` / `planos_precos`, `tipos`

- [ ] **Step 1: Add params** to `_SEED` / register path used by project (same pattern as `saturacao_bairro_*`).

- [ ] **Step 2: Failing tests**

```python
# tools/test_matriz_demo_saturacao.py
from tools.matriz_demo_saturacao import classificar_tier_concorrente, contar_mix

def test_smart_fit_is_low():
    assert classificar_tier_concorrente({"nome": "Smart Fit Cocó"}) == "low"

def test_bodytech_is_premium():
    assert classificar_tier_concorrente({"nome": "Bodytech Aldeota"}) == "premium"

def test_ticket_mid_band():
    assert classificar_tier_concorrente({"nome": "Academia X", "ticket_medio": 189}) == "mid"

def test_contar_mix():
    cs = [
        {"nome": "Smart Fit"},
        {"nome": "Bodytech"},
        {"nome": "Bodytech 2"},
        {"nome": "Local", "ticket_medio": 180},
    ]
    m = contar_mix(cs)
    assert m["low"] == 1 and m["premium"] == 2 and m["mid"] == 1
```

- [ ] **Step 3: Run — FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_matriz_demo_saturacao.py -q --tb=short -x
```

- [ ] **Step 4: Implement** tier + mix (fold nome via `normalizar_bairro` / `fold_texto`).

- [ ] **Step 5: Run — PASS**

---

### Task 2: `n_per_10k` + `classificar_quadrante` + `matriz_demo_saturacao`

**Files:**
- Modify: `tools/matriz_demo_saturacao.py`
- Modify: `tools/test_matriz_demo_saturacao.py`

**Interfaces:**
- Produces:

```python
def matriz_demo_saturacao(
    *,
    populacao: int | None,
    renda_pc: float | None = None,
    renda_percentil: float | None = None,
    concorrentes: list[dict] | None = None,
    censo_base: str | None = None,
    fonte_espacial: str | None = None,  # poligono_ibge_bairro | raio_fallback
    baixas_24m: int | None = None,  # W3; ignore if None
    rede_ancora: bool | None = None,  # W3
) -> dict: ...
```

Return keys exactly as spec: `quadrante`, `modelo_sugerido`, `n_poligono`, `n_per_10k`, `mix`, `rating_medio`, `censo_base`, `fonte_espacial`, `acao_estrategica`, `carimbo`.

**Quadrante logic (implement verbatim):**

1. `n = len(concorrentes)`; `n_per_10k = n / (pop/10000)` if pop&gt;0 else `None`
2. `alta_renda = (percentil >= param(matriz_renda_alta_percentil)) or (renda_pc >= param(matriz_renda_pc_alta_min))`
3. If `alta_renda` and `mix["premium"] >= param(matriz_premium_min_armadilha)` → **Armadilha de Renda** / modelo `nicho_ou_mid_high`
4. Elif `alta_renda` and (`n_per_10k` is None or `n_per_10k < baixo` or (`mix["premium"]==0` and rating_medio &lt; fraco)) → **Oceano Azul** / `premium_ou_mid_high`
5. Elif (not alta_renda) and `mix["low"] >= max(2, n//2)` and `n_per_10k >= alto` → **Guerra de Preço** / `low_ou_nicho`
6. Else → **Deserto Viável** / `teste_leve` (inclui N baixo + demo fraca)

- [ ] **Step 1: Failing tests**

```python
def test_oceano_azul_alta_renda_sem_premium():
    r = matriz_demo_saturacao(
        populacao=50000, renda_percentil=0.9,
        concorrentes=[{"nome": "Smart Fit", "rating": 3.5}],
        fonte_espacial="poligono_ibge_bairro",
    )
    assert r["quadrante"] == "Oceano Azul"
    assert "premium" in r["modelo_sugerido"].lower() or "mid" in r["modelo_sugerido"].lower()

def test_armadilha_dois_premium():
    r = matriz_demo_saturacao(
        populacao=50000, renda_percentil=0.9,
        concorrentes=[{"nome": "Bodytech"}, {"nome": "Bio Ritmo"}, {"nome": "Smart Fit"}],
        fonte_espacial="poligono_ibge_bairro",
    )
    assert r["quadrante"] == "Armadilha de Renda"
    assert "premium" not in r["modelo_sugerido"].lower() or "nicho" in r["modelo_sugerido"].lower()

def test_n_per_10k():
    r = matriz_demo_saturacao(
        populacao=10000, renda_pc=2000,
        concorrentes=[{"nome": "A"}, {"nome": "B"}],
    )
    assert r["n_per_10k"] == 2.0
```

- [ ] **Step 2: Run — FAIL → implement → PASS**

---

### Task 3: Wire A9 state

**Files:**
- Modify: `agents/a9_positioning_strategist.py` (where demografia + concorrentes already available — near `_a9_override_veredito_deterministico` / build parsed)
- Create: `tools/test_a9_matriz_attach.py` (unit with fake state, no LLM)

**Interfaces:**
- Consumes: `state["demografia_bairro"]` or meta; `concorrentes_brutos` / `inteligencia_competitiva.concorrentes_detalhados`
- Produces: `parsed["matriz_demo_saturacao"] = matriz_demo_saturacao(...)`
- If Armadilha and veredito would be OCEANO_AZUL → set `parsed["matriz_override"]=True` and keep/adjust note (do **not** force VERMELHO blindly — document: veredito legado may stay; seção matriz manda)

Filter concorrentes: prefer those with `gate_espacial=="poligono_ibge_bairro"`; else all list + `fonte_espacial=raio_fallback`.

- [ ] **Step 1: Test** attach returns Armadilha key on rich+2 premium fixture state.

- [ ] **Step 2: Implement hook** after demografia/competitors present.

- [ ] **Step 3: pytest PASS**

---

### Task 4: PDF section + preview

**Files:**
- Modify: `pdf/html_builder.py` — new `{% if matriz %}` block (after demografia / before ERRC or near posicionamento)
- Create: `pdf/test_matriz_modelo_html.py`
- Create: `docs/superpowers/previews/2026-08-07-matriz-w1.html`

**Copy (template):**

- Title: `Modelo de Negócio Adequado`
- Rows: Quadrante · Modelo sugerido · N no polígono · N/10k · Mix (L/M/P) · Rating médio · Ação
- Note: carimbo `fonte_espacial` + `censo_base`

- [ ] **Step 1: Test** `_contexto` with metadata.matriz → HTML contains “Armadilha” / “Modelo de Negócio Adequado”

- [ ] **Step 2: Implement** context extraction from `model.posicionamento_estrategico` or `metadata`

- [ ] **Step 3: Preview** — open for Marcelo OK

```bash
Start-Process "c:\Users\marce\gymsite\docs\superpowers\previews\2026-08-07-matriz-w1.html"
```

---

### Task 5: Docs W1

**Files:**
- Modify: `docs/arquitetura/PIPELINE_AGENTES.md` (A9 + tabela fontes)
- Modify: `.agent/rules/conferencia-fontes-pipeline.md` (nova § matriz)

- [ ] Document: modelo narrado = matriz; aluguel continua MRLR; Maps gate Spec C

---

# Wave 2 — Veto A4

### Task 6: Armadilha blocks generic premium recommendation

**Files:**
- Modify: `tools/financial_tools.py` (where `escolhido` / `modelo_recomendado` finalized — near justificativa ~L996–1061)
- Create: `tools/test_a4_matriz_veto.py`

**Interfaces:**
- Consumes: optional `matriz_demo_saturacao` dict passed into analise financeira payload / state key
- If `quadrante == "Armadilha de Renda"` and escolhido is premium → pick best non-premium viable mid (or low); set  
  `justificativa_matriz = "Armadilha de Renda: ≥2 Premium no polígono — Premium genérico vetado pela matriz."`

- [ ] **Step 1: Failing test** — mock cenarios with premium best by payback + matriz Armadilha → result modelo_key ≠ premium

- [ ] **Step 2: Implement → PASS**

---

# Wave 3 — A0 CNPJ modifiers

### Task 7: `baixas_24m` / `rede_ancora` modifiers

**Files:**
- Modify: `tools/matriz_demo_saturacao.py`
- Modify: `tools/test_matriz_demo_saturacao.py`
- Wire from A9: read `arvore_2x2` / market_context CNPJ metrics if present (no new A0 LLM)

**Rules:**
- If `baixas_24m >= 3` and N baixo → force note Deserto / `red_flag_rotatividade=True` (quadrante Deserto if not Armadilha)
- If `rede_ancora` and alta_renda → bump toward Armadilha only if premium count ≥ 1 (âncora nacional conta como pressão)

- [ ] Tests for modifiers
- [ ] Docs one-liner in conferencia

---

## Spec coverage

| Spec | Task |
|---|---|
| `matriz_demo_saturacao` compute | T1–T2 |
| 4 quadrantes + Armadilha precedence | T2 |
| A9 attach + override flag | T3 |
| PDF / preview | T4 |
| Docs | T5 |
| A4 veto | T6 |
| A0 CNPJ modifiers | T7 |
| Fora SOV/churn/canibalização | não no plano |

## Placeholder scan

Limiares travados na tabela Global Constraints. Sem TBD.

---

## Execution

Plan: `docs/superpowers/plans/2026-08-07-matriz-demo-saturacao-modelo.md`

**1. Subagent-Driven** (recomendado) · **2. Inline**

Which?
