# PRD — Agentes de Marketing "in-house" (SEO + Meta) no código GymSite

> Complementa o `PRD Storage Agentes Marketing.md` (que define a base de conhecimento/Data Store).
> Este documento define a **implementação dos agentes dentro do código** do GymSite, no mesmo
> padrão ADK dos 5 agentes do site (`agents_site/agent.py`), em vez de uma ilha no Vertex Agent Studio.
> Status: **preparado, não implementado.** Decisão de storage (pgvector vs Vertex Search) em aberto.

## 1. Objetivo

Trazer os 2 agentes de marketing (Especialista SEO e Especialista Meta/Instagram-Facebook),
hoje rascunhados no Vertex AI Agent Studio, para o código do projeto — reusando o padrão dos 5
agentes consultores, as ferramentas já existentes e o interruptor de modelo (`LLM_PROVIDER`).

**Por quê:** evitar um 4º stack de RAG isolado (fragmentação), ter controle/custo, e permitir que
os agentes de mkt rodem no mesmo cérebro (Gemini ou modelo local) do resto da casa.

## 2. Decisões e pendências

| Item | Decisão | Status |
|---|---|---|
| Onde os agentes moram | No código, padrão `agents_site/agent.py` | ✅ decidido |
| Roteador | **Próprio** (`agents_marketing/`), separado do roteador público de degustação (público/guardrails diferentes) | ✅ decidido |
| Modelo | `GYMSITE_SITE_MODEL` + interruptor `LLM_PROVIDER` (gemini/local) | ✅ decidido |
| Storage do RAG de marketing | pgvector (`kb_chunks`) **ou** Vertex AI Search | ⏳ **em aberto** |
| Busca web/URL | Tools da casa (`gemini_search_grounding` / `deep_research_tool`), não `GoogleSearchTool` do Studio | ✅ decidido |

## 3. Reaproveitamento do export do Agent Studio

O export do Studio serve para o **conteúdo** (personas), não para o encanamento.

| Parte | Reaproveita? | Ação |
|---|---|---|
| Persona SEO (E-E-A-T, long-tail, CTR) | ✅ | Copiar, limpar aspas escapadas, endurecer p/ padrão da casa |
| Persona Meta (hooks, CTA, Reels×Carrossel) | ✅ | Idem |
| Split SEO vs Meta sob roteador | ✅ | Vira 2 `sub_agents` no padrão dos 5 |
| `GoogleSearchTool` | 🟡 trocar | `tools/gemini_search_grounding.py` / `tools/deep_research_tool.py` |
| `url_context` | 🟡 trocar | Fetch da casa (deep research) |
| `AgentTool`-wrapping de cada tool | 🟡 simplificar | Anexar direto; ver ressalva built-in (§6) |
| `GlobalGemini` / `gemini-3.5-flash` | 🟡 trocar | `GYMSITE_SITE_MODEL` + `LLM_PROVIDER` |
| Grounding na base da marca | 🔴 **falta** | Criar `consultar_marketing()` (§5) |
| Instagram real dos concorrentes | 🔴 **falta** | Reusar `tools/instagram_profile.py` (add-on IG) |

## 4. Arquitetura proposta

```
agents_marketing/agent.py
  root_marketing (roteador)
    ├── especialista_seo      → tools: consultar_marketing(), buscar_web(), fetch_url()
    └── especialista_meta     → tools: consultar_marketing(), instagram_profile(), buscar_web()
```

- Mesmo padrão de `agents_site/agent.py`: `Agent(...)` com `instruction`, `description`, `tools`,
  `generate_content_config`, roteamento por `transfer_to_agent` (ou roteador determinístico por
  código, como validado no lab — ver `lab_ollama/run_site_roteador_codigo.py`).
- Modelo via `GYMSITE_SITE_MODEL`; chamadas passam pelo interruptor `services/consultor/model_provider.py`
  (`LLM_PROVIDER=gemini|local`) para poder rodar Gemini ou Qwen local.

## 5. A base de conhecimento de marketing (o que dá valor)

Segue a taxonomia/metadados/chunking do `PRD Storage Agentes Marketing.md`, aplicada na infra escolhida:

- **Taxonomia** (`docs/marketing/`): `branding/`, `posts_conteudo/`, `campanhas/`, `pesquisa_mercado/`.
- **Chunking** (PRD): texto 512 tokens / 10% overlap; planilha (CSV/XLSX) linha→JSON; imagem→VLM (OCR+descrição).
  - ⚠️ O `scripts/batch/ingest_kb.py` hoje faz 2400 chars fixo + PDF por página, sem CSV→JSON e sem imagem.
    Se for pgvector, precisa evoluir o ingestor (512 tokens + tabular + imagem) + filtro de metadado no
    `match_kb_chunks`.
- **Metadados** (PRD): `content_type`, `department_owner`, `access_level`, `freshness_timestamp`, `topic_tags`
  → cabem no `metadados` (jsonb) do `kb_chunks`.
- **Lições internas que o PRD não cobre (aplicar por cima):** PDF envenena número (cuidar dos relatórios de
  465/561 páginas), formato Q&A recupera melhor que prosa, teste de recuperação estatístico (N≥3), carimbo
  fonte·data. Ver a SPEC de RAG dos agentes do site.
- **Ferramenta:** `consultar_marketing(pergunta, filtros)` — grounding obrigatório antes de citar
  cor/slogan/hashtag/persona. Sem isso, reprova o teste Dia dos Pais (§7).

Inventário de arquivos novos: `python scripts/batch/preview_kb_source.py --dir docs/marketing --check-db`.

## 6. Ressalva técnica (built-in tools do ADK)

`GoogleSearchTool` (grounding nativo) não convive no mesmo agente com function tools (como
`consultar_marketing()`). Por isso o Studio embrulha cada busca num sub-agente (`AgentTool`).
Recomendação: usar a busca própria da casa (`gemini_search_grounding`, que é function tool normal),
evitando o embrulho e convivendo com o RAG.

## 7. Critérios de aceite (do PRD Storage)

- Coerência textual média ≥ 4/5; recusa de fora-de-escopo ≥ 99%; alucinação factual < 2%.
- **Teste Dia dos Pais** (gabarito): o Meta deve usar cores `#FF5733`/`#2C3E50`, slogan
  "Conectando Histórias", hashtag `#ConexaoPaterna` e CTA pra bio — tudo vindo do `guia_marca` via
  `consultar_marketing()`, não inventado. É o teste que prova o grounding.

## 8. Fases

| Fase | Entrega |
|---|---|
| 0 | Este PRD + inventário (`preview_kb_source.py`) — **feito** |
| 1 | Decidir storage (pgvector vs Vertex Search) |
| 2 | Ingerir `docs/marketing/` na infra escolhida (chunking do PRD + metadados) |
| 3 | `agents_marketing/agent.py`: 2 especialistas no padrão dos 5, personas limpas, tools da casa + `consultar_marketing()` |
| 4 | Roteador (transfer ou determinístico) + `generate_content_config` + escopo/guardrails |
| 5 | Homologação: teste Dia dos Pais + métricas de aceite |
| 6 | (opcional) rodar sob modelo local via `LLM_PROVIDER=local` |

## 9. Arquivos de referência

- `agents_site/agent.py` — padrão dos 5 agentes (copiar a forma).
- `services/consultor/model_provider.py` — interruptor Gemini↔local.
- `tools/discovery_engine_tools.py` — RAG Vertex AI Search (se caminho Vertex).
- `services/kb_rag.py` + `scripts/batch/ingest_kb.py` — RAG pgvector (se caminho pgvector).
- `tools/gemini_search_grounding.py` / `tools/deep_research_tool.py` — busca web da casa.
- `tools/instagram_profile.py` — dados reais de IG (add-on).
- `scripts/batch/preview_kb_source.py` — inventário dry-run da pasta.
- `docs/marketing/PRD Storage Agentes Marketing.md` — base de conhecimento (storage).
