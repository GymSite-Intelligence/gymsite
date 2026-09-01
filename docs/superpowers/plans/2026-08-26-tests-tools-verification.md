# tests/tools Verification Gate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate verificável para `tests/tools/` — script único, README, preview HTML de evidência — padrão Superpowers + P-000.

**Architecture:** Script PowerShell chama pytest no venv; resultado documentado em preview HTML versionado; spec define matriz tool→teste.

**Tech Stack:** Python 3.11, pytest, PowerShell, HTML estático em `docs/superpowers/previews/`.

**Spec:** [docs/superpowers/specs/2026-08-26-tests-tools-verification-design.md](../specs/2026-08-26-tests-tools-verification-design.md)

## Global Constraints

- Verifier: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tests/tools/ -v --tb=short`
- Superpowers `verification-before-completion`: zero claims sem output fresh
- Commits só se Marcelo pedir
- Não editar plan file após aprovação

---

### Task 1: Script verifier

**Files:**
- Create: `scripts/verify-tools-tests.ps1`

- [x] **Step 1:** Script cd repo root, roda pytest `tests/tools/`, exit code pytest
- [x] **Step 2:** Rodar script — confirmar 17 passed

---

### Task 2: README tests/tools

**Files:**
- Create: `tests/tools/README.md`

- [x] **Step 1:** Documentar verifier, matriz resumida, link spec/plan/preview

---

### Task 3: Preview evidência (Superpowers)

**Files:**
- Create: `docs/superpowers/previews/2026-08-26-tests-tools-matrix.html`

- [x] **Step 1:** HTML auto-contido — 17 testes, módulo, status PASS, comando verifier, timestamp UTC-3

---

### Task 4: Verification gate (obrigatório)

- [x] **Step 1:** Rodar `scripts/verify-tools-tests.ps1`
- [x] **Step 2:** Colar exit code + contagem no preview HTML metadata

**Evidence (2026-08-26):**

```
17 passed in ~2s
exit code: 0
command: .venv/Scripts/python.exe -m pytest tests/tools/ -v --tb=short
```
