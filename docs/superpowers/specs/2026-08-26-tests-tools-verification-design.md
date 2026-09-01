# tests/tools — Verification Gate Design

**Date:** 2026-08-26  
**Status:** Approved for implementation  
**Scope:** `tests/tools/` — pytest offline para tools determinísticas do pipeline/listings/security

## Problem

Testes de tools vivem espalhados (`tests/tools/`, alguns em `tools/test_*.py`, `pdf/test_*.py`). Sem gate único documentado, agente pode:

- Rodar scan HTTP prod confundindo com pytest
- Afirmar "passou" sem comando fresh (viola Superpowers `verification-before-completion`)
- Ignorar `.venv/Scripts/python.exe` e quebrar em Python 3.13 global

## Goal

Um **verifier canônico** + **matriz tool→teste** versionada, no padrão Superpowers deste repo (`docs/superpowers/specs` + `plans` + `previews`).

## Architecture

```
scripts/verify-tools-tests.ps1
        │
        ▼
.venv/Scripts/python.exe -m pytest tests/tools/ -v --tb=short
        │
        ▼
docs/superpowers/previews/2026-08-26-tests-tools-matrix.html  (evidência visual)
```

## Matriz tool → teste (2026-08-26)

| Módulo | Arquivo teste | Invariante protegido |
|--------|---------------|-------------------|
| `tools/listing_candidato_normalize.py` | `test_listing_candidato_normalize.py` | Drop fora cidade; score distância; área/endereço obrigatórios |
| `tools/candidato_viabilidade_rank.py` | `test_candidato_viabilidade_rank.py` | **Nunca `price_raw`**; payback norm; rank composto geo+payback |
| `agents/a6_report_consolidator.py` | `test_a6_top3_mrlr_md.py` | Top3 MD com carimbo MRLR; aviso sem viabilidade |
| `tools/security_audit/` | `test_security_audit_smoke.py` | Registry 8 scanners; config gymsite; skip user_enum |

**Total:** 4 módulos · 17 testes · 0 rede

## Global constraints (P-000)

- Verifier: `.venv/Scripts/python.exe -m pytest` — nunca `pytest` solto
- Escopo gate: só `tests/tools/` nesta fase (não expandir para `tools/test_*.py` sem PR separado)
- Números financeiros nos testes: MRLR/aluguel — nunca `price_raw` de listing
- Preview HTML em `docs/superpowers/previews/` — evidência versionada

## Out of scope

- Cobertura 100% de `tools/`
- Scan HTTP prod (`security_audit` manual)
- CI obrigatório no merge (opcional futuro)

## Success criteria

1. `scripts/verify-tools-tests.ps1` exit 0
2. `tests/tools/README.md` aponta verifier + matriz
3. Preview HTML lista 17/17 PASS com timestamp e comando
