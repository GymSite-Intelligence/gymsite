# RAG determinístico + LLM leitura — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tirar Vertex Discovery do caminho quente de `agents_site/tools.py`, separar L1 (dados) / L2 (corpus) / L3 (LLM só lê), com fallback local curado e carimbo em todo número.

**Architecture:** Facades RAG: Eros → corpus local (`docs/agente/agentes_site/rag/`) → stub honesto. Nunca Discovery no happy path. Tools L1 ficam em módulo próprio; L2 em outro; factory Eros permanece. Prompts dos 5 especialistas reforçam “só tool/corpus”.

**Tech Stack:** Python 3.11+, FastAPI/ADK `agents_site`, Eros Edge `knowledge-ask`, pytest, corpus `.txt` versionado no repo.

**Spec:** `docs/superpowers/specs/2026-08-04-rag-deterministico-llm-leitura-design.md`  
**Handoff:** `docs/handoffs/2026-08-04-vertex-off-eros-rag-parallel.md`

## Global Constraints

- Número exibido = valor · base · fonte · janela (regra Cocó / `.agent/rules`).
- Aluguel viabilidade = MRLR no A4 — nunca listing SearchAPI.
- `VERTEX_RAG_ENABLED` default off; prod example = `0`.
- Código/nomes de símbolos em inglês; copy usuário PT-BR.
- Testes backend: `gymsite_intelligence\.venv\Scripts\python.exe -m pytest` (ou `.venv` do monorepo se existir).
- Não commit sem pedido explícito do Marcelo.

## File map (alvo)

| Path | Responsabilidade |
|------|------------------|
| `agents_site/tools_l1_dados.py` | L1: Maps, IBGE, CNPJ bundle, MRLR, fórmulas, planta, reviews |
| `agents_site/tools_l2_rag.py` | L2: facades mercado/reg/obra/catálogo + pack Eros + corpus local |
| `agents_site/tools_eros.py` | Factory `consultar_eros_*` (hoje fim de `tools.py`) |
| `agents_site/corpus_local.py` | Retrieve determinístico sobre `docs/agente/agentes_site/rag/` |
| `agents_site/tools.py` | Re-export estável (compat ADK imports) — fino |
| `tools/discovery_engine_tools.py` | Legado: stub only OU delete callsites; sem import das facades |
| `agents_site/agent.py` | Docstring + prompts L3 |
| `agents_site/specs/SPEC_RAG_AGENTES_SITE.md` | Engines Vertex → Eros + corpus |
| `tests/agents_site/test_*` | Facades, corpus local, no-Vertex |

---

### Task 1: Inventário congelado + teste “facade não chama Discovery”

**Files:**
- Create: `tests/agents_site/test_no_vertex_in_facades.py`
- Modify: (nenhum ainda — só red)

**Interfaces:**
- Consumes: `consultar_base_mercado`, `consultar_base_regulatoria`, `consultar_engenharia_obra`, `consultar_catalogo_equipamentos`
- Produces: teste que falha se `buscar_conhecimento` / `buscar_catalogos_equipamentos` forem chamados quando Eros ausente

- [ ] **Step 1: Write the failing test**

```python
"""Facades L2 não importam/chamam Discovery no caminho feliz nem no fallback."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _clear_eros_and_vertex(monkeypatch):
    for k in (
        "EROS_GROUP_ID_MERCADO",
        "EROS_GROUP_ID_REGULATORIO",
        "EROS_GROUP_ID_ENGENHARIA",
        "EROS_GROUP_ID_TECNICO",
        "VERTEX_RAG_ENABLED",
    ):
        monkeypatch.delenv(k, raising=False)


def test_consultar_base_mercado_nao_chama_discovery():
    with patch("tools.discovery_engine_tools.buscar_conhecimento") as mock_v:
        from agents_site import tools as t

        out = t.consultar_base_mercado("tendencia academias brasil")
        mock_v.assert_not_called()
    assert out.get("fonte")
    assert "Vertex" not in str(out.get("fonte", ""))
    assert out.get("n_docs", 0) == 0 or out.get("status") in (
        "deprecated",
        "indisponivel",
        "vazio",
        None,
    )


def test_consultar_catalogo_nao_chama_discovery():
    with patch("tools.discovery_engine_tools.buscar_catalogos_equipamentos") as mock_v:
        from agents_site import tools as t

        out = t.consultar_catalogo_equipamentos("esteira Matrix")
        mock_v.assert_not_called()
    assert "Vertex" not in str(out.get("fonte", ""))
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/agents_site/test_no_vertex_in_facades.py -q
```

Expected: FAIL — hoje mercado/catálogo ainda caem em `buscar_*` Discovery quando Eros vazio.

- [ ] **Step 3: Commit** (só se Marcelo pedir)

```bash
git add tests/agents_site/test_no_vertex_in_facades.py
git commit -m "test(agents_site): facades must not call Vertex Discovery"
```

---

### Task 2: Corpus local determinístico (L2 fallback)

**Files:**
- Create: `agents_site/corpus_local.py`
- Create: `tests/agents_site/test_corpus_local.py`
- Modify: (depois Task 3)

**Interfaces:**
- Consumes: arquivos em `docs/agente/agentes_site/rag/*.txt`
- Produces: `buscar_corpus_local(pergunta: str, dominio: Literal["mercado","regulatorio","engenharia","tecnico"], n: int = 4) -> dict` com shape `{resultados: [{titulo, trecho, uri, fonte}], n_docs, fonte, status}`

- [ ] **Step 1: Write the failing test**

```python
from agents_site.corpus_local import buscar_corpus_local


def test_corpus_regulatorio_recupera_cref():
    out = buscar_corpus_local("CREF PJ registro academia", dominio="regulatorio", n=3)
    assert out["status"] == "ok"
    assert out["n_docs"] >= 1
    assert out["fonte"].startswith("corpus_local")
    assert any("CREF" in (r.get("trecho") or "").upper() or "CREF" in (r.get("titulo") or "").upper()
               for r in out["resultados"])


def test_corpus_dominio_vazio_status_vazio():
    out = buscar_corpus_local("xyzzy-no-match-qqq", dominio="tecnico", n=2)
    assert out["n_docs"] == 0
    assert out["status"] in ("vazio", "ok")
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError` ou função ausente)

- [ ] **Step 3: Implement `agents_site/corpus_local.py`**

Mapa domínio → globs (ajustar se paths mudarem):

```python
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

Dominio = Literal["mercado", "regulatorio", "engenharia", "tecnico"]

_ROOT = Path(__file__).resolve().parents[1] / "docs" / "agente" / "agentes_site" / "rag"

_GLOBS: dict[Dominio, tuple[str, ...]] = {
    "regulatorio": ("regulatorio_*.txt", "mapa_uf_cref_*.txt"),
    "engenharia": ("engenharia_*.txt",),
    "tecnico": ("tecnico_*.txt",),
    "mercado": ("mercado_*.txt",),  # pode ficar vazio até curadoria
}

_CHUNK = 1200
_OVERLAP = 200


def _tokenize(q: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9à-ü]{3,}", (q or "").lower())}


def _score(chunk: str, tokens: set[str]) -> int:
    low = chunk.lower()
    return sum(1 for t in tokens if t in low)


def buscar_corpus_local(
    pergunta: str, *, dominio: Dominio, n: int = 4
) -> dict:
    tokens = _tokenize(pergunta)
    hits: list[tuple[int, dict]] = []
    if not _ROOT.is_dir():
        return {
            "resultados": [],
            "n_docs": 0,
            "fonte": "corpus_local",
            "status": "indisponivel",
            "aviso_usuario": "Corpus local não encontrado no deploy.",
        }
    for pattern in _GLOBS.get(dominio, ()):
        for path in sorted(_ROOT.glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="replace")
            i = 0
            while i < len(text):
                chunk = text[i : i + _CHUNK]
                sc = _score(chunk, tokens) if tokens else 0
                if sc > 0:
                    hits.append(
                        (
                            sc,
                            {
                                "titulo": path.name,
                                "trecho": chunk.strip()[:800],
                                "uri": str(path.as_posix()),
                                "fonte": f"corpus_local:{path.name}",
                            },
                        )
                    )
                i += _CHUNK - _OVERLAP
    hits.sort(key=lambda x: -x[0])
    # dedupe por titulo+início
    seen: set[str] = set()
    resultados = []
    for _, row in hits:
        key = row["titulo"] + row["trecho"][:40]
        if key in seen:
            continue
        seen.add(key)
        resultados.append(row)
        if len(resultados) >= max(1, n):
            break
    return {
        "resultados": resultados,
        "n_docs": len(resultados),
        "fonte": f"corpus_local/{dominio}",
        "status": "ok" if resultados else "vazio",
    }
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
..\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/agents_site/test_corpus_local.py -q
```

- [ ] **Step 5: Commit** (se pedido)

```bash
git add agents_site/corpus_local.py tests/agents_site/test_corpus_local.py
git commit -m "feat(agents_site): deterministic local corpus retrieve for L2 fallback"
```

---

### Task 3: Facades L2 — Eros → corpus → stub (zero Discovery)

**Files:**
- Modify: `agents_site/tools.py` (funções `consultar_base_*`, `consultar_engenharia_obra`, `consultar_catalogo_equipamentos`)
- Modify: `tests/agents_site/test_no_vertex_in_facades.py` (deve passar)
- Modify: `tests/agents_site/test_facades_eros_first.py` se existir (não regredir)

**Interfaces:**
- Consumes: `_pack_eros_as_resultados`, `consultar_eros_*`, `buscar_corpus_local`
- Produces: mesmo shape `{resultados, n_docs, fonte}`; `fonte` nunca `"Vertex AI Search…"` no default

- [ ] **Step 1: Helper interno** (em `tools.py` ou `tools_l2_rag.py`):

```python
def _rag_cascade(
    pergunta: str,
    *,
    eros_env: str,
    eros_fn,
    dominio_corpus: str,
    fonte_eros: str,
) -> dict:
    if (os.getenv(eros_env) or "").strip():
        packed = _pack_eros_as_resultados(eros_fn(pergunta), fonte_eros)
        if packed and packed.get("n_docs", 0) > 0:
            return packed
    from agents_site.corpus_local import buscar_corpus_local

    local = buscar_corpus_local(pergunta, dominio=dominio_corpus, n=4)  # type: ignore[arg-type]
    if local.get("n_docs", 0) > 0:
        return local
    return {
        "resultados": [],
        "n_docs": 0,
        "fonte": f"corpus_local/{dominio_corpus}+eros",
        "status": "vazio",
        "aviso_usuario": (
            "A base qualitativa não cobriu esta pergunta. "
            "Use tools de números (Maps/IBGE) quando couber, ou diga que não há trecho."
        ),
    }
```

- [ ] **Step 2: Substituir corpo de cada facade** — remover `from tools.discovery_engine_tools import …` e ramo Vertex.

Exemplo `consultar_base_regulatoria`:

```python
def consultar_base_regulatoria(pergunta: str) -> dict:
    from agents_site.carimbo import anotar_retrieval_legal

    r = _rag_cascade(
        pergunta,
        eros_env="EROS_GROUP_ID_REGULATORIO",
        eros_fn=consultar_eros_regulatorio,
        dominio_corpus="regulatorio",
        fonte_eros="Eros RAG (regulatório CREF/Lei)",
    )
    return anotar_retrieval_legal(r, r.get("fonte") or "RAG regulatório")
```

Repetir para mercado / obra / catálogo (`dominio_corpus="tecnico"`).

Obra: manter reforço HVAC **depois** do Eros pack, **antes** do corpus fallback (mesma lógica de hints `_HVAC_HINTS`).

- [ ] **Step 3: Run**

```powershell
..\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/agents_site/test_no_vertex_in_facades.py tests/agents_site/test_facades_eros_first.py tests/agents_site/test_corpus_local.py -q
```

Expected: PASS

- [ ] **Step 4: Commit** (se pedido)

```bash
git add agents_site/tools.py tests/agents_site/
git commit -m "refactor(agents_site): L2 facades Eros then local corpus, drop Discovery"
```

---

### Task 4: Split módulos L1 / L2 / Eros (compat re-export)

**Files:**
- Create: `agents_site/tools_l1_dados.py` (mover funções L1 inventário)
- Create: `agents_site/tools_l2_rag.py` (facades + `_pack_eros` + `_rag_cascade`)
- Create: `agents_site/tools_eros.py` (factory)
- Modify: `agents_site/tools.py` → só `from … import *` / re-exports explícitos
- Modify: `agents_site/agent.py` imports (podem continuar `from agents_site.tools import …`)

**Interfaces:**
- Consumes: mesmos nomes públicos
- Produces: `agents_site.tools.consultar_base_mercado` etc. intactos

- [ ] **Step 1: Mover sem mudar lógica** — um módulo por vez; após cada move:

```powershell
..\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/agents_site/ -q --tb=line
```

- [ ] **Step 2: `tools.py` vira:**

```python
"""Re-export estável — L1 dados, L2 RAG, Eros."""
from agents_site.tools_l1_dados import *  # noqa: F403
from agents_site.tools_l2_rag import *  # noqa: F403
from agents_site.tools_eros import (  # noqa: F401
    consultar_eros_arquiteto,
    consultar_eros_engenharia,
    consultar_eros_mercado,
    consultar_eros_regulatorio,
    consultar_eros_tecnico,
)
```

Preferir lista explícita `__all__` se o time evitar star-import.

- [ ] **Step 3: Commit** (se pedido)

```bash
git add agents_site/tools*.py agents_site/tools_eros.py
git commit -m "refactor(agents_site): split L1 dados / L2 RAG / Eros modules"
```

---

### Task 5: L3 — prompts “só leitura” + docstring agent.py

**Files:**
- Modify: `agents_site/agent.py` (topo ainda diz “Vertex AI Search”)
- Modify: prompts Técnico/Reg/Mercado/Arq/Eng — uma linha canônica L3

**Interfaces:**
- Consumes: tools L1/L2
- Produces: instrução única:

```text
REGRA L3: Você só LÊ saídas de tools. Número/norma/modelo sem tool = proibido.
Se tool status=vazio/indisponivel, diga que a base não cobre — não complete de memória.
```

- [ ] **Step 1: Patch docstring módulo** — trocar “Vertex AI Search” por “Eros RAG / corpus local + tools determinísticas”.

- [ ] **Step 2: Inserir REGRA L3** no início do instruction de cada especialista (5 blocos).

- [ ] **Step 3: Smoke manual** (local API): pergunta CREF → `consultar_eros_regulatorio` ou corpus; pergunta “quantas academias Cocó” → `buscar_concorrentes` com total tool.

- [ ] **Step 4: Commit** (se pedido)

```bash
git add agents_site/agent.py
git commit -m "docs(agents_site): L3 read-only prompts; drop Vertex from agent docstring"
```

---

### Task 6: Discovery legado — stub only + env example

**Files:**
- Modify: `tools/discovery_engine_tools.py` — se `vertex_rag_enabled()` false, stub; se true, manter (ops emergencial)
- Modify: `.env.production.example` — `VERTEX_RAG_ENABLED=0`
- Grep callsites: garantir **zero** import de facades L2

- [ ] **Step 1: Grep**

```powershell
rg "discovery_engine_tools|buscar_conhecimento|buscar_catalogos" agents_site tools agents -g "*.py"
```

Expected: callsites só em `discovery_engine_tools.py` / testes legados / (opcional) consultor interno se ainda existir — **não** em facades site.

- [ ] **Step 2: Se `buscar_conhecimento_consultor` ainda usado no consultor logado** — documentar no SPEC como exceção ou migrar numa task futura (não misturar com degustação).

- [ ] **Step 3: Commit** (se pedido)

```bash
git add tools/discovery_engine_tools.py .env.production.example
git commit -m "chore: Vertex Discovery stub-only; VERTEX_RAG_ENABLED=0 in prod example"
```

---

### Task 7: Docs — SPEC_RAG + handoff + PIPELINE se preciso

**Files:**
- Modify: `agents_site/specs/SPEC_RAG_AGENTES_SITE.md` — tabela agente→Eros group→corpus glob (marcar Vertex DEPRECATED)
- Modify: `docs/handoffs/2026-08-04-vertex-off-eros-rag-parallel.md` — link spec+plan; checkbox corpus local
- Modify: `docs/arquitetura/PIPELINE_AGENTES.md` só se state keys / fonte RAG mudarem no relatório (geralmente não)

- [ ] **Step 1: Reescrever tabela mapa** (exemplo):

| Agente | Tool L2 | Eros env | Corpus glob |
|--------|---------|----------|-------------|
| Mercado | `consultar_base_mercado` | `EROS_GROUP_ID_MERCADO` | `mercado_*.txt` (se houver) |
| Técnico | `consultar_catalogo_equipamentos` | `EROS_GROUP_ID_TECNICO` | `tecnico_*.txt` |
| Regulatório | `consultar_base_regulatoria` | `EROS_GROUP_ID_REGULATORIO` | `regulatorio_*.txt` |
| Arquiteto/Eng | `consultar_engenharia_obra` | `EROS_GROUP_ID_ENGENHARIA` | `engenharia_*.txt` |

- [ ] **Step 2: Commit** (se pedido)

```bash
git add agents_site/specs/SPEC_RAG_AGENTES_SITE.md docs/handoffs/2026-08-04-vertex-off-eros-rag-parallel.md
git commit -m "docs: SPEC_RAG Eros+corpus; Vertex Discovery deprecated"
```

---

### Task 8: Ops Técnico Eros (bloqueio externo)

**Não é código.** Checklist Marcelo/ops:

- [ ] Criar grupo Eros Técnico + ingest catálogos Matrix/LF/TH
- [ ] Setar `EROS_GROUP_ID_TECNICO` em Cloud Run / `.env`
- [ ] Smoke: `consultar_catalogo_equipamentos("esteira Matrix")` → `n_docs>0`, `fonte` Eros

Até lá: corpus `tecnico_*.txt` + stub “não encontrei no catálogo”.

---

### Task 9 (opcional / paralelo): L1 coerce args str (padrão `dias`)

**Files:**
- Modify: tools L1 que fazem `int(raio_metros)`, `float(area_m2)`, etc.
- Pattern: já existe `_as_positive_int` em `tools/cnpj_fitness_tools.py` — extrair util compartilhado OU duplicar helper fino em `agents_site`

- [ ] **Step 1: Teste** `buscar_concorrentes(..., raio_metros="1000")` não TypeError
- [ ] **Step 2: Coerce no entry**
- [ ] **Step 3: pytest**

---

## Self-review

| Spec requirement | Task |
|------------------|------|
| Zero Vertex no happy path | 1, 3, 6 |
| Corpus local fallback | 2, 3 |
| Split L1/L2 | 4 |
| LLM só leitura | 5 |
| SPEC atualizado | 7 |
| Técnico Eros | 8 |
| Carimbo / coerce | design + Task 9; L1 carimbo já parcial em tools |

Placeholder scan: nenhum TBD de implementação — Task 8 é ops consciente.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-08-04-rag-deterministico-llm-leitura.md`.  
Design: `docs/superpowers/specs/2026-08-04-rag-deterministico-llm-leitura-design.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session, `executing-plans`, checkpoints  

**Which approach?**
