# Absorção / Margem Fresca — Implementation Plan (W2a + W2b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deterministic `absorcao_margem_fresca` block: teto operacional × capacidade do parque por tier × pool demográfico → rótulo `fresco|misto|roubo`, attached by A9 and shown in PDF.

**Architecture:** Pure compute in `tools/absorcao_margem_fresca.py` (reuses `contar_mix` from Matriz). A9 attaches next to Matriz. PDF renders a short section after Demografia / before or after Modelo Adequado. No Voronoi in this plan (W2.1).

**Tech Stack:** Python 3.11+, pytest, `param()` / `parametros_metodologia`, A9 state hook, Jinja PDF (`pdf/html_builder.py`).

**Spec:** `docs/superpowers/specs/2026-08-07-absorcao-margem-fresca-design.md`

## Global Constraints

- Absorção **não** vive dentro de `matriz_demo_saturacao.py` — módulo próprio
- Mix / tier = `tools.matriz_demo_saturacao.contar_mix` / `classificar_tier_concorrente` (não reinventar)
- Área proxy travada: Low **1000**, Mid **1500**, Premium **2000**, nicho/desc **1250**
- Matrículas = `matr_m2_{tier}_realista` via `param()`
- Penetração = `penetracao_bairro_ab` se perfil A/B; senão `penetracao_geral`
- Spatial W2a: `poligono_ibge` | `raio_fallback` only — **no Voronoi import/code**
- Números = tool; LLM só veste copy
- Verifier: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Commits **só se Marcelo pedir**
- Conferência: `.agent/rules/conferencia-fontes-pipeline.md` + `pipeline-fontes-deterministicas.md`
- Antes de tocar pipeline: ler `.agent/rules/conferencia-fontes-pipeline.md`

### Param seeds (gravar em `parametros_metodologia.py`)

| Key | Value | Fonte / meaning |
|---|---|---|
| `area_proxy_low_m2` | `1000.0` | Smart Fit mín ≥950 + Panobianco Padrão 900–1000 |
| `area_proxy_mid_m2` | `1500.0` | Ultra média ~1500 + Bluefit tip. |
| `area_proxy_premium_m2` | `2000.0` | Placeholder calibrável Bodytech/Cia |
| `area_proxy_nicho_desconhecido_m2` | `1250.0` | Meio-termo low↔mid |

Reuse existing (do **not** reseed): `matr_m2_*_realista`, `penetracao_geral`, `penetracao_bairro_ab`, `perfil_ab_renda_pc_min`, `perfil_ab_idh_renda_min`.

---

## File map

| File | Role |
|------|------|
| `tools/parametros_metodologia.py` | Area proxy seeds |
| `tools/absorcao_margem_fresca.py` | Compute + attach |
| `tools/test_absorcao_margem_fresca.py` | TDD golden + rótulos + proxies |
| `agents/a9_positioning_strategist.py` | Call `attach_absorcao_margem_fresca` after Matriz |
| `pdf/html_builder.py` | Seção Absorção + ctx |
| `pdf/test_absorcao_html.py` | Assert seção / carimbo |
| `docs/arquitetura/PIPELINE_AGENTES.md` | Bullet Absorção |
| `.agent/rules/conferencia-fontes-pipeline.md` | § Absorção |
| `docs/superpowers/previews/2026-08-07-absorcao-w2a.html` | Preview humano (opcional Task 5) |

**Out of this plan:** Voronoi (`tools/voronoi_atratividade.py`), W2c calibração premium, card React no app (pode seguir em PR separado se PDF fechar primeiro).

---

# Wave W2a — Core + A9 + docs

### Task 1: Params `area_proxy_*`

**Files:**
- Modify: `tools/parametros_metodologia.py` (junto aos params `matr_m2_*` / densidade)
- Test: `tools/test_absorcao_margem_fresca.py` (criado aqui; cresce nas tasks)

**Interfaces:**
- Produces: `param("area_proxy_low_m2")` → `1000.0` (idem mid/premium/nicho)

- [ ] **Step 1: Failing test — valores travados**

```python
# tools/test_absorcao_margem_fresca.py
from tools.parametros_metodologia import param

def test_area_proxy_seeds():
    assert param("area_proxy_low_m2") == 1000.0
    assert param("area_proxy_mid_m2") == 1500.0
    assert param("area_proxy_premium_m2") == 2000.0
    assert param("area_proxy_nicho_desconhecido_m2") == 1250.0
```

- [ ] **Step 2: Run — FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py::test_area_proxy_seeds -q --tb=short -x
```

Expected: FAIL (KeyError / missing param)

- [ ] **Step 3: Add seeds** next to `matr_m2_*` block:

```python
"area_proxy_low_m2": _p(1000.0, "Smart Fit mín franquia ≥950 + Panobianco Padrão 900-1000", "absorcao_area_proxy", "m2", "benchmark", "2026-08-07"),
"area_proxy_mid_m2": _p(1500.0, "Ultra média ~1500 + Bluefit tip.", "absorcao_area_proxy", "m2", "benchmark", "2026-08-07"),
"area_proxy_premium_m2": _p(2000.0, "placeholder Bodytech/Cia — calibrável W2c", "absorcao_area_proxy", "m2", "calibracao", "2026-08-07"),
"area_proxy_nicho_desconhecido_m2": _p(1250.0, "meio-termo low↔mid", "absorcao_area_proxy", "m2", "calibracao", "2026-08-07"),
```

- [ ] **Step 4: Run — PASS**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py::test_area_proxy_seeds -q --tb=short -x
```

- [ ] **Step 5: Commit** — só se Marcelo pedir

---

### Task 2: `absorcao_margem_fresca` — fórmula + rótulos (TDD)

**Files:**
- Create: `tools/absorcao_margem_fresca.py`
- Modify: `tools/test_absorcao_margem_fresca.py`

**Interfaces:**
- Consumes: `contar_mix` from `tools.matriz_demo_saturacao`; `param` for area_proxy + matr_m2_*_realista + penetração
- Produces:
  - `absorcao_margem_fresca(*, concorrentes, pop_poligono, area_candidato_m2, modelo_cenario, renda_pc=None, perfil_ab=None, fonte_espacial="raio_fallback", censo_base=None) -> dict`
  - Return keys per spec §5 (W2a: `base_espacial` ∈ `poligono_ibge` | `raio_fallback`)

- [ ] **Step 1: Failing golden (exemplo do spec)**

```python
from tools.absorcao_margem_fresca import absorcao_margem_fresca

def test_golden_spec_example_mid():
    """4 Low + 2 Mid + 1 Premium; unidade Mid 1500 m²; pop alta → teto/cap conhecidos."""
    cs = (
        [{"nome": "Smart Fit A"}, {"nome": "Smart Fit B"},
         {"nome": "Smart Fit C"}, {"nome": "Smart Fit D"}]
        + [{"nome": "Local Mid", "ticket_medio": 180}] * 2
        + [{"nome": "Bodytech X"}]
    )
    # Force pop so pool known: use penetracao_geral 0.045 → pool = int(100_000 * 0.045) = 4500
    out = absorcao_margem_fresca(
        concorrentes=cs,
        pop_poligono=100_000,
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=False,
        fonte_espacial="poligono_ibge",
    )
    assert out["teto_unidade"] == 2100  # 1500 * 1.4
    assert out["capacidade_parque_estimada"] == 14200  # 4*1000*2.2 + 2*1500*1.4 + 1*2000*0.6
    assert out["pool_demografico"] == 4500  # 100000 * 0.045
    assert out["margem_fresca"] == 4500 - 14200
    assert out["rotulo"] == "roubo"
    assert out["area_proxy_usada"]["low"] == 1000
    assert out["base_espacial"] in ("poligono_ibge", "raio_fallback")
    assert "voronoi" not in str(out["base_espacial"])


def test_rotulo_fresco():
    out = absorcao_margem_fresca(
        concorrentes=[],
        pop_poligono=100_000,
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=False,
        fonte_espacial="raio_fallback",
    )
    assert out["capacidade_parque_estimada"] == 0
    assert out["rotulo"] == "fresco"
    assert out["margem_fresca"] >= out["teto_unidade"]


def test_rotulo_misto():
    # 1 Low only → cap = 1000*2.2 = 2200; pool 4500; teto 2100 → margem 2300 >= teto → fresco
    # Need margem between 0 and teto: pool slightly above cap
    # cap 1*1000*2.2=2200; want pool=3000 → margem=800 < teto 2100 → misto
    out = absorcao_margem_fresca(
        concorrentes=[{"nome": "Smart Fit"}],
        pop_poligono=int(3000 / 0.045),  # pool ≈ 3000
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=False,
    )
    assert out["rotulo"] == "misto"


def test_nicho_uses_1250_x_mid():
    out = absorcao_margem_fresca(
        concorrentes=[{"nome": "Studio X", "tipos": ["pilates"]}],  # may land nicho/desconhecido
        pop_poligono=50_000,
        area_candidato_m2=800.0,
        modelo_cenario="mid",
        perfil_ab=False,
    )
    # If classified nicho or desconhecido: cap = 1250 * matr_m2_mid_realista
    from tools.matriz_demo_saturacao import classificar_tier_concorrente
    tier = classificar_tier_concorrente({"nome": "Studio X", "tipos": ["pilates"]})
    if tier in ("nicho", "desconhecido"):
        from tools.parametros_metodologia import param
        expected = int(1250 * param("matr_m2_mid_realista"))
        assert out["capacidade_parque_estimada"] == expected
```

- [ ] **Step 2: Run — FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py -q --tb=short -x
```

Expected: FAIL import / missing function

- [ ] **Step 3: Implement** `tools/absorcao_margem_fresca.py`

```python
"""Absorção / margem fresca — pool vs parque (proxy área×tier) vs teto unidade."""
from __future__ import annotations

from typing import Any, Literal

from tools.matriz_demo_saturacao import contar_mix
from tools.parametros_metodologia import param, param_meta

Modelo = Literal["low", "mid", "premium"]
Rotulo = Literal["fresco", "misto", "roubo"]


def _perfil_ab(renda_pc: float | None, perfil_ab: bool | None) -> bool:
    if perfil_ab is not None:
        return bool(perfil_ab)
    if renda_pc is None:
        return False
    return float(renda_pc) >= float(param("perfil_ab_renda_pc_min"))


def _penetracao_efetiva(renda_pc: float | None, perfil_ab: bool | None) -> tuple[float, str]:
    ab = _perfil_ab(renda_pc, perfil_ab)
    key = "penetracao_bairro_ab" if ab else "penetracao_geral"
    return float(param(key)), key


def _carimbo(valor: Any, base: str, fonte: str, janela: str = "n/a") -> str:
    return f"{valor} · {base} · {fonte} · {janela}"


def absorcao_margem_fresca(
    *,
    concorrentes: list[dict[str, Any]] | None,
    pop_poligono: int | float | None,
    area_candidato_m2: float,
    modelo_cenario: str,
    renda_pc: float | None = None,
    perfil_ab: bool | None = None,
    fonte_espacial: str = "raio_fallback",
    censo_base: str | None = None,
) -> dict[str, Any]:
    modelo = modelo_cenario if modelo_cenario in ("low", "mid", "premium") else "mid"
    mix = contar_mix(concorrentes)

    a_low = float(param("area_proxy_low_m2"))
    a_mid = float(param("area_proxy_mid_m2"))
    a_prem = float(param("area_proxy_premium_m2"))
    a_nd = float(param("area_proxy_nicho_desconhecido_m2"))

    m_low = float(param("matr_m2_low_realista"))
    m_mid = float(param("matr_m2_mid_realista"))
    m_prem = float(param("matr_m2_premium_realista"))

    cap = (
        mix.get("low", 0) * a_low * m_low
        + mix.get("mid", 0) * a_mid * m_mid
        + mix.get("premium", 0) * a_prem * m_prem
        + (mix.get("nicho", 0) + mix.get("desconhecido", 0)) * a_nd * m_mid
    )
    cap_i = int(round(cap))

    pen, pen_key = _penetracao_efetiva(renda_pc, perfil_ab)
    pop = int(pop_poligono or 0)
    pool = int(round(pop * pen))

    matr_modelo = float(param(f"matr_m2_{modelo}_realista"))
    teto = int(round(float(area_candidato_m2) * matr_modelo))

    margem = pool - cap_i
    if margem >= teto:
        rotulo: Rotulo = "fresco"
    elif margem > 0:
        rotulo = "misto"
    else:
        rotulo = "roubo"

    base_esp = "poligono_ibge" if fonte_espacial in (
        "poligono_ibge",
        "poligono_ibge_bairro",
    ) else "raio_fallback"

    return {
        "teto_unidade": teto,
        "modelo_teto": modelo,
        "area_candidato_m2": float(area_candidato_m2),
        "capacidade_parque_estimada": cap_i,
        "mix": mix,
        "pool_demografico": pool,
        "penetracao_efetiva": pen,
        "margem_fresca": margem,
        "rotulo": rotulo,
        "carimbos": {
            "teto_unidade": _carimbo(teto, f"{area_candidato_m2}m²×{matr_modelo}", f"matr_m2_{modelo}_realista", "ACAD/param"),
            "capacidade_parque_estimada": _carimbo(
                cap_i, "N×tier×área_proxy×matr/m²", "proxy franquia", "não medido"
            ),
            "pool_demografico": _carimbo(pool, f"pop×{pen_key}", "IBGE+param", censo_base or "n/d"),
            "margem_fresca": _carimbo(margem, "pool−cap_parque", "derivada", "n/a"),
        },
        "area_proxy_usada": {
            "low": int(a_low),
            "mid": int(a_mid),
            "premium": int(a_prem),
            "nicho_desconhecido": int(a_nd),
        },
        "base_espacial": base_esp,
    }
```

Adjust `test_nicho_uses_1250_x_mid` if current tier rules never emit `nicho` for that fixture — then use explicit mix by stubbing or pass a competitor already classified via nome that maps to desconhecido with ticket None.

- [ ] **Step 4: Run — PASS**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py -q --tb=short -x
```

- [ ] **Step 5: Commit** — só se Marcelo pedir

---

### Task 3: `attach_absorcao_margem_fresca` + A9 hook

**Files:**
- Modify: `tools/absorcao_margem_fresca.py` (add attach)
- Modify: `agents/a9_positioning_strategist.py` (após `attach_matriz_demo_saturacao`)
- Modify: `tools/test_absorcao_margem_fresca.py`

**Interfaces:**
- Consumes: same `_concorrentes_from_state` pattern — **import** from `tools.matriz_demo_saturacao` if exported; else duplicate thin helper or export `_concorrentes_from_state` as `concorrentes_espaciais_from_state` (prefer export public alias in matriz module to avoid private import)
- Produces: `parsed["absorcao_margem_fresca"] = dict`

- [ ] **Step 1: Export spatial competitor helper** (if still private)

In `tools/matriz_demo_saturacao.py`, add:

```python
def concorrentes_espaciais_from_state(state: dict[str, Any]) -> tuple[list[dict], str]:
    return _concorrentes_from_state(state)
```

- [ ] **Step 2: Failing attach test**

```python
from tools.absorcao_margem_fresca import attach_absorcao_margem_fresca

def test_attach_writes_parsed():
    state = {
        "demografia_bairro": {"populacao": 100_000, "renda_media_per_capita": 1500, "censo_base": "poligono_ibge_bairro"},
        "concorrentes_brutos": [
            {"nome": "Smart Fit", "gate_espacial": "poligono_ibge_bairro"},
            {"nome": "Bodytech", "gate_espacial": "poligono_ibge_bairro"},
        ],
        "area_m2": 1500,
        "modelo_recomendado": "mid",
    }
    parsed: dict = {}
    out = attach_absorcao_margem_fresca(state, parsed)
    assert out is not None
    assert parsed["absorcao_margem_fresca"]["rotulo"] in ("fresco", "misto", "roubo")
    assert parsed["absorcao_margem_fresca"]["base_espacial"] == "poligono_ibge"
```

- [ ] **Step 3: Implement attach**

```python
def attach_absorcao_margem_fresca(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any] | None:
    from tools.matriz_demo_saturacao import concorrentes_espaciais_from_state

    demo = state.get("demografia_bairro") if isinstance(state.get("demografia_bairro"), dict) else {}
    hr = parsed.get("headroom_renda") if isinstance(parsed.get("headroom_renda"), dict) else {}
    pop = demo.get("populacao") or hr.get("populacao")
    renda_pc = hr.get("renda_pc") or demo.get("renda_media_per_capita") or demo.get("renda_pc")

    area = state.get("area_m2") or state.get("area_candidato_m2")
    if area is None:
        # fallback faixa mid do relatório se existir
        area = 1500.0
    modelo = (
        parsed.get("modelo_sugerido")
        or (parsed.get("matriz_demo_saturacao") or {}).get("modelo_sugerido")
        or state.get("modelo_recomendado")
        or "mid"
    )
    if isinstance(modelo, str) and "premium" in modelo.lower():
        modelo_c = "premium"
    elif isinstance(modelo, str) and "low" in modelo.lower():
        modelo_c = "low"
    else:
        modelo_c = "mid"

    cs, fonte = concorrentes_espaciais_from_state(state)
    result = absorcao_margem_fresca(
        concorrentes=cs,
        pop_poligono=pop,
        area_candidato_m2=float(area),
        modelo_cenario=modelo_c,
        renda_pc=float(renda_pc) if renda_pc is not None else None,
        fonte_espacial=fonte,
        censo_base=str(demo.get("censo_base") or fonte),
    )
    parsed["absorcao_margem_fresca"] = result
    return result
```

- [ ] **Step 4: Wire A9** — same try/except pattern as Matriz (~linha 1072):

```python
            from tools.absorcao_margem_fresca import attach_absorcao_margem_fresca
            attach_absorcao_margem_fresca(state, parsed)
```

(logo após `attach_matriz_demo_saturacao`)

- [ ] **Step 5: Run tests PASS**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py -q --tb=short -x
```

- [ ] **Step 6: Commit** — só se Marcelo pedir

---

### Task 4: Docs conferência + PIPELINE

**Files:**
- Modify: `.agent/rules/conferencia-fontes-pipeline.md` (nova subseção após matriz §9.1)
- Modify: `docs/arquitetura/PIPELINE_AGENTES.md` (bullet A9 Absorção)

- [ ] **Step 1: Add § Absorção** in conferência (espelho matriz):

```markdown
### Absorção / margem fresca (W2a)

| Peça | Regra |
|---|---|
| Compute | `tools/absorcao_margem_fresca.py` — **não** A0/A2/Matriz embutida |
| Área proxy | `area_proxy_low_m2=1000`, mid=1500, premium=2000, nicho/desc=1250 |
| Capacidade parque | N×tier × área_proxy × `matr_m2_*_realista` |
| Pool | pop polígono × penetração (geral \| A/B) |
| Quem anexa | A9 `attach_absorcao_margem_fresca` → `absorcao_margem_fresca` |
| Spatial W2a | Spec C PIP / raio — **sem Voronoi** |
| Spec | `docs/superpowers/specs/2026-08-07-absorcao-margem-fresca-design.md` |
```

- [ ] **Step 2: PIPELINE_AGENTES.md** — sob A9, 2–3 linhas: Absorção irmão da Matriz; números tool-only; state key.

- [ ] **Step 3: Commit** — só se Marcelo pedir

---

# Wave W2b — PDF

### Task 5: Seção PDF Absorção

**Files:**
- Modify: `pdf/html_builder.py` (template + `_build_context` / return dict)
- Create: `pdf/test_absorcao_html.py`
- Create (optional): `docs/superpowers/previews/2026-08-07-absorcao-w2a.html`

**Interfaces:**
- Consumes: `pos["absorcao_margem_fresca"]` or `meta["absorcao_margem_fresca"]`
- Produces: ctx key `absorcao` with display fields

- [ ] **Step 1: Failing test** — render HTML contains "Absorção" / "alunos frescos" and rótulo

```python
# pdf/test_absorcao_html.py
# Follow pattern of pdf/test_matriz_modelo_html.py if present;
# else build minimal RelatorioModel / context stub that injects absorcao.

def test_html_has_absorcao_section():
    # Use existing html builder entry that accepts posicionamento meta
    ...
    assert "Absorção" in html or "alunos frescos" in html.lower()
    assert "roubo" in html.lower() or "fresco" in html.lower() or "misto" in html.lower()
```

(Implementer: open `pdf/test_matriz_modelo_html.py` and clone fixture; inject `absorcao_margem_fresca`.)

- [ ] **Step 2: Template block** — insert **after** Demografia, **before** `{% if matriz %}` (or after matriz — prefer **after competitiva / before matriz** per spec “Demografia/Competitiva → Absorção → Quadro Modelo”; if competitiva comes after demografia today, place Absorção **after matriz is OK only if preview order documented** — preferred order:

1. Demografia  
2. Absorção  
3. Modelo Adequado (matriz)  
4. Inteligência Competitiva  

```html
{% if absorcao %}
<div class="sec">Absorção e margem de alunos</div>
<table class="d"><tr><th>Métrica</th><th>Valor</th></tr>
  <tr><td>Teto da unidade (matrículas realistas)</td><td><strong>{{ absorcao.teto }}</strong></td></tr>
  <tr><td>Capacidade estimada do parque</td><td>{{ absorcao.cap_parque }}</td></tr>
  <tr><td>Pool demográfico</td><td>{{ absorcao.pool }}</td></tr>
  <tr><td>Margem fresca</td><td>{{ absorcao.margem }}</td></tr>
  <tr><td>Leitura</td><td><strong>{{ absorcao.rotulo_label }}</strong></td></tr>
</table>
{% if absorcao.nota %}<div class="note" style="margin-top:6px;">{{ absorcao.nota }}</div>{% endif %}
{% endif %}
```

Copy labels PT:
- `fresco` → "Há margem de alunos frescos"
- `misto` → "Parte fresca, parte absorção do parque"
- `roubo` → "Crescimento exige absorver alunos do parque ativo"

Nota: incluir carimbo curto (proxy área; não m² medido).

- [ ] **Step 3: Context mapping** (mirror matriz block ~1453):

```python
    _raw_abs = pos.get("absorcao_margem_fresca") or meta.get("absorcao_margem_fresca")
    absorcao = None
    if isinstance(_raw_abs, dict) and _raw_abs.get("rotulo"):
        _lab = {
            "fresco": "Há margem de alunos frescos",
            "misto": "Parte fresca, parte absorção do parque",
            "roubo": "Crescimento exige absorver alunos do parque ativo",
        }
        absorcao = {
            "teto": _raw_abs.get("teto_unidade"),
            "cap_parque": _raw_abs.get("capacidade_parque_estimada"),
            "pool": _raw_abs.get("pool_demografico"),
            "margem": _raw_abs.get("margem_fresca"),
            "rotulo_label": _lab.get(_raw_abs.get("rotulo"), _raw_abs.get("rotulo")),
            "nota": (_raw_abs.get("carimbos") or {}).get("capacidade_parque_estimada"),
        }
```

Add `"absorcao": absorcao` to return dict.

- [ ] **Step 4: Run PASS**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest pdf/test_absorcao_html.py tools/test_absorcao_margem_fresca.py -q --tb=short -x
```

- [ ] **Step 5: Preview HTML** (optional) under `docs/superpowers/previews/2026-08-07-absorcao-w2a.html` with sample numbers — Marcelo review before merge.

- [ ] **Step 6: Commit** — só se Marcelo pedir

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|---|---|
| Função determinística + carimbos | T2 |
| Mix via Matriz | T2 (`contar_mix`) |
| Área proxy 1000/1500/2000/1250 | T1 |
| A9 attach | T3 |
| PDF quadro | T5 |
| Conferência + PIPELINE | T4 |
| Sem Voronoi W2a | Global + T2 assert `base_espacial` |
| SOV fora | não há task SOV |
| W2c / app card | fora deste plan |

Placeholder scan: none intentional.  
Types: `rotulo` / `base_espacial` / state key `absorcao_margem_fresca` consistent across T2–T5.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-07-absorcao-margem-fresca.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session, `executing-plans`, checkpoints  

Which approach?
