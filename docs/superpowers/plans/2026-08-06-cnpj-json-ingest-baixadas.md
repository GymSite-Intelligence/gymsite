# CNPJ JSON ingest + baixadas + métricas oferta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingerir JSON RFB (ativos+baixadas) em `cnpj_fitness_estabelecimentos` e expor métricas determinísticas mun/bairro (90d + Q calendário fechado) + cluster rede por `cnpj_basico` para A0/A6/IPM parcial.

**Architecture:** Migração `cnpj_basico` → loader `--from-json` + ZIP `--include-baixadas` → módulo puro de janelas/`as_of` → contagens baixas/entrantes/redes em `cnpj_fitness_tools` → override A0 copia os novos campos. Enrich `razao_social` async não bloqueia load.

**Tech Stack:** Python 3.11+, Supabase, pytest, argparse loader existente.

**Spec:** `docs/superpowers/specs/2026-08-05-cnpj-json-ingest-baixadas-design.md`

## Global Constraints

- Baixadas (`situacao=08`) **obrigatórias** no JSON load — file sem `08` → exit ≠ 0
- Parque ativo = sempre filtro `situacao_cadastral = 02` (após gate limpo)
- Baixas usam o **mesmo gate** parque limpo (CNAE 931 + nome→tipo)
- Janelas: `as_of = min(hoje_utc, último_dia_de_ref_month)`; Q = **último trimestre civil fechado** relativo a `as_of`
- Redes v1: `cnpj_basico` com ≥2 ativos fitness no BR = multiunidade; `razao_social` async
- Números = tool/banco, nunca LLM; carimbo valor · base · fonte · janela/`as_of`/`ref_month`
- Sinal `pressao_oferta_q`: `retracao` se saldo_q &lt; 0; `expansao` se &gt; 0; `neutro` se 0
- Verifier: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Commits só se Marcelo pedir
- Antes de alterar agents/tools de relatório: reler `.agent/rules/conferencia-fontes-pipeline.md` + `pipeline-fontes-deterministicas.md`

## File map

| File | Role |
|------|------|
| `db/migrations/20260806_cnpj_basico.sql` | coluna + indexes |
| `tools/cnpj_oferta_janelas.py` | puro: `as_of`, Q fechado, parse datas, normalize bairro |
| `tools/rfb_cnpj_fitness_loader.py` | `--from-json`, `--include-baixadas`, persist `cnpj_basico` |
| `tools/cnpj_fitness_tools.py` | baixas, entrantes_q, arvore oferta, redes, `as_of` nas queries |
| `agents/a0_context_builder.py` | override copia árvore/redes/baixas |
| `tools/test_a0_override.py` | assert novos campos |
| `tools/test_cnpj_oferta_janelas.py` | TDD janelas |
| `tools/test_rfb_cnpj_json_loader.py` | TDD map JSON + reject sem 08 |
| `tools/test_cnpj_oferta_metricas.py` | TDD contagens in-memory / helpers |
| `agents/specs/SPEC_A0_ContextBuilder.md` | contrato campos |
| `docs/arquitetura/PIPELINE_AGENTES.md` | fonte baixas |

---

### Task 1: Janelas puras (`as_of` + Q fechado)

**Files:**
- Create: `tools/cnpj_oferta_janelas.py`
- Create: `tools/test_cnpj_oferta_janelas.py`

**Interfaces:**
- Produces:
  - `ultimo_dia_mes(ref_month: date) -> date`
  - `as_of_ref(hoje: date, ref_month: date) -> date`  # min(hoje, last day of ref month)
  - `ultimo_trimestre_fechado(as_of: date) -> tuple[date, date, str]`  # start, end, label `YYYY-Qn`
  - `janela_90d(as_of: date) -> tuple[date, date]`
  - `parse_rfb_date(value: Any) -> date | None`  # int YYYYMMDD, str, date
  - `normalize_bairro(s: str) -> str`  # upper, strip accents, collapse spaces

- [ ] **Step 1: Write failing tests**

```python
from datetime import date
from tools.cnpj_oferta_janelas import (
    as_of_ref,
    ultimo_trimestre_fechado,
    janela_90d,
    parse_rfb_date,
    normalize_bairro,
)

def test_as_of_atrasado_pelo_ref_month():
    assert as_of_ref(date(2026, 8, 5), date(2026, 5, 1)) == date(2026, 5, 31)

def test_as_of_ref_no_futuro_usa_hoje():
    assert as_of_ref(date(2026, 5, 10), date(2026, 5, 1)) == date(2026, 5, 10)

def test_q_fechado_em_maio_e_q1():
    start, end, label = ultimo_trimestre_fechado(date(2026, 5, 31))
    assert (start, end, label) == (date(2026, 1, 1), date(2026, 3, 31), "2026-Q1")

def test_q_fechado_em_abril_e_q1():
    start, end, label = ultimo_trimestre_fechado(date(2026, 4, 1))
    assert label == "2026-Q1"

def test_janela_90d():
    a, b = janela_90d(date(2026, 5, 31))
    assert b == date(2026, 5, 31)
    assert a == date(2026, 3, 2)  # 31 - 90

def test_parse_rfb_date_int():
    assert parse_rfb_date(20221027) == date(2022, 10, 27)
    assert parse_rfb_date(0) is None
    assert parse_rfb_date(None) is None

def test_normalize_bairro_acento():
    assert normalize_bairro("  Perdízes ") == "PERDIZES"
```

- [ ] **Step 2: Run — expect fail**

```powershell
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_cnpj_oferta_janelas.py -q --tb=short -x
```

Expected: import/collection error or `ModuleNotFoundError`

- [ ] **Step 3: Implement `tools/cnpj_oferta_janelas.py`** (stdlib only: `datetime`, `unicodedata`, `re`)

- [ ] **Step 4: Run — expect pass**

- [ ] **Step 5: Commit** só se pedido

---

### Task 2: Migração `cnpj_basico`

**Files:**
- Create: `db/migrations/20260806_cnpj_basico.sql`

**Interfaces:**
- Produces: column `cnpj_basico text` + indexes; backfill `left(cnpj, 8)`

- [ ] **Step 1: Write migration**

```sql
-- cnpj_basico: raiz 8 dígitos para cluster rede / grupo econômico
alter table cnpj_fitness_estabelecimentos
  add column if not exists cnpj_basico text;

update cnpj_fitness_estabelecimentos
set cnpj_basico = left(cnpj, 8)
where cnpj_basico is null
  and cnpj is not null
  and length(cnpj) >= 8;

create index if not exists idx_cnpj_fitness_basico
  on cnpj_fitness_estabelecimentos (cnpj_basico);

create index if not exists idx_cnpj_fitness_situacao_data
  on cnpj_fitness_estabelecimentos (situacao_cadastral, data_situacao_cadastral);

comment on column cnpj_fitness_estabelecimentos.cnpj_basico is
  'CNPJ raiz (8 dígitos). Cluster multiunidade = mesma raiz com >=2 estab. ativos fitness no BR.';
```

- [ ] **Step 2: Apply** via Supabase MCP `apply_migration` (project GymSite) **ou** SQL editor — confirmar coluna com `list_tables` / query sample

- [ ] **Step 3: Commit** só se pedido

---

### Task 3: Map JSON → row + reject sem baixadas (TDD)

**Files:**
- Create: `tools/test_rfb_cnpj_json_loader.py`
- Modify: `tools/rfb_cnpj_fitness_loader.py`

**Interfaces:**
- Produces:
  - `SITUACAO_BAIXADA = {"8", "08"}`
  - `SITUACAO_LOAD = SITUACAO_ATIVA | SITUACAO_BAIXADA`
  - `json_row_to_estabelecimento(row: dict, *, ref_date: str, cidade: str | None, empresas_map: dict[str, str] | None) -> dict | None`
  - `load_from_json(path: str | Path, *, ref_month: str, dry_run: bool = False, empresas_map: dict | None = None) -> dict`  
    returns `{"upserted_02": int, "upserted_08": int, "skipped_situacao": int, "skipped_bad_date": int, "ref_month": str}`  
    raises `SystemExit` / `ValueError` se zero rows `08` no arquivo

- [ ] **Step 1: Failing tests** (fixtures inline, sem file 44MB)

```python
import pytest
from tools.rfb_cnpj_fitness_loader import json_row_to_estabelecimento, assert_json_has_baixadas

SAMPLE_02 = {
    "cnpj": "48434433000181",
    "cnpj_basico": "48434433",
    "situacao_cadastral": "02",
    "data_situacao_cadastral": 20221027,
    "data_inicio_atividade": 20221027,
    "cnae_fiscal_principal": "9313100",
    "cnae_fiscal_secundaria": "9319199",
    "nome_fantasia": "3B CROSSTRAINING",
    "bairro": "COHAB",
    "uf": "AC",
    "municipio": "0107",
    "cep": 69980000,
    "logradouro": "THAUMATURGO",
    "numero": "427",
    "complemento": "",
}

SAMPLE_08 = {**SAMPLE_02, "cnpj": "11111111000191", "cnpj_basico": "11111111",
             "situacao_cadastral": "08", "data_situacao_cadastral": 20260315}

def test_json_row_maps_basico_e_situacao():
    row = json_row_to_estabelecimento(SAMPLE_02, ref_date="2026-05-01", cidade="Rio Branco")
    assert row["cnpj"] == "48434433000181"
    assert row["cnpj_basico"] == "48434433"
    assert row["situacao_cadastral"] == 2
    assert row["bairro"] == "COHAB"
    assert row["data_inicio_atividade"] == "2022-10-27" or row["data_inicio_atividade"].isoformat() == "2022-10-27"

def test_assert_json_has_baixadas_ok():
    assert_json_has_baixadas([SAMPLE_02, SAMPLE_08])  # no raise

def test_assert_json_has_baixadas_fail():
    with pytest.raises((ValueError, SystemExit)):
        assert_json_has_baixadas([SAMPLE_02])

def test_cnpj_basico_derivado_se_ausente():
    r = {**SAMPLE_02}
    del r["cnpj_basico"]
    row = json_row_to_estabelecimento(r, ref_date="2026-05-01", cidade=None)
    assert row["cnpj_basico"] == "48434433"
```

- [ ] **Step 2: Run — expect fail**

```powershell
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_rfb_cnpj_json_loader.py -q --tb=short -x
```

- [ ] **Step 3: Implement** `json_row_to_estabelecimento`, `assert_json_has_baixadas`, reuse `_parse_date` / `parse_rfb_date`; situacao int; skip situacao fora `{02,08}` return `None`

- [ ] **Step 4: Pass tests**

- [ ] **Step 5: Commit** só se pedido

---

### Task 4: CLI `--from-json` + ZIP `--include-baixadas`

**Files:**
- Modify: `tools/rfb_cnpj_fitness_loader.py` (`load_ref_month`, `main`, `_flush` payload)

**Interfaces:**
- Consumes: Task 3 mappers; Task 2 column
- Produces: CLI flags; ZIP path inclui `08` quando `include_baixadas=True` (default True)

- [ ] **Step 1: Change ZIP filter**

Where today:

```python
if situacao not in SITUACAO_ATIVA:
    continue
```

Replace with:

```python
allowed = SITUACAO_LOAD if include_baixadas else SITUACAO_ATIVA
if situacao not in allowed:
    continue
```

Always set `"cnpj_basico": basico` (8 chars) on buffer dict.

- [ ] **Step 2: Implement `load_from_json`**

```python
def load_from_json(path, *, ref_month: str, dry_run: bool = False, empresas_map=None) -> dict:
    import json
    ref_month = _normalize_ref_month(ref_month)
    ref_date = f"{ref_month}-01"
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("JSON deve ser array de estabelecimentos")
    assert_json_has_baixadas(raw)
    # map → buffer → _flush upsert (same as ZIP)
    # count upserted_02 / upserted_08 by situacao_cadastral
    ...
```

Resolve `cidade` via `municipios_map` when available (`--ref` + Municipios.zip optional); else leave `cidade=None` and rely on later backfill — prefer resolve when map present.

- [ ] **Step 3: Wire argparse**

```python
ap.add_argument("--from-json", default="", help="Path JSON ativo+baixada (CNAE 9313100)")
ap.add_argument(
    "--include-baixadas",
    action=argparse.BooleanOptionalAction,
    default=True,
    help="Inclui situacao 08 no load ZIP (default: true).",
)
```

In `main`:

- If `--from-json`: **não** exigir `--cidade/--uf`; chamar `load_from_json`; print counts; return 0
- Else: existing path; pass `include_baixadas=args.include_baixadas` into `load_ref_month`

- [ ] **Step 4: Smoke dry-run** (se path local existir)

```powershell
c:\Users\marce\gymsite\.venv\Scripts\python.exe tools/rfb_cnpj_fitness_loader.py --from-json "C:\Users\marce\assistent-control\data\processed\receita-cnae-9313100-principal-ativo-baixada.json" --ref 2026-05 --dry-run
```

Expected: stdout com `upserted_08 > 0` (ou selected counts) e exit 0

- [ ] **Step 5: Commit** só se pedido

---

### Task 5: Helpers métricas oferta (TDD in-memory)

**Files:**
- Create: `tools/test_cnpj_oferta_metricas.py`
- Create or extend: `tools/cnpj_oferta_janelas.py` **ou** `tools/cnpj_oferta_metricas.py` (prefer novo módulo fino)

**Interfaces:**
- Produces:
  - `contar_eventos_oferta(rows: list[dict], *, as_of: date, bairro_norm: str | None, gate_fn) -> dict`
  - Each row: `situacao_cadastral`, `data_inicio_atividade`, `data_situacao_cadastral`, `bairro`, `cnpj`, `cnpj_basico`, plus fields gate needs
  - `classificar_raizes_multiunidade(ativos_br: list[dict]) -> set[str]`  # basicos with >=2 ativos
  - `bloco_redes(rows_ativos_recortados, raizes_multi: set[str], baixas_q_rows) -> dict` matching spec JSON keys
  - `pressao_oferta(saldo: int) -> str`  # retracao|expansao|neutro

- [ ] **Step 1: Failing tests**

```python
from datetime import date
from tools.cnpj_oferta_metricas import (
    contar_eventos_oferta,
    classificar_raizes_multiunidade,
    pressao_oferta,
)

def _row(**kw):
    base = {"situacao_cadastral": 2, "bairro": "PERDIZES", "cnpj": "1", "cnpj_basico": "11111111",
            "nome_fantasia": "GYM X", "cnae_fiscal_principal": "9313100", "cnaes_secundarios": ""}
    base.update(kw)
    return base

def test_baixas_e_entrantes_q_e_90d():
    as_of = date(2026, 5, 31)
    rows = [
        _row(cnpj="a", data_inicio_atividade=date(2026, 4, 1), situacao_cadastral=2),  # entrante 90d+Q2? wait Q=Q1
        _row(cnpj="b", data_inicio_atividade=date(2026, 2, 15), situacao_cadastral=2),  # entrante Q1
        _row(cnpj="c", situacao_cadastral=8, data_situacao_cadastral=date(2026, 2, 20),
             data_inicio_atividade=date(2020, 1, 1)),  # baixa Q1
        _row(cnpj="d", situacao_cadastral=8, data_situacao_cadastral=date(2026, 5, 1),
             data_inicio_atividade=date(2020, 1, 1)),  # baixa 90d not Q1
    ]
    # gate_fn identity True for test
    out = contar_eventos_oferta(rows, as_of=as_of, bairro_norm="PERDIZES", gate_fn=lambda r: True)
    assert out["entrantes_q"] == 1  # only Feb
    assert out["baixas_q"] == 1
    assert out["baixas_90d"] == 1  # May baixa
    assert out["saldo_oferta_q"] == 0  # 1-1
    assert out["janela_q_label"] == "2026-Q1"

def test_pressao():
    assert pressao_oferta(-1) == "retracao"
    assert pressao_oferta(1) == "expansao"
    assert pressao_oferta(0) == "neutro"

def test_multiunidade_br():
    ativos = [
        _row(cnpj="1", cnpj_basico="AAAAAAAA"),
        _row(cnpj="2", cnpj_basico="AAAAAAAA"),
        _row(cnpj="3", cnpj_basico="BBBBBBBB"),
    ]
    multi = classificar_raizes_multiunidade(ativos)
    assert multi == {"AAAAAAAA"}
```

Adjust expected entrantes_90d in test after implementing (Apr 1 is within 90d of May 31). Document expected counts in asserts explicitly.

- [ ] **Step 2: Fail → implement → pass**

- [ ] **Step 3: Commit** só se pedido

---

### Task 6: Wire Supabase queries + `dados_parque_cnpj_para_a0`

**Files:**
- Modify: `tools/cnpj_fitness_tools.py`
- Modify: `tools/test_a0_override.py` (extend fixtures)
- Test: `tools/test_cnpj_oferta_metricas.py` (keep pure); optional smoke with mock sb

**Interfaces:**
- Consumes: `contar_eventos_oferta`, `as_of_ref`, `bloco_redes`, gate existente (`incluir_no_parque` / classificador)
- Produces: extended return of `dados_parque_cnpj_para_a0`:

```python
"arvore_oferta": {
  "estoque_municipio": int,
  "estoque_bairro": int | None,
  "entrantes_municipio_90d": int,
  "entrantes_bairro_90d": int | None,
  "entrantes_municipio_q": int,
  "entrantes_bairro_q": int | None,
  "baixas_municipio_90d": int,
  "baixas_bairro_90d": int | None,
  "baixas_municipio_q": int,
  "baixas_bairro_q": int | None,
  "saldo_oferta_municipio_q": int,
  "saldo_oferta_bairro_q": int | None,
  "churn_municipio_q_pct": float | None,
  "churn_bairro_q_pct": float | None,
  "pressao_oferta_municipio_q": "retracao"|"expansao"|"neutro",
  "janela_90d": {"inicio": "...", "fim": "..."},
  "janela_q": {"inicio": "...", "fim": "...", "label": "2026-Q1"},
  "as_of": "...",
  "ref_month": "...",
  "fonte": "RFB CNPJ Aberto · cnpj_fitness_estabelecimentos",
},
"redes": { ... },  # spec keys
"arvore_2x2_parque": { ... },  # KEEP for back-compat; add baixas_* keys inside or leave + duplicate in arvore_oferta
```

Also put scalars in `metricas_objetivas`:
- `baixas_cnpj_fitness_90d`, `baixas_cnpj_fitness_q`, `entrantes_cnpj_fitness_q`, `saldo_oferta_q`, `pressao_oferta_q`, `janela_q_label`, `as_of`

**Query rules:**

1. Resolve `ref_month` vigente = max `ref_month` for cidade (existing pattern if any; else latest national).
2. `as_of = as_of_ref(date.today(), ref_month)`.
3. Entrantes / baixas: fetch candidates by cidade/uf + date bounds (union of 90d start and Q start → as_of), then apply gate client-side; filter `situacao` for baixas = 8.
4. Multiunidade: one query or reuse cached ativos BR `cnpj_basico` counts for `ref_month` — if too heavy, compute from distinct pairs in SQL via RPC later; v1 acceptable: load basico counts for roots present in mun sample + second query `in_(basicos)`.

- [ ] **Step 1: Extend override test fixture** so `dados_parque` mock / monkeypatch returns new keys; assert `_a0_override` copies `arvore_oferta` + `redes` (Task 7 can finish override — here only tool shape)

- [ ] **Step 2: Implement query + assembly in `dados_parque_cnpj_para_a0`**

- [ ] **Step 3: Keep `listar_entrantes_cnpj_fitness` using `as_of` from latest ref_month** (not bare `date.today()` alone) — same helper

- [ ] **Step 4: Run**

```powershell
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_cnpj_oferta_metricas.py tools/test_cnpj_oferta_janelas.py tools/test_a0_override.py -q --tb=short -x
```

- [ ] **Step 5: Commit** só se pedido

---

### Task 7: A0 override + SPEC docs

**Files:**
- Modify: `agents/a0_context_builder.py` (`_a0_override_cnpj_numeros`)
- Modify: `tools/test_a0_override.py`
- Modify: `agents/specs/SPEC_A0_ContextBuilder.md`
- Modify: `docs/arquitetura/PIPELINE_AGENTES.md` (seção CNPJ / fontes)

**Interfaces:**
- Consumes: `dados_parque_cnpj_para_a0` new keys
- Produces: `inner["arvore_oferta"]`, `inner["redes"]`, scalars baixas/saldo/pressao/as_of; keep `arvore_2x2_parque`

- [ ] **Step 1: Failing test** — mock tool return includes `arvore_oferta` / `redes`; after callback, `inner["baixas_cnpj_fitness_90d"] == …` and `inner["arvore_oferta"]` present

- [ ] **Step 2: Implement override copies** (mirror existing metricas block)

```python
inner["arvore_oferta"] = tool.get("arvore_oferta")
inner["redes"] = tool.get("redes")
inner["baixas_cnpj_fitness_90d"] = m.get("baixas_cnpj_fitness_90d")
inner["baixas_cnpj_fitness_q"] = m.get("baixas_cnpj_fitness_q")
inner["entrantes_cnpj_fitness_q"] = m.get("entrantes_cnpj_fitness_q")
inner["saldo_oferta_q"] = m.get("saldo_oferta_q")
inner["pressao_oferta_q"] = m.get("pressao_oferta_q")
inner["janela_q_label"] = m.get("janela_q_label")
inner["cnpj_as_of"] = m.get("as_of")
```

- [ ] **Step 3: Update SPEC_A0** table with new fields + carimbo rule
- [ ] **Step 4: Update PIPELINE_AGENTES.md** — baixas first-class; JSON ingest; MRLR untouched
- [ ] **Step 5: pytest override + janelas + metricas**
- [ ] **Step 6: Commit** só se pedido

---

### Task 8: Enrich async (mínimo)

**Files:**
- Create: `scripts/backfill_cnpj_razao_social.py` (thin CLI)
- Optional modify: reuse `tools/cnpj_enrichment.py`

**Interfaces:**
- Produces: script that selects rows `razao_social is null` for latest `ref_month`, calls existing enrich/cache, updates `cnpj_fitness_estabelecimentos.razao_social`
- Rate-limit polite; `--limit N`; `--dry-run`

- [ ] **Step 1: Script** — no need full TDD; smoke `--dry-run --limit 3`
- [ ] **Step 2: Document** one-liner in loader docstring / plan note
- [ ] **Step 3: Commit** só se pedido

---

### Task 9: Verificação ponta a ponta (checklist)

- [ ] Migration applied on target Supabase
- [ ] Dry-run JSON OK (`upserted_08 > 0`)
- [ ] Real upsert `--from-json` (staging/prod conforme Marcelo)
- [ ] Manual or pytest integration: cidade com dados → `arvore_oferta` keys present, `pressao_oferta_q` in {retracao,expansao,neutro}
- [ ] Parque ativo count unchanged vs filter `situacao=02` only (spot-check Fortaleza or fixture)
- [ ] Full unit suite:

```powershell
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_cnpj_oferta_janelas.py tools/test_rfb_cnpj_json_loader.py tools/test_cnpj_oferta_metricas.py tools/test_a0_override.py -q --tb=short
```

Expected: exit 0

---

## Spec coverage (self-review)

| Spec item | Task |
|-----------|------|
| Ingest JSON 02+08 | 3, 4 |
| Reject sem 08 | 3 |
| `cnpj_basico` column | 2, 4 |
| ZIP `--include-baixadas` default on | 4 |
| `as_of` + Q fechado + 90d | 1, 5, 6 |
| Árvore oferta mun/bairro | 5, 6 |
| Gate limpo em baixas | 5, 6 |
| Redes hybrid + enrich async | 5, 6, 8 |
| `pressao_oferta` via saldo_q | 5, 6 |
| A0 override + docs | 7 |
| Fantasma / no delete old refs | 4 (docstring; no DELETE) |
| MRLR / SearchAPI untouched | Global + docs |

## Placeholder scan

Nenhum TBD/TODO aberto — Task 6 multiunidade BR pode usar query `in_` por basicos do município se full-BR count for pesado; critério permanece ≥2 ativos BR.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-08-06-cnpj-json-ingest-baixadas.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session, `executing-plans`, checkpoints  

Which approach?
