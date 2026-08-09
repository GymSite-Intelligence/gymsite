# Handoff — Sair do Vertex: RAG Eros + LLM paralelo

**Data:** 2026-08-04  
**Repo:** `gymsite`  
**Humano:** Marcelo  

---

## 1. Decisão

Projeto **sai do Vertex Discovery** como fonte de RAG dos agentes.  
Alimentação qualitativa = **Eros** (`knowledge-ask` / grupos).  

**Dois eixos paralelos** (não misturar):

| Trilha | O quê | Vertex? | Status |
|--------|--------|---------|--------|
| **A — RAG chat/degustação** | grounding dos 5 especialistas | Discovery **off** (`VERTEX_RAG_ENABLED=0`) | Mercado/Reg/Eng Eros; Técnico aguarda ingest |
| **B — LLM relatório A0–A9** | Gemini/NVIDIA no SequentialAgent | `PIPELINE_LLM_PROVIDER=nvidia` + `GOOGLE_GENAI_USE_VERTEXAI=false` (local) | **Feito 2026-08-04** — factory resolve LiteLlm; restart API |
| **C — NLP barato** (opcional) | DistilBERT intent / sentiment reviews | n/a | `2026-08-02-nlp-pipeline-a0-a9.md` — spikes, não bloqueia A/B |

Relatório que falhou **não** se conserta com Eros RAG — precisa trilha **B** (NVIDIA/`SITE` já nvidia; pipeline A0–A9 ainda Vertex).

---

## 2. Mapa atual (GymSite)

| Facade / tool | Backend alvo | Env |
|---------------|--------------|-----|
| `consultar_base_mercado` | Eros Metodologia | `EROS_GROUP_ID_MERCADO=7b471b98-…` |
| `consultar_base_regulatoria` | Eros Regulatório | `EROS_GROUP_ID_REGULATORIO=b7dad505-…` |
| `consultar_engenharia_obra` | Eros Engenharia | `EROS_GROUP_ID_ENGENHARIA=f087bfc8-…` |
| `consultar_eros_arquiteto` | fallback → Engenharia se `ARQUITETO` vazio | opcional UUID próprio |
| `consultar_catalogo_equipamentos` / `consultar_eros_tecnico` | Eros Técnico | **`EROS_GROUP_ID_TECNICO` ainda vazio** |
| SearchAPI / MRLR / IBGE | inalterados | não são Vertex Discovery |

Eros Mercado 58k Receita: grupo aggregate separado (`b2bce16f-…`) — ver `2026-08-03-eros-mercado-timeout.md` (fechado).

---

## 3. Trabalho paralelo (owners)

### Trilha A — GymSite (esta sessão / follow-up)

1. Facades Eros-first (mercado/reg/obra/catalog) — `_pack_eros_as_resultados`.
2. Smoke: `consultar_eros_mercado("tendencia academias")`, `consultar_eros_regulatorio("CREF PJ")`, `consultar_eros_engenharia("NBR 6120")`.
3. Eros: criar/ingest grupo **Técnico** (catálogos Matrix/LF/TH) → setar `EROS_GROUP_ID_TECNICO`.
4. Opcional: grupo Arquiteto próprio ou manter fallback Engenharia.
5. Atualizar `SPEC_RAG_AGENTES_SITE.md` quando Técnico verde.

### Trilha B — LLM pipeline (2026-08-04)

1. `tools/pipeline_model.py` + `build_llm_agent` → `PIPELINE_LLM_PROVIDER=nvidia` (LiteLlm).
2. `.env` local: `GOOGLE_GENAI_USE_VERTEXAI=false` + `PIPELINE_LLM_PROVIDER=nvidia`.
3. Restart `uvicorn` pra recarregar agentes.
4. Maps Places 403 = key/billing Maps — paralelo, não Eros.

### Trilha C — NLP (baixo prioridade vs A/B)

Spikes intent/sentiment — handoff 2026-08-02. Sem DistilBERT no meio A0–A9.

---

## 4. Aceite

- [x] Chat degustação: Reg/Eng/Mercado com `fonte` Eros ou corpus local, `n_docs>0` ou “base não cobre” — **nunca** 403 Discovery  
- [ ] Técnico: Eros group ingest + `EROS_GROUP_ID_TECNICO` (corpus `tecnico_*.txt` já fallback)  
- [x] Relatório A0–A9: 1 run local sem `PERMISSION_DENIED` billing Vertex (`PIPELINE_LLM_PROVIDER=nvidia`) — ver run `25f5e40f-…`  
- [x] `VERTEX_RAG_ENABLED=0` em prod example  
- [x] Facades site: Eros → corpus local → stub (`corpus_local.py`, split L1/L2/Eros)  

Spec/plan: `docs/superpowers/specs/2026-08-04-rag-deterministico-llm-leitura-design.md` · `docs/superpowers/plans/2026-08-04-rag-deterministico-llm-leitura.md` 

---

## 5. Mensagem curta

> RAG dos agentes = Eros. Vertex Discovery = legado off.  
> Relatório A0–A9 que quebrou = **LLM/billing Vertex**, outra trilha — paralelizar com RAG, não confundir.
