---
id: spec-a3a-002
agente: A3a CompetitorSearch
modelo_llm: determinístico sem LLM (BaseAgent)
versão: 2.0 (atualizada PONTO 11 — cascata de localização + incidente deps-reverse)
data: 2026-08-10
---

# SPEC — A3a CompetitorSearch

## 1. Responsabilidade única

O A3a é responsável exclusivamente por **buscar, enriquecer e classificar concorrentes físicos** no bairro-alvo, entregando ao pipeline um snapshot bruto e estruturado (`concorrentes_brutos`) pronto para análise agregada pelo A3b. Ele não faz análise, não pondera gaps de mercado, não calcula scores — apenas coleta dados via APIs externas e os grava no state de forma determinística, sem envolver LLM em nenhuma etapa.

---

## 2. Contrato de entrada

| Chave no `state` | Tipo | Origem |
|---|---|---|
| `bairro` | `str` (opcional, fallback de `market_context`) | A0 MarketContext / input do usuário |
| `cidade` | `str` (opcional, fallback de `market_context`) | A0 MarketContext / input do usuário |
| `market_context` | `dict` ou `str` (JSON/markdown fenced) | A0 MarketContext (`output_key="market_context"`) |

Extração realizada por `_extrair_bairro_cidade(state)` em `a3a_competitor_search.py`, que prioriza o topo do state e cai em `market_context.market_context.bairro/cidade` via `_parse_market_context`.

**RN-A3a-00 — Cascata de localização documentada (v2.0, PONTO 11)**
A extração de `bairro`/`cidade` segue a cascata:
1. **Raiz do state** (`state.get("bairro")`, `state.get("cidade")`) — origem: input direto do usuário via API
2. **`input_params`** (`state["input_params"]["bairro"]`, `state["input_params"]["cidade"]`) — origem: validação/pydantic
3. **`market_context` do A0** (`state["market_context"]["market_context"]["bairro"]`) — fallback final

Se todos os níveis retornarem vazio, a macro `analisar_concorrentes_a3a_completo` é chamada com strings vazias e retorna lista vazia + fallback heurístico no A3b. O incidente `deps-reverse` (A3a depender de dado que A0 ainda não gravou) foi resolvido garantindo que A0 roda antes de A3a na orquestração paralela.

---

## 3. Contrato de saída

**output_key / state_delta:** `concorrentes_brutos`

| Campo | Tipo | Descrição |
|---|---|---|
| `concorrentes_brutos` | `list[dict]` | Lista de concorrentes enriquecidos (reviews + Knowledge Panel + horários de pico) |
| `concorrentes_excluidos` | `list[dict]` | Itens descartados pelo filtro semântico `_eh_academia_tradicional` (ex: clínicas) |
| `redes_a0_solicitadas` | `list[str]` | Redes das quais A0 pediu busca balanceada |
| `redes_a0_cobertas` | `list[str]` | Redes efetivamente encontradas |
| `redes_a0_nao_encontradas` | `list[str]` | Redes pedidas mas não localizadas no raio |

Gravado via `EventActions(state_delta={"concorrentes_brutos": resultado})` — não via `output_key` de LLM.

---

## 4. Regras de negócio

**RN-A3a-01 — Fluxo determinístico em 1 macro-call**
A execução chama `analisar_concorrentes_a3a_completo(tool_context, bairro, cidade)` (em `tools/competitor_tools.py`, linha 2292). Esta macro encapsula em código Python: `buscar_concorrentes_balanceados` → filtro semântico → `buscar_reviews_academia` → `enriquecer_concorrente_via_google` (async/Playwright) → `classificar_dores_reviews_batch_gemini` (1 call Gemini Flash batch) → `aplicar_classificacao_dores`. Nenhum LLM orquestra o fluxo — é 100% Python.

**RN-A3a-02 — Cap de enriquecimento por latência**
Enriquece somente os `MAX_ENRIQUECIMENTO` (default **3**, via env) concorrentes com maior número de avaliações. Concorrentes além do cap ficam na lista com dados básicos (sem reviews/pico). Razão: enrichment sequencial é long-pole; cap 3 corta wall sem matar cobertura do top.

**RN-A3a-03 — Filtro semântico de tipo pré-enriquecimento**
Antes do enriquecimento, cada item passa por `_eh_academia_tradicional(c)`. Itens que não passam (ex: clínicas, estúdios de dança classificados pelo Google como fora do escopo) vão para `concorrentes_excluidos`. O filtro é binário e determinístico.

**RN-A3a-04 — Fail-soft total**
Qualquer exceção na macro é capturada no `except Exception` do `_run_async_impl`. O agente emite `_ERRO_VAZIO` (listas vazias + campo `"erro"`) em vez de derrubar o pipeline. O A3b sabe lidar com lista vazia (retorna análise de fallback heurística com `score_concorrencia=7.0`).

**RN-A3a-05 — Enriquecimento best-effort por concorrente**
Dentro de `_processar_um(c)`, tanto `enriquecer_concorrente_via_google` (Playwright Knowledge Panel) quanto `pesquisar_horarios_pico` (SearchAPI/popular_times) são best-effort: exceção individual vira campo de status (`scraping_status: "exception: ..."`) e não interrompe o processamento dos demais concorrentes.

**RN-A3a-06 — Sem LLM no agente**
O agente é `BaseAgent` (não `LlmAgent`). Não há chamada de LLM no `_run_async_impl`. A única chamada de modelo é o Gemini Flash batch dentro da macro-tool para classificação de dores de reviews (fora do ciclo de orquestração do ADK).

---

## 5. Critérios de aceite mensuráveis

- [ ] `state["concorrentes_brutos"]` existe após a execução e é `dict` com chave `concorrentes_brutos` sendo `list`.
- [ ] Em caso de falha total da macro, `state["concorrentes_brutos"]` contém `{"erro": "...", "concorrentes_brutos": [], ...}` — nunca `KeyError` ou ausência da chave.
- [ ] Nenhum token de LLM consumido pelo agente A3a em si (log de telemetria: `tokens_a3a == 0`).
- [x] Com `MAX_ENRIQUECIMENTO=3` (default), no máximo 3 concorrentes recebem reviews e horários de pico.
- [ ] Clínicas médicas ou estúdios de dança retornados pela busca inicial aparecem em `concorrentes_excluidos`, não em `concorrentes_brutos`.
- [ ] Smoke E2E: relatório completo gera `concorrentes_brutos.concorrentes_brutos` com lista não-vazia para cidades com academias mapeadas no Google Maps.

---

## 6. Comportamento em degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| `analisar_concorrentes_a3a_completo` lança exceção | Emite `_ERRO_VAZIO` + campo `"erro"` no state; pipeline continua para A3b |
| `enriquecer_concorrente_via_google` falha para 1 concorrente | Concorrente entra na lista com `enrichment_search_grounding_text=None`; os demais não são afetados |
| `pesquisar_horarios_pico` falha | Campo `horarios_pico` fica `None`; campo `dados_por_dia` fica vazio |
| `buscar_concorrentes_balanceados` retorna `{"erro": ...}` | Macro retorna envelope com `concorrentes_brutos: []` imediatamente; não processa enriquecimento |
| `market_context` ausente ou malformado | `_extrair_bairro_cidade` retorna strings vazias; `analisar_concorrentes_a3a_completo` é chamada com `bairro=""`, `cidade=""`; resultado é lista vazia com fallback heurístico no A3b |

---

## 7. Contexto para IA

**Gotcha 1 — BaseAgent, não LlmAgent:** O `CompetitorSearchAgent` herda de `google.adk.agents.BaseAgent` e implementa `_run_async_impl`. Não tem `instruction`, `tools` declarados no construtor nem `output_key`. A gravação no state é via `EventActions(state_delta=...)`, não via parsing de JSON do LLM.

**Gotcha 2 — Playwright Windows sync lock:** A macro roda `enriquecer_concorrente_via_google` de forma sequencial deliberada. Paralelização via `asyncio.gather` causava travamento do Playwright no Windows. (Histórico: o antigo A3c, hoje removido, sofria o mesmo lock ao paralelizar coroutines; sua função de oferta migrou para SearchAPI e foi fundida no A3b.) Não re-paralelizar o enriquecimento do A3a sem testar em Windows.

**Gotcha 3 — `_StateShim`:** A macro `analisar_concorrentes_a3a_completo` espera um `tool_context` com atributo `.state`. O agente cria um `_StateShim(state)` mínimo (apenas `__slots__ = ("state",)`) para compatibilidade com as tools que fazem `tool_context.state.get(...)`.

**Gotcha 4 — Custo zero de token A3a:** O refator de 2026-06-14 eliminou o LlmAgent que ecoava ~83k tokens por relatório. Qualquer regressão que reintroduza um `LlmAgent` aqui é custo não-intencional.

**Gotcha 5 — output_key vs state_delta:** A3a usa `state_delta` (BaseAgent), não `output_key` (LlmAgent). O A3b lê `state["concorrentes_brutos"]` — se o A3a for convertido para LlmAgent com `output_key="concorrentes_brutos"`, o JSON do LLM pode vir como string com markdown fence, quebrando `analisar_concorrentes_completo` no A3b.

**Gotcha 6 — Incidente deps-reverse resolvido (v2.0):** Houve incidente onde A3a tentava ler `market_context` antes do A0 gravar. Solução: orquestração agora garante A0 completo antes de disparar A3a, mesmo em execução paralela com A2/A4. Documentado na RN-A3a-00.
