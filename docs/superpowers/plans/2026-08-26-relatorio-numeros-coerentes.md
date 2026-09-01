# Relatório PDF — números coerentes (CAPEX, payback, CNO, contagens)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the client PDF internally consistent: displayed CAPEX parts sum to CAPEX total, payback formula is visible and matches A4, CNO resident total equals the sum of displayed rows, and competitor counts/ratings say which N they use.

**Architecture:** Display-only in the PDF view layer (`pdf/models.py` → `pdf/adapters.py` → `pdf/html_builder.py`). Do **not** change A4 formulas in `tools/financial_tools.py`. The engine is already consistent (`investimento_total = capex + capital_giro`; `receita = alunos × ticket × (1 − inadimplência)`). The PDF currently hides pieces (frete, giro, inadimplência, three different competitor Ns).

**Tech Stack:** Python 3.11, pytest via `.venv`, Jinja2 template in `pdf/html_builder.py`, `RelatorioPdfModel` / `CenarioPdf`, `gerar_html`.

**Evidence (debug session):** auditor HTML `rpt_1786` Cocó 2026-08-10. Root causes confirmed in code, not guessed.

## Global Constraints

- Numbers on the report come from tools/state, never LLM invention (P-000 §6 / pipeline-fontes-deterministicas).
- Carimbo on every new displayed figure: valor · base · fonte · janela (P-010).
- Client copy in Portuguese; no `pool` / `pen.` / param IDs (`.agent/rules/leitura-executiva-pdf.md`).
- Tests: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short` — never global `pytest`.
- TDD: write failing test first; fail must be `AssertionError`, not ImportError.
- Commits only if Marcelo asks (do not `git commit` in execution unless he says so).
- Preview before claiming UI done: `gerar_html(...)` dump to `docs/superpowers/previews/2026-08-26-relatorio-numeros-coerentes.html` and open in browser (`.agent/rules/preview-aprovacao.md`).
- Do not touch MRLR, SearchAPI, A0–A3 engines, or Oceano Azul classification math.
- Out of scope (auditor mixed artifacts): trailing `</html>3`, `styles.css`, `script.js`, `getElementById('currentTime')`. Those are not produced by `_TEMPLATE`.

## File map

| File | Role |
|------|------|
| `pdf/models.py` | Optional fields on `CenarioPdf`: `capex_frete`, `capital_giro`, `taxa_inadimplencia`, `ticket_realizado` |
| `pdf/adapters.py` | Map A4 `capex_detalhado.frete_equipamentos`, `capital_giro`, `taxa_inadimplencia`, `ticket_realizado_estimado` in `_map_cenario_row` **and** `_nested_cenarios_to_rows` |
| `pdf/html_builder.py` | CAPEX bars vs `capex_total`; payback/receita notes; CNO rounding; rating N; glossário 7 vs polígono vs anéis; `<title>`; `<thead>` |
| `pdf/test_html_builder.py` | Existing fixtures — keep `2.879` when there is no per-obra list |
| `pdf/test_relatorio_numeros_coerentes.py` | **Create** — all new assertions |
| `docs/superpowers/previews/2026-08-26-relatorio-numeros-coerentes.html` | Preview dump |

**Do not modify:** `tools/financial_tools.py` payback/CAPEX math.

---

### Task 1: Pipe hidden A4 fields into `CenarioPdf`

**Files:**
- Modify: `pdf/models.py` (`CenarioPdf` after `capex_contingencia`)
- Modify: `pdf/adapters.py` (`_map_cenario_row` ~89–126, `_nested_cenarios_to_rows` ~625–657)
- Test: `pdf/test_relatorio_numeros_coerentes.py`

**Interfaces:**
- Consumes: A4 row keys `capex_detalhado.frete_equipamentos`, `capital_giro`, `taxa_inadimplencia`, `ticket_realizado_estimado` (already on scenario dict in `financial_tools.py` ~720–758)
- Produces: `CenarioPdf.capex_frete: float | None = None`, `capital_giro: float | None = None`, `taxa_inadimplencia: float | None = None` (fraction, e.g. `0.06`), `ticket_realizado: float | None = None`

- [ ] **Step 1: Write the failing test**

Create `pdf/test_relatorio_numeros_coerentes.py`:

```python
from pdf.adapters import _map_cenario_row, _nested_cenarios_to_rows


def test_map_cenario_row_keeps_frete_giro_inad():
    row = {
        "modelo": "mid",
        "ticket_medio": 150,
        "receita_mensal": 201466.0,
        "lucro_mensal_estimado": 41606.0,
        "margem_percentual": 21,
        "payback_meses": 40,
        "investimento_total": 1_664_240.0,
        "capex_total": 1_226_244.0,
        "capex_equipamentos": 600_030.0,
        "capex_obra_adaptacao": 400_000.0,
        "capex_projeto_arquitetonico": 50_000.0,
        "capex_alvara_e_taxas": 25_874.0,
        "capex_contingencia_valor": 111_477.0,
        "capex_frete_equipamentos": 38_863.0,
        "capital_giro": 437_996.0,
        "taxa_inadimplencia": 0.0407,
        "ticket_realizado_estimado": 143.90,
        "viabilidade": "INVIAVEL",
        "alunos_projetados": 1400,
    }
    c = _map_cenario_row(row)
    assert c.capex_frete == 38863.0
    assert c.capital_giro == 437996.0
    assert c.taxa_inadimplencia == 0.0407
    assert c.ticket_realizado == 143.90


def test_nested_cenarios_copy_frete_giro_inad():
    nested = {
        "mid": {
            "ticket_medio": 150,
            "receita_mensal": 201466.0,
            "lucro_mensal_estimado": 41606.0,
            "margem_percentual": 21,
            "payback_meses": 40,
            "investimento_total": 1_664_240.0,
            "capex_total": 1_226_244.0,
            "capital_giro": 437_996.0,
            "taxa_inadimplencia": 0.0407,
            "ticket_realizado_estimado": 143.90,
            "viabilidade": "INVIAVEL",
            "alunos_projetados": 1400,
            "capex_detalhado": {
                "equipamentos": 600_030.0,
                "obra_adaptacao": 400_000.0,
                "projeto_arquitetonico": 50_000.0,
                "alvara_e_taxas": 25_874.0,
                "frete_equipamentos": 38_863.0,
                "contingencia_valor": 111_477.0,
                "total": 1_226_244.0,
            },
        }
    }
    rows = _nested_cenarios_to_rows(nested)
    assert len(rows) == 1
    assert rows[0]["capex_frete_equipamentos"] == 38863.0
    assert rows[0]["capital_giro"] == 437996.0
    mapped = _map_cenario_row(rows[0])
    assert mapped.capex_frete == 38863.0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest pdf/test_relatorio_numeros_coerentes.py::test_map_cenario_row_keeps_frete_giro_inad pdf/test_relatorio_numeros_coerentes.py::test_nested_cenarios_copy_frete_giro_inad -v --tb=short
```

Expected: FAIL `AttributeError` on `capex_frete` or assert `None == 38863.0`.

- [ ] **Step 3: Write minimal implementation**

On `CenarioPdf` (`pdf/models.py`), after `capex_contingencia`:

```python
    capex_frete: float | None = None
    capital_giro: float | None = None
    taxa_inadimplencia: float | None = None
    ticket_realizado: float | None = None
```

In `_map_cenario_row`, pass:

```python
        capex_frete=_num(row.get("capex_frete_equipamentos")),
        capital_giro=_num(row.get("capital_giro")),
        taxa_inadimplencia=_num(row.get("taxa_inadimplencia")),
        ticket_realizado=_num(row.get("ticket_realizado_estimado")),
```

In `_nested_cenarios_to_rows` `row = { ... }` add:

```python
            "capex_frete_equipamentos": capex.get("frete_equipamentos"),
            "capital_giro": c.get("capital_giro"),
            "taxa_inadimplencia": c.get("taxa_inadimplencia"),
            "ticket_realizado_estimado": c.get("ticket_realizado_estimado"),
```

Keep existing `capex_obra=obra + projeto + alvara` (do not un-fold in this task).

- [ ] **Step 4: Run test to verify it passes**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit** (only if Marcelo asked)

```
git add pdf/models.py pdf/adapters.py pdf/test_relatorio_numeros_coerentes.py
git commit -m "fix(pdf): pass A4 frete, working capital and delinquency into CenarioPdf"
```

---

### Task 2: CAPEX bars sum to displayed CAPEX

**Files:**
- Modify: `pdf/html_builder.py` — `_TEMPLATE` CAPEX block (~392–398) and Python builder (~1497–1514)
- Test: `pdf/test_relatorio_numeros_coerentes.py`

**Root cause:** Bars use only obra / equipamentos / contingência and `% = v / sum(those three)`. Frete is in `capex_total` but not in bars. Adapter already folds projeto+alvará into `capex_obra`. Missing line ≈ R$ 38.863 on the Cocó sample = `frete_equipamentos`.

**Interfaces:**
- Consumes: `CenarioPdf.capex_obra`, `capex_equipamentos`, `capex_contingencia`, `capex_frete`, `capex_total`
- Produces: `capex.itens[]` with `pct` vs **`capex_total`**, plus `capex.total` and `capex.fecha` bool

- [ ] **Step 1: Write the failing test**

Append:

```python
from pdf.html_builder import gerar_html
from pdf.models import CenarioPdf, RelatorioPdfModel
from pdf.test_html_builder import _model


def _mid_capex() -> CenarioPdf:
    return CenarioPdf(
        modelo="mid",
        label="Padrão",
        ticket_medio=150,
        receita_mensal=201_466,
        lucro_mensal=41_606,
        margem_pct=21,
        payback_meses=40,
        investimento_total=1_664_240,
        capex_total=1_226_244,
        capex_obra=475_874,
        capex_equipamentos=600_030,
        capex_contingencia=111_477,
        capex_frete=38_863,
        capital_giro=437_996,
        viabilidade="INVIAVEL",
        matriculas_realista=1400,
    )


def test_capex_bars_include_frete_and_pct_of_total():
    m = _model()
    m.cenarios = [_mid_capex()]
    m.modelo_recomendado = "nenhum"
    h = gerar_html(m)
    assert "Frete equipamentos" in h
    assert "38.863" in h
    # 38863/1226244 ≈ 3% — must NOT be 0% of a 3-line-only subtotal
    assert "Composição do investimento" in h
    assert "soma das linhas = CAPEX" in h.lower() or "Soma das linhas" in h
```

- [ ] **Step 2: Run test to verify it fails**

```
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest pdf/test_relatorio_numeros_coerentes.py::test_capex_bars_include_frete_and_pct_of_total -v --tb=short
```

Expected: FAIL `assert "Frete equipamentos" in h`.

- [ ] **Step 3: Write minimal implementation**

Replace the bar builder (~1497–1514) with:

```python
    capex = None
    cap_cen = next((c for c in (model.cenarios or [])
                    if (c.modelo or "").lower() == rec_norm or (c.label or "").lower() == rec_norm), mid_cen)
    if cap_cen is not None and cap_cen.capex_total:
        itens_raw = [
            ("Obra/adaptação", cap_cen.capex_obra),
            ("Equipamentos", cap_cen.capex_equipamentos),
            ("Frete equipamentos", cap_cen.capex_frete),
            ("Contingência", cap_cen.capex_contingencia),
        ]
        itens_raw = [(lab, v) for lab, v in itens_raw if v]
        tot_ref = float(cap_cen.capex_total)
        soma = sum(v for _, v in itens_raw)
        capex = {
            "modelo": cap_cen.label or cap_cen.modelo,
            "total": _brl(tot_ref),
            "itens": [
                {"label": lab, "valor": _brl(v), "pct": round(100 * v / tot_ref)}
                for lab, v in itens_raw
            ],
            "fecha": abs(soma - tot_ref) < 1.0,
            "soma": _brl(soma),
        }
```

In `_TEMPLATE` after the bar loop (~397), add:

```html
<div class="note">CAPEX deste cenário: R$ {{ capex.total }} · % sobre o CAPEX total (não sobre um subconjunto). Obra/adaptação já inclui projeto e alvará. {% if capex.fecha %}Soma das linhas = CAPEX.{% else %}Soma das linhas R$ {{ capex.soma }} — conferir linhas omitidas.{% endif %} Fonte: A4 (SINAPI/CUB + kit + ANTT + contingência).</div>
```

Skip frete row when `capex_frete` is 0/None (already filtered by `if v`).

- [ ] **Step 4: Run tests**

```
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest pdf/test_relatorio_numeros_coerentes.py pdf/test_html_builder.py pdf/test_render_campos_v3.py -q --tb=short
```

Expected: PASS.

- [ ] **Step 5: Commit** (only if asked)

```
git add pdf/html_builder.py pdf/test_relatorio_numeros_coerentes.py
git commit -m "fix(pdf): CAPEX bars include freight and percent of full total"
```

---

### Task 3: Expose payback formula (not CAPEX ÷ lucro)

**Files:**
- Modify: `pdf/html_builder.py` KPI strip (~1488–1496, template ~371–376) and financial note (~381)
- Test: `pdf/test_relatorio_numeros_coerentes.py`

**Root cause:** A4 `payback_meses = int(investimento_total / lucro_mensal)` with `investimento_total = capex + capital_giro`. KPI shows `capex_total` + mid payback, so auditor divided the wrong numerator. Each row has its own investimento.

**Interfaces:**
- Consumes: `mid_cen.investimento_total`, `mid_cen.capex_total`, `mid_cen.capital_giro`, `mid_cen.payback_meses`
- Produces: `kpi_fin.capex`, `kpi_fin.investimento`, `kpi_fin.payback`, template note

- [ ] **Step 1: Write the failing test**

```python
def test_payback_note_uses_investimento_not_capex_alone():
    m = _model()
    m.cenarios = [_mid_capex()]
    h = gerar_html(m)
    assert "capital de giro" in h.lower()
    assert "1.664.240" in h or "investimento" in h.lower()
    assert "Payback (mid)" in h
```

- [ ] **Step 2: Run test — expect FAIL** (no “capital de giro” near finance)

- [ ] **Step 3: Implement**

KPI builder:

```python
        kpi_fin = {
            "area": f"{model.area_m2_min}–{model.area_m2_max}",
            "aluguel": _brl(model.aluguel_mensal) if model.aluguel_mensal else None,
            "capex": _brl(mid_cen.capex_total) if mid_cen and mid_cen.capex_total else None,
            "investimento": _brl(mid_cen.investimento_total) if mid_cen and mid_cen.investimento_total else None,
            "payback": f"{mid_cen.payback_meses}m" if mid_cen and mid_cen.payback_meses else None,
        }
```

Template after KPI cells (new cell if investimento present):

```html
  {% if kpi_fin.investimento %}<div class="c"><div class="kpi-t">Investimento (mid)</div><div class="kpi-n" style="font-size:13pt;">R$ {{ kpi_fin.investimento }}</div><div class="kpi-s">CAPEX + giro</div></div>{% endif %}
```

Note after the 3-scenario table (always when `cenarios`):

```html
<div class="note">Payback de cada linha = investimento daquele modelo (CAPEX + capital de giro) ÷ lucro/mês, truncado para inteiro — não é o CAPEX do KPI ÷ lucro. Cada modelo tem CAPEX próprio. Fonte: A4.</div>
```

Do not change `int()` truncation in `financial_tools.py`.

- [ ] **Step 4: Run tests** — same pytest files as Task 2. Expected PASS.

- [ ] **Step 5: Commit** (only if asked)

```
git commit -m "fix(pdf): show working-capital investment and payback formula"
```

---

### Task 4: Explain receita ≠ alunos × ticket de balcão

**Files:**
- Modify: `pdf/html_builder.py` scenario loop (~1448–1454) + template note
- Test: `pdf/test_relatorio_numeros_coerentes.py`

**Root cause:** `ticket_realizado = ticket * (1 - inadimplencia)`; `receita_mensal = matr_real * ticket_realizado`. Delinquency differs by model.

- [ ] **Step 1: Failing test**

```python
def test_receita_note_mentions_inadimplencia():
    m = _model()
    c = _mid_capex()
    c.taxa_inadimplencia = 0.04
    c.ticket_realizado = 144.0
    m.cenarios = [c]
    h = gerar_html(m)
    assert "inadimplência" in h.lower()
    assert "ticket realizado" in h.lower() or "ticket efetivo" in h.lower()
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement**

When building each `cenarios` dict, add:

```python
            "inad": (
                f"{c.taxa_inadimplencia * 100:.0f}%"
                if c.taxa_inadimplencia is not None else None
            ),
```

Template note (same finance section):

```html
<div class="note">Receita/mês = alunos × ticket efetivo. Ticket efetivo = mensalidade de balcão × (1 − inadimplência estimada do modelo). Não multiplique alunos × ticket da coluna. Fonte: A4.</div>
```

If any scenario has `inad`, append `Inadimplência neste run: Econômico x% · Padrão y% · Premium z%.`

Keep the note even when `taxa_inadimplencia` is missing (old reports) — formula still true.

- [ ] **Step 4: pytest** Task 2 file list + this test. PASS.

- [ ] **Step 5: Commit** (only if asked)

```
git commit -m "fix(pdf): label revenue as students times net ticket after delinquency"
```

---

### Task 5: CNO moradores total = sum of displayed row integers

**Files:**
- Modify: `pdf/html_builder.py` `_contexto` demanda block (~1694–1758)
- Test: `pdf/test_relatorio_numeros_coerentes.py`

**Root cause:** Row cell uses `_int(v)` → `int(v)` **truncates**. Footer uses `_brl(moradores_total_est)` → `:,.0f` **rounds**. Cocó: rows 938+772+609+345+142+71 = 2877 vs footer 2879.

**Do not** change `tools/demanda_futura_tools.py` `round(tot["moradores_est"], 1)`.

- [ ] **Step 1: Failing test**

```python
def test_cno_total_equals_sum_of_displayed_rows():
    m = _model()
    m.metadata = {
        "demanda_futura": {
            "status": "ok",
            "provavel_residencial_n": 2,
            "captura_total_est": 26,
            "receita_total_mensal_est": 4828,
            "moradores_total_est": 2879.4,
            "obras": [
                {
                    "empreendimento": "A",
                    "provavel_residencial": True,
                    "unidades_est": 353,
                    "moradores_est": 938.6,
                    "captura_est": 14.2,
                    "receita_mensal_est": 2648,
                },
                {
                    "empreendimento": "B",
                    "provavel_residencial": True,
                    "unidades_est": 290,
                    "moradores_est": 772.4,
                    "captura_est": 11.8,
                    "receita_mensal_est": 2180,
                },
            ],
        }
    }
    h = gerar_html(m)
    # displayed rows use same round-half-up as total
    assert ">939<" in h or ">938<" in h  # lock after choosing ONE helper
```

**Chosen rule (lock this):** display people with `_brl` (round to integer, thousands as `.`). Footer `demanda.moradores` = `_brl(sum of the same floats used in rows)` **or** if `obras_ficha` non-empty, `_brl(sum(float(ob["moradores_est"]) for displayed obras))` so footer equals sum of what the eye adds **after the same formatter**.

Simplest lock: format every `moradores_est` with `_brl`; set `demanda.moradores` to `_brl(sum of those floats for the same obras_ficha slice)` not `moradores_total_est` when the table is shown.

Update `test_html_builder.py::test_binda_secoes_do_dado_real` only if it breaks: that fixture has **no obras list**, so footer still uses `moradores_total_est` → keep `"2.879"`.

Refine Step 1 test after helper exists:

```python
    assert h.count("939") + h.count("772") >= 1
    # footer must equal 939+772 = 1711 if both rounded with _brl
    assert "1.711" in h
    assert "2.879" not in h  # must not keep engine total when rows are shown
```

938.6 → `_brl` = 939; 772.4 → 772; footer 1.711. Engine 2879.4 must not show when the table is the 2-obra fixture.

- [ ] **Step 2: Run — FAIL** (footer still 2.879)

- [ ] **Step 3: Implement**

When appending each `obras_ficha` row, keep the float and format with `_brl` (same as money integers). After `obras_ficha = obras_ficha[:6]`, set footer from that slice only:

```python
            _mor_f = float(ob.get("moradores_est") or 0) if ob.get("moradores_est") else None
            obras_ficha.append({
                "nome": str(ob.get("empreendimento") or ob.get("construtora") or "—")[:28],
                "unidades": _int(ob.get("unidades_est")),
                "real": (ob.get("unidades_fonte") == "lancamento_exato"),
                "area": f"{ob.get('area_privativa_media')} m²" if ob.get("area_privativa_media") else "—",
                "entrega": str(ob.get("entrega") or "—")[:7],
                "fitness": bool(ob.get("amenidade_fitness")),
                "aderencia": aderencia,
                "aderencia_cls": aderencia_cls,
                "moradores": _brl(_mor_f) if _mor_f else "—",
                "captura": (round(float(_cap)) if _cap is not None else "—"),
                "receita": _brl(ob.get("receita_mensal_est")) if ob.get("receita_mensal_est") else "—",
                "quente": bool(ob.get("janela_quente")),
                "_mor_f": _mor_f or 0.0,
            })
        obras_ficha = obras_ficha[:6]
        ...
            "moradores": (
                _brl(sum(x["_mor_f"] for x in obras_ficha))
                if obras_ficha
                else _brl(df.get("moradores_total_est"))
            ),
```

Do not put `_mor_f` in the Jinja table; it is only for the Python sum. Hidden 7th obra must not enter the footer.

- [ ] **Step 4: pytest** including `pdf/test_html_builder.py::test_binda_secoes_do_dado_real`. PASS.

- [ ] **Step 5: Commit** (only if asked)

```
git commit -m "fix(pdf): CNO resident total uses same rounding as table rows"
```

---

### Task 6: Competitor N glossary + rating sample size

**Files:**
- Modify: `pdf/html_builder.py` panorama rating (~176, ~1343–1347), matriz note (~250–262), anéis intro (~344)
- Test: `pdf/test_relatorio_numeros_coerentes.py` (and existing `test_leitura_competitiva_*` must stay green)

**Root cause:** KPI “7” = gated Maps set. Matriz “N no polígono = 2” = saturation quadrant input. Anéis 0/0/2 = distance-weighted rings. Rating 4.2 = mean of **deep** competitors (4.1 and 4.3), not six listed notes. Copy “7 com reviews analisados” is already fixed in current `_contagem` for mixed analisado/mapeado — keep those tests.

- [ ] **Step 1: Failing tests**

```python
from pdf.models import CompetidorPdf

def test_rating_medio_states_sample_size():
    m = _model()
    m.competidores = [
        CompetidorPdf("A", 4.1, 429, "Aldeota", True, profundidade="analisado"),
        CompetidorPdf("B", 4.3, 160, "Papicu", False, profundidade="analisado"),
        CompetidorPdf("C", 5.0, 6, None, None, profundidade="mapeado"),
    ]
    m.metadata = {
        **(m.metadata or {}),
        "panorama": {"saturacao": "ALTO", "rating_medio": 4.2, "total": 7, "raio": 6},
    }
    h = gerar_html(m)
    assert "4.2" in h
    assert "2 analisados" in h.lower() or "n=2" in h.lower() or "2 concorrentes analisados" in h.lower()


def test_matriz_explains_n_poligono_vs_sete():
    m = _model()
    m.total_concorrentes = 7
    m.posicionamento_estrategico = {
        **(m.posicionamento_estrategico or {}),
        "matriz_demo_saturacao": {
            "quadrante": "Oceano Azul",
            "modelo_sugerido": "premium_ou_mid_high",
            "n_poligono": 2,
            "n_per_10k": 0.87,
            "mix": {"low": 0, "mid": 0, "premium": 0},
            "acao_estrategica": "Espaço para Premium/Mid-High.",
            "carimbo": "Oceano Azul · N=2",
        },
    }
    h = gerar_html(m)
    assert "não é a contagem de 7" in h.lower() or "régua da matriz" in h.lower()
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement**

Panorama rating cell:

```html
<tr><td>Rating médio dos concorrentes</td><td>{{ panorama.rating_medio }} ★{% if panorama.rating_n %} (n={{ panorama.rating_n }} analisados a fundo){% endif %}</td></tr>
```

In `_contexto`, set `panorama["rating_n"]` = count of `model.competidores` with `profundidade == "analisado"` and `rating is not None`. If 0, omit.

Matriz note (always when `matriz.n` is not None):

```html
<div class="note">“N no polígono” ({{ matriz.n }}) é a régua da matriz de posicionamento (densidade no polígono IBGE), não o número de academias no KPI nem nos anéis. Anéis = pressão ponderada por distância. Contagem da praça = gate bairro+tipo (quadro Cross-check).</div>
```

When `matriz.nota_contradicao` already fires (all INVIAVEL), keep it. Add one more sentence if `absorcao` deficit exists — **only if** `absorcao` is in context: “Oceano Azul fala de faixa (renda × mix no polígono), não de ‘há aluno novo’. Déficit no bloco Quem ainda pode matricular é outra pergunta.” Avoid `pool`.

Do not rewrite Oceano Azul to Vermelho.

- [ ] **Step 4: pytest** `pdf/test_html_builder.py::test_leitura_competitiva_mapeados_vs_analisados` must still PASS.

- [ ] **Step 5: Commit** (only if asked)

```
git commit -m "fix(pdf): label which competitor N and rating sample each figure uses"
```

---

### Task 7: `<title>` + `<thead>` on `table.d`

**Files:**
- Modify: `pdf/html_builder.py` `_TEMPLATE` head (~27) and tables that already have CSS `table.d thead { display: table-header-group; }`
- Test: `pdf/test_relatorio_numeros_coerentes.py`

**Out of scope:** wrapping every table in the 500-line template in one giant diff. Minimum: document title + wrap header row of (1) panorama/contexto, (2) financial scenarios, (3) CNO obras, (4) competitive list. Pattern:

```html
<table class="d"><thead><tr><th>...</th></tr></thead>
```

Existing first data row stays in implicit `<tbody>` (HTML5). Do not add empty `<tbody>` unless needed.

- [ ] **Step 1: Failing test**

```python
def test_html_has_title_and_thead_on_finance_table():
    m = _model()
    m.cenarios = [_mid_capex()]
    h = gerar_html(m)
    assert "<title>" in h
    assert "Viabilidade" in h[h.find("<title>"):h.find("</title>")+8]
    assert "Coco" in h or "Cocó" in h or "Fortaleza" in h
    fin = h[h.find("Viabilidade Financeira"):]
    assert "<thead>" in fin[:2500]
```

- [ ] **Step 2: FAIL** (no title today)

- [ ] **Step 3: Implement**

After `<meta charset="UTF-8">`:

```html
<title>Viabilidade · {{ bairro }} · {{ cidade }}</title>
```

Wrap the finance table header (the `Modelo / Ticket / ...` row) in `<thead>`. Repeat for CNO table and competitor table. Skip ERRC (not `table.d`).

- [ ] **Step 4: pytest** this test + `pdf/test_logo_html.py`. PASS.

- [ ] **Step 5: Commit** (only if asked)

```
git commit -m "fix(pdf): add document title and thead for print header repeat"
```

---

### Task 8: Preview for Marcelo

**Files:**
- Create: `docs/superpowers/previews/2026-08-26-relatorio-numeros-coerentes.html`
- Modify: none of A4

- [ ] **Step 1: Script** — dump HTML from `gerar_html` with a `RelatorioPdfModel` that includes mid CAPEX fixture + 2 CNO obras + 2 analisados + 1 mapeado + matriz Oceano Azul n=2 + panorama total=7. Use `gerar_html` only (preview-aprovacao). No micro-stub table.

- [ ] **Step 2: Write file** under `docs/superpowers/previews/2026-08-26-relatorio-numeros-coerentes.html`

- [ ] **Step 3: Open**

```
Start-Process "c:\Users\marce\gymsite\docs\superpowers\previews\2026-08-26-relatorio-numeros-coerentes.html"
```

- [ ] **Step 4: Checklist on the open page**

- CAPEX bars include frete; % of 1.226.244; note soma = CAPEX
- KPI investimento ≠ CAPEX; note payback formula
- Receita note mentions inadimplência
- CNO footer = sum of row people
- Rating has n=; matriz note separates 2 vs 7
- Browser tab title set
- No `styles.css` / `script.js` required (inline CSS stays)

- [ ] **Step 5: Commit preview** only if Marcelo asked to commit

---

## Self-review

**1. Spec coverage**

| Auditor item | Task |
|---|---|
| CAPEX ≠ sum of 3 bars | Task 2 (+ frete from Task 1) |
| Payback ≠ CAPEX÷lucro | Task 3 (formula was right in A4; PDF lied) |
| Receita ≠ alunos×ticket | Task 4 |
| 2879 vs 2877 | Task 5 |
| 7 vs N=2 vs anéis | Task 6 |
| Rating 4.2 vs six notes | Task 6 |
| “7 reviews analisados” | Already Task 6 / existing tests; regenerate report |
| Oceano Azul vs déficit | Task 6 note only — no engine change |
| `</html>3` | Out of scope (not in `_TEMPLATE`) |
| css/js/currentTime | Out of scope |
| Missing logo file in zip | Out of scope (builder already falls back if asset missing) |
| thead / title | Task 7 |

**2. Placeholder scan:** none of TBD / “add validation” / “similar to Task N”.

**3. Type consistency:** `capex_frete` / `capital_giro` / `taxa_inadimplencia` / `ticket_realizado` on `CenarioPdf`; adapter keys `capex_frete_equipamentos`, `ticket_realizado_estimado`. Nested path copies the same keys.

**Gap accepted:** `_nested_cenarios_to_rows` still does not copy tributos/ocupação (pre-existing). Do not expand in this plan.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-08-26-relatorio-numeros-coerentes.md`.

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks

**2. Inline Execution** — this session, `executing-plans`, checkpoints after each task’s pytest

Which approach?
