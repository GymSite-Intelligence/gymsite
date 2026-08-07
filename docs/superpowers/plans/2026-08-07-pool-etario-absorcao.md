# Pool Etário Absorção — Implementation Plan (W2a.1 + W2a.2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Absorção `pool = pop × pen_acad` with two-rate pools over age stock (form primary / rest secondary / total 15+), rótulo on primary only, PDF three-pool rows + `gerar_html` preview.

**Architecture:** Extend `tools/absorcao_margem_fresca.py` with faixa mapping + pool layers. Attach pulls pirâmide from `demografia_bairro` and idade_min/max from `input_params` / params. PDF context maps new fields. No Matriz/Voronoi changes.

**Tech Stack:** Python 3.11+, pytest, `param()`, A9 attach, `pdf/html_builder.py` `gerar_html`.

**Spec:** `docs/superpowers/specs/2026-08-07-pool-etario-absorcao-design.md`

## Global Constraints

- Pool ≠ 100% of Core (18.420); always `estoque × interesse × pen_acad`
- `interesse = param("penetracao_potencial_fitness")` (0.40)
- `pen_acad = penetracao_geral | penetracao_bairro_ab` (same A/B rule as today)
- Rótulo / `margem_fresca` use **`pool_primario` only**
- Faixas IBGE: `15-24`, `25-39`, `40-59`, `60+`
- Form default 25–40 → primario `25-39` + `40-59`
- Fallback sem pirâmide: `pop_total × interesse × pen_acad` + carimbo `fallback_pop_total`
- Preview PDF = **`gerar_html`** + **abrir browser** (`.agent/rules/preview-aprovacao.md`)
- Verifier: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Commits **só se Marcelo pedir**
- Ler `.agent/rules/conferencia-fontes-pipeline.md` antes de docs

---

## File map

| File | Role |
|------|------|
| `tools/absorcao_margem_fresca.py` | Map faixas + três pools + attach |
| `tools/test_absorcao_margem_fresca.py` | TDD (extend) |
| `pdf/html_builder.py` | Linhas pool primário/secundário/total + nota |
| `pdf/test_absorcao_html.py` | Assert três pools |
| `.agent/rules/conferencia-fontes-pipeline.md` | §9.2 delta |
| `docs/arquitetura/PIPELINE_AGENTES.md` | Uma linha |
| `docs/superpowers/previews/2026-08-07-absorcao-w2a.html` | Regenerar via `gerar_html` |

---

### Task 1: Map form ages → faixas IBGE

**Files:**
- Modify: `tools/absorcao_margem_fresca.py`
- Modify: `tools/test_absorcao_margem_fresca.py`

**Interfaces:**
- Produces:
  - `FAIXAS_IBGE_15MAIS = ("15-24", "25-39", "40-59", "60+")`
  - `FAIXA_BOUNDS = {"15-24": (15,24), "25-39": (25,39), "40-59": (40,59), "60+": (60,120)}`
  - `faixas_primario_from_idade(idade_min: int, idade_max: int) -> list[str]`
  - `faixas_secundario_from_primario(primario: list[str]) -> list[str]`

- [ ] **Step 1: Failing tests**

```python
from tools.absorcao_margem_fresca import (
    faixas_primario_from_idade,
    faixas_secundario_from_primario,
)

def test_form_25_40_maps_core_and_maduro():
    p = faixas_primario_from_idade(25, 40)
    assert p == ["25-39", "40-59"]
    assert faixas_secundario_from_primario(p) == ["15-24", "60+"]

def test_form_25_39_core_only():
    p = faixas_primario_from_idade(25, 39)
    assert p == ["25-39"]
    assert "40-59" in faixas_secundario_from_primario(p)
```

- [ ] **Step 2: Run RED**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py::test_form_25_40_maps_core_and_maduro tools/test_absorcao_margem_fresca.py::test_form_25_39_core_only -q --tb=short -x
```

- [ ] **Step 3: Implement**

```python
FAIXAS_IBGE_15MAIS = ("15-24", "25-39", "40-59", "60+")
FAIXA_BOUNDS = {
    "15-24": (15, 24),
    "25-39": (25, 39),
    "40-59": (40, 59),
    "60+": (60, 120),
}

def faixas_primario_from_idade(idade_min: int, idade_max: int) -> list[str]:
    lo, hi = int(idade_min), int(idade_max)
    if hi < lo:
        lo, hi = hi, lo
    out: list[str] = []
    for f in FAIXAS_IBGE_15MAIS:
        a, b = FAIXA_BOUNDS[f]
        if lo <= b and hi >= a:
            out.append(f)
    return out

def faixas_secundario_from_primario(primario: list[str]) -> list[str]:
    s = set(primario)
    return [f for f in FAIXAS_IBGE_15MAIS if f not in s]
```

- [ ] **Step 4: GREEN** same pytest commands

- [ ] **Step 5: Commit** — só se Marcelo pedir

---

### Task 2: Três pools + rótulo no primário

**Files:**
- Modify: `tools/absorcao_margem_fresca.py` (`absorcao_margem_fresca` signature + body)
- Modify: `tools/test_absorcao_margem_fresca.py`

**Interfaces:**
- Consumes: Task 1 helpers; `param("penetracao_potencial_fitness")`
- New kwargs on `absorcao_margem_fresca`:
  - `segmentos: dict[str, dict] | None = None`  # faixa → {total: int}
  - `idade_min: int | None = None`
  - `idade_max: int | None = None`
- Produces: fields from spec §4; `pool_demografico == pool_primario`

- [ ] **Step 1: Failing golden (spec exemplo A/B)**

```python
def test_pool_duas_camadas_tres_bases():
    from tools.absorcao_margem_fresca import absorcao_margem_fresca
    from tools.parametros_metodologia import param

    segs = {
        "15-24": {"total": 7850},
        "25-39": {"total": 18420},
        "40-59": {"total": 12100},
        "60+": {"total": 8200},
    }
    out = absorcao_margem_fresca(
        concorrentes=[],
        pop_poligono=60165,
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=True,  # pen 0.10
        segmentos=segs,
        idade_min=25,
        idade_max=40,
        fonte_espacial="poligono_ibge",
    )
    interesse = param("penetracao_potencial_fitness")
    pen = param("penetracao_bairro_ab")
    assert out["faixas_primario"] == ["25-39", "40-59"]
    assert out["estoque_primario"] == 30520
    assert out["estoque_secundario"] == 16050
    assert out["pool_primario"] == int(round(30520 * interesse * pen))
    assert out["pool_secundario"] == int(round(16050 * interesse * pen))
    assert out["pool_total_15mais"] == int(round(46570 * interesse * pen))
    assert out["pool_demografico"] == out["pool_primario"]
    assert out["interesse_fitness"] == interesse
    # cap=0 → margem = pool_primario ≥ teto → fresco
    assert out["rotulo"] == "fresco"
    assert out["margem_fresca"] == out["pool_primario"]


def test_fallback_sem_piramide():
    from tools.absorcao_margem_fresca import absorcao_margem_fresca
    from tools.parametros_metodologia import param

    out = absorcao_margem_fresca(
        concorrentes=[],
        pop_poligono=100_000,
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=False,
        segmentos=None,
    )
    interesse = param("penetracao_potencial_fitness")
    pen = param("penetracao_geral")
    assert out["pool_primario"] == int(round(100_000 * interesse * pen))
    assert "fallback_pop_total" in out["carimbos"]["pool_demografico"]
```

Update existing `test_golden_spec_example_mid` / `test_rotulo_*` if they assumed `pool = pop * pen` only — recompute expected pools **or** pass `segmentos=None` and expect new fallback formula (`pop × interesse × pen`).

- [ ] **Step 2: RED**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py -q --tb=short -x
```

- [ ] **Step 3: Implement pool body** (replace `pool = pop * pen`):

```python
    interesse = float(param("penetracao_potencial_fitness"))
    pen, pen_key = _penetracao_efetiva(renda_pc, perfil_ab)
    imin = int(idade_min if idade_min is not None else param("publico_fitness_idade_min"))
    imax = int(idade_max if idade_max is not None else param("publico_fitness_idade_max"))

    if isinstance(segmentos, dict) and segmentos:
        prim = faixas_primario_from_idade(imin, imax)
        sec = faixas_secundario_from_primario(prim)
        def _tot(fs):
            s = 0
            for f in fs:
                cell = segmentos.get(f) or {}
                s += int(cell.get("total") or 0)
            return s
        est_p, est_s = _tot(prim), _tot(sec)
        pool_p = int(round(est_p * interesse * pen))
        pool_s = int(round(est_s * interesse * pen))
        pool_t = int(round((est_p + est_s) * interesse * pen))
        pool_stamp_base = f"estoque_form×interesse×{pen_key}"
        fallback = False
    else:
        prim, sec = faixas_primario_from_idade(imin, imax), []
        est_p = int(pop_poligono or 0)
        est_s = 0
        pool_p = int(round(est_p * interesse * pen))
        pool_s, pool_t = 0, pool_p
        pool_stamp_base = "fallback_pop_total"
        fallback = True

    # margem / rótulo usam pool_p
    margem = pool_p - cap_i
    ...
    # return includes pool_* , estoque_* , faixas_* , interesse_fitness,
    # pool_demografico=pool_p, nota_modelo_secundario=...
```

`nota_modelo_secundario` example:

```python
"Faixas fora do formulário (ex. Jovem/Silver) têm pool secundário — informam modelo, não o rótulo fresco/roubo."
```

- [ ] **Step 4: GREEN** full `tools/test_absorcao_margem_fresca.py`

- [ ] **Step 5: Commit** — só se Marcelo pedir

---

### Task 3: Attach lê pirâmide + idades form

**Files:**
- Modify: `attach_absorcao_margem_fresca` in `tools/absorcao_margem_fresca.py`
- Modify: `tools/test_absorcao_margem_fresca.py` (`test_attach_writes_parsed`)

**Interfaces:**
- From `demografia_bairro.perfil_idade_sexo_bairro.segmentos` (or equivalent path used by PDF)
- From `state["input_params"]` keys `idade_min` / `idade_max` / `publico_fitness_idade_*` if present; else params

- [ ] **Step 1: Extend attach test** with segmentos in demografia → `pool_primario` ≠ `pop × pen` only

- [ ] **Step 2: Implement extract** in attach; pass into `absorcao_margem_fresca`

- [ ] **Step 3: GREEN**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py -q --tb=short -x
```

---

### Task 4: Docs §9.2 + PIPELINE

**Files:**
- Modify: `.agent/rules/conferencia-fontes-pipeline.md` §9.2
- Modify: `docs/arquitetura/PIPELINE_AGENTES.md` (A9 Absorção bullet)

- [ ] **Step 1:** Add: pool = estoque×interesse×pen_acad; três pools; rótulo no primário; Core ≠ 100% ativo

- [ ] **Step 2:** Commit — só se Marcelo pedir

---

### Task 5: PDF + preview `gerar_html` + abrir

**Files:**
- Modify: `pdf/html_builder.py` (template Absorção + ctx)
- Modify: `pdf/test_absorcao_html.py`
- Regenerate: `docs/superpowers/previews/2026-08-07-absorcao-w2a.html`

- [ ] **Step 1: Failing test** — HTML contains "Pool primário", "Pool secundário", "Pool total"

- [ ] **Step 2: Template rows**

```html
  <tr><td>Pool primário (form × interesse × pen.)</td><td><strong>{{ absorcao.pool_primario }}</strong></td></tr>
  <tr><td>Pool secundário (outras faixas 15+)</td><td>{{ absorcao.pool_secundario }}</td></tr>
  <tr><td>Pool total 15+</td><td>{{ absorcao.pool_total }}</td></tr>
```

Keep margem/leitura; append `absorcao.nota` from `nota_modelo_secundario` if set.

- [ ] **Step 3: Context** map `pool_primario`, `pool_secundario`, `pool_total_15mais` → template keys

- [ ] **Step 4: GREEN** `pdf/test_absorcao_html.py` + absorcao tests

- [ ] **Step 5: Regenerate preview** via `gerar_html` with Cocó segmentos + form 25–40 + Armadilha/roubo coerente (não Oceano Azul se margem negativa)

- [ ] **Step 6: `Start-Process` preview HTML** (obrigatório)

- [ ] **Step 7: Commit** — só se Marcelo pedir

---

## Self-review (plan vs spec)

| Spec | Task |
|---|---|
| Duas camadas × três pools | T2 |
| Map form→faixas | T1 |
| Rótulo no primário | T2 |
| Fallback | T2 |
| Attach pirâmide/form | T3 |
| Docs | T4 |
| PDF + gerar_html + abrir | T5 |
| Não 100% Core | T2 assert |

---

## Execution handoff

Plan: `docs/superpowers/plans/2026-08-07-pool-etario-absorcao.md`

**1. Subagent-Driven** (recomendado)  
**2. Inline** (se quota subagent falhar)

Which approach?
