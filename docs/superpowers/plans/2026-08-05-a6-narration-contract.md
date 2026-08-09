# A6 Narration Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align A6 narration with the current listing+MRLR pipeline and make crowdsource rendering depend only on structured input.

**Architecture:** Keep Gemini as the long-form Markdown narrator, but remove obsolete business data from its instruction. Inject deterministic Markdown for alternative neighborhoods, crowdsource, offers, entrants, and MRLR; retain the post-generation aligner as the authority for scores and Top3.

**Tech Stack:** Python, Google ADK callbacks, pytest.

## Global Constraints

- Numbers shown to users come from tools/state, never from the LLM.
- Viability rent is MRLR; SearchAPI listings provide candidates and display-only `price_raw`.
- `tests/test_a6.py` remains the fixed Steinberger verifier gate.
- Use the project interpreter at `C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe`.

---

### Task 1: Lock the Current Narration Contract

**Files:**
- Create: `tools/test_a6_narration_contract.py`
- Modify: `tools/test_a6_referencia_aluguel.py`

**Interfaces:**
- Consumes: `report_consolidator_agent.instruction`, A6 rendering helpers.
- Produces: regression coverage for structured crowdsource, MRLR-only rent narration, and removal of obsolete POI language.

- [x] Write tests asserting the instruction has no POI tie-breaker, no keyword crowdsource heuristic, no hardcoded city recommendations, and no unconditional indirect-signal warning.
- [x] Write tests for `_renderizar_secao_crowdsource(state)` using only `input_params.bairros_indicados`.
- [x] Replace the old portal/Grounding rent test with MRLR rendering and MRLR-unavailable behavior.
- [x] Run the focused tests and confirm they fail because the new behavior is absent.

### Task 2: Implement Deterministic Narration Inputs

**Files:**
- Modify: `agents/a6_report_consolidator.py`

**Interfaces:**
- Produces: `_renderizar_secao_crowdsource(state: dict) -> str`.
- Preserves: `_renderizar_secao_referencia_aluguel(inner_fin: dict) -> str`.

- [x] Render crowdsource Markdown only from a non-empty structured list, deduplicated in input order.
- [x] Inject the crowdsource section in `_a6_before_model_callback`.
- [x] Persist `bairros_indicados` in `input_canonico`.
- [x] Rewrite rent reference rendering to expose MRLR facts only; when MRLR is unavailable, emit an explicit validation warning without portal/Grounding values.
- [x] Run focused tests until green.

### Task 3: Simplify and Correct the A6 Instruction

**Files:**
- Modify: `agents/a6_report_consolidator.py`
- Update: `docs/arquitetura/PIPELINE_AGENTES.md`

**Interfaces:**
- Consumes: deterministic sections injected by callbacks.
- Produces: a shorter instruction aligned with listing+MRLR and structured crowdsource.

- [x] Consolidate date and integrity rules at the top.
- [x] Remove hardcoded alternative-neighborhood data and retain only the rule to copy the injected section.
- [x] Remove the POI tie-breaker and describe the already-ranked composite Top3 as read-only.
- [x] Replace indirect-heuristic listing language with `qualidade_sinal` and conditional warnings.
- [x] Add a short pre-emission checklist while keeping deterministic post-alignment authoritative.
- [x] Run the fixed A6 gate, focused narration tests, and existing A6 regression suite.
