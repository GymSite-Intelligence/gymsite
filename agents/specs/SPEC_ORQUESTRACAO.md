# SPEC_ORQUESTRACAO.md

| Campo | Valor |
|-------|-------|
| **ID** | spec-orch-001 |
| **Agente / Área** | Orquestração GymSitePipeline — `gymsite_intelligence/agent.py` |
| **Modelo LLM** | Root agent: `gemini-2.5-flash`; agentes delegados têm modelos próprios |
| **Versão** | 2.0 (atualizada PONTO 30, A8 → after-A9) |
| **Data** | 2026-08-10 |

---

## 1. Responsabilidade Única (C6.1)

O módulo `gymsite_intelligence/agent.py` define a **topologia de orquestração** do pipeline de viabilidade: compõe os agentes A0–A6 e A9 em grafos ADK (`SequentialAgent`, `ParallelAgent`), aplica telemetria/observabilidade centralizada via `_attach_telemetry`, e expõe `root_agent` como ponto de entrada do ADK Runner. Não contém lógica de negócio; toda lógica vive nos agentes e tools individuais.

---

## 2. Contrato de Entrada / Saída

### Entrada (root_agent recebe do usuário)

O `root_agent` (`GymSiteIntelligence`, `gemini-2.5-flash`) extrai parâmetros da mensagem natural:

| Parâmetro | Obrigatoriedade | Valores possíveis / Default |
|-----------|-----------------|------------------------------|
| `cidade` + `estado` | Obrigatório | ex: "Fortaleza, CE" |
| `bairro` | Opcional | qualquer bairro |
| `tamanho_preset` | Opcional | `pp` / `p` / `m` (★ default) / `g` / `gg` |
| `tipo_negocio` | Opcional | `academia` (default) / `crossfit_box` / `studio_pilates` / `studio_funcional` / `outro` |
| `genero_alvo` | Opcional | `misto` (default) / `predominantemente_feminino` / `predominantemente_masculino` / `exclusivamente_feminino` / `exclusivamente_masculino` |
| `bairros_indicados` | Modo Crowdsource | lista de bairros sugeridos por terceiros |

**Roteamento:** qualquer pedido de análise → `transfer_to_agent("GymSitePipeline")`.

### Sequência de Execução (GymSitePipeline)

```
root_agent (GymSiteIntelligence)
  └── GymSitePipeline [SequentialAgent]
        ├── A0 ContextBuilder         # Deep Research de mercado
        ├── A1 GeoScout               # Localização + candidatos
        ├── ParallelAnalysis [ParallelAgent]
        │     ├── A2 DemoAnalyst      # IBGE demográfico
        │     ├── CompetitorPipeline [SequentialAgent]
        │     │     ├── A3a CompetitorSearch   # busca Maps/OSM/CNPJ
        │     │     └── A3b CompetitorAnalysis # reviews + scores
        │     └── A4 FinancialEstimator        # 3 cenários financeiros
        ├── A6 ReportConsolidator     # relatório executivo
        ├── A9 PositioningStrategist  # ERRC + veredito posicionamento
        └── (A8 ValidadorCruzado)     # after-A9: validação cruzada via tools/a8_runner.run_a8_validation()
```

**Agentes fora do pipeline de viabilidade:**
- **A5 ContactHunter**: definido e importado, mas não incluído no `GymSitePipeline` (linha 163–165 de `agent.py`). Pertence à rota de prospecção (VEC-410 / Apollo people_search), não à viabilidade. Remover custo ~R$0,17/relatório e 1 step de latência.
- **A3c CompetitorMapper**: REMOVIDO (jun/2026). Era `LlmAgent` dead code; sua função (mapear oferta) foi fundida no A3b determinístico. A oferta migrou Playwright→SearchAPI, matando o crash sync/async no Windows (run `9213f40d`).
- **A7 MarketResearch**: importado como função dentro de A3a/A4 (não como AgentTool no grafo).
- **A8 ValidadorCruzado**: invocado via `tools/a8_runner.run_a8_validation()` dentro do `after_agent_callback` do **A9** (PONTO 29). Não é nó do grafo. Validação ocorre após posicionamento estar disponível para validar coerência do ERRC e veredito.

### Saída (state keys produzidas ao longo do pipeline)

| Chave | Produtor | Tipo |
|-------|----------|------|
| `market_context` | A0 | dict / str JSON |
| `candidatos_geoscout` | A1 | list |
| `analise_demografica` | A2 | dict |
| `inteligencia_competitiva` | A3b | dict / str JSON |
| `analise_financeira` | A4 | dict |
| `relatorio_md` | A6 | str markdown |
| `relatorio_posicionamento` | A9 | dict |
| `relatorio_posicionamento_md` | A9 (output_key) | str JSON bruta |

---

## 3. Regras de Negócio

**RN-ORCH-001 — Topologia: Sequential > Parallel > Sequential interno**
`GymSitePipeline` é `SequentialAgent`. `ParallelAnalysis` (`ParallelAgent`) executa A2, `CompetitorPipeline` e A4 em paralelo. `CompetitorPipeline` é `SequentialAgent` interno (A3a → A3b) para garantir que A3b consome o output de A3a. Não existe garantia de ordem dentro do `ParallelAgent` entre A2, A3 e A4.

**RN-ORCH-002 — `_attach_telemetry` é centralizado e idempotente**
`_attach_telemetry(*agents)` (linha 77) aplica em cada agente:
1. Wrap do modelo string → `Gemini(retry_options=HttpRetryOptions(attempts=4, initial_delay=2.0, max_delay=60.0, exp_base=2.0, http_status_codes=[429,503,500]))` — retenta a CHAMADA de modelo, não o pipeline inteiro.
2. `before_agent_callback`: chain de `_otel_before` (spans OpenTelemetry) + `_progress_before` (etapa_atual no banco).
3. `after_model_callback`: `_telemetry_after_model` (tokens CSV). Só em `LlmAgent` — BaseAgent determinístico (A3a) pula pela checagem `"after_model_callback" in model_fields` (linha 98).
4. `after_agent_callback`: chain de `_otel_after` + `_state_dump` + `_progress_after`.
`_chain_callbacks` (linha 63) deduplica por identidade — sem risco de double-call se `build_llm_agent` já injetou o callback.

**RN-ORCH-003 — `build_llm_agent` é a factory canônica (C5.2/C5.4/C7.2)**
Agentes LLM são construídos via `tools/agent_factory.build_llm_agent()`. A factory aplica retry + telemetria na construção — agentes fora do Runner (A7, A8, root_agent) ficam instrumentados mesmo sem passar pelo `_attach_telemetry`.

**RN-ORCH-004 — Retry de modelo é por chamada (não por pipeline)**
`_RETRY_OPTIONS = HttpRetryOptions(attempts=4, ...)` (linha 21). Um `429 RESOURCE_EXHAUSTED` da Vertex (frequente em `gemini-2.5-pro` do A6/A9) retenta a chamada individual. Sem isso, o pipeline inteiro retornaria ao início (~10 min re-rodando A0–A5).

**RN-ORCH-005 — A5 ContactHunter excluído da viabilidade**
A5 foi removido do `GymSitePipeline` explicitamente (linha 163). Responsabilidade separada: viabilidade responde "devo abrir?"; prospecção responde "quem contatar?" (conforme `feedback_separar_viabilidade_prospeccao`). Qualquer PR que reinsira A5 no pipeline principal exige justificativa de negócio.

**RN-ORCH-006 — A3c fundido no A3b (removido do grafo)**
`competitor_mapper_agent` foi REMOVIDO (arquivo `agents/a3c_competitor_mapper.py` deletado). O `CompetitorPipeline` é só A3a → A3b. O A3b (BaseAgent determinístico) absorveu o mapeamento de oferta: chama `mapear_oferta_competidores_completo` (site via httpx + Instagram via SearchAPI `engine=instagram_profile`, sem Playwright/Outscraper) e mescla os serviços por concorrente, gravando `oferta_concorrentes` no state.

**RN-ORCH-010 — A8 roda no after-A9, não after-A6 (PONTO 29)**
O A8 ValidadorCruzado agora é invocado pelo `after_agent_callback` do **A9 PositioningStrategist**, não mais pelo A6. Esta mudança (implementada em ago/2026) permite que a validação cruzada inclua a coerência do framework ERRC e o veredito de posicionamento, que só estão disponíveis após o A9 completar. O `tools/a8_runner.run_a8_validation()` recebe o output consolidado do A9 (`relatorio_posicionamento`) e valida contra os dados estruturados do A6.

**RN-ORCH-007 — Modo Crowdsource detectado pelo root_agent**
Palavras-chave: "indicações da comunidade", "formulário", "campanha", "pesquisa", "votação" ou lista de bairros sugeridos por terceiros. Ativa `bairros_indicados=[...]` na delegação. A6 renderiza seção especial "Demanda Social Detectada".

**RN-ORCH-008 — Callbacks são fail-safe absolutos**
`_attach_telemetry` envolve todo o bloco em `try/except: pass` (linha 117). Falha de telemetria, progresso ou state dump nunca bloqueia o pipeline.

**RN-ORCH-009 — `InMemorySessionService` é o gap C6.4**
O ADK usa `InMemorySessionService` por default. Estado do pipeline não é recuperável após crash do processo. Não há persistência externa de checkpoints de orquestração. O JSON local (`metrics/relatorios/<id>.json`) e o Supabase são fontes de verdade dos outputs, mas a sessão ADK em si não é recuperável.

---

## 4. Critérios de Aceite Mensuráveis

| Critério | Limiar |
|----------|--------|
| **CA-ORCH-01** — Pipeline completo A0→A6→A9 produz `relatorio_md` (str) e `relatorio_posicionamento` (dict) no state | 100% em smoke E2E |
| **CA-ORCH-02** — A2, A3 (A3a→A3b) e A4 executam em paralelo (sem dependência de output entre si) | Verificável por logs de span OpenTelemetry simultâneos |
| **CA-ORCH-03** — 429/503/500 do modelo não reinicia o pipeline; retenta a chamada | Máximo 4 tentativas por chamada de modelo, pipeline não reinicia |
| **CA-ORCH-04** — `tokens_pipeline.csv` contém entradas para todos os agentes LLM do run | 1 entrada por agente LLM por run |
| **CA-ORCH-05** — `etapa_atual` / `etapas_concluidas` atualizados no banco após cada agente | Verificável via Supabase `relatorios.progresso` |
| **CA-ORCH-06** — Falha de telemetria/progresso não interrompe pipeline | Pipeline completa mesmo com `_attach_telemetry` levantando exceção internamente |
| **CA-ORCH-07** — A5 ausente do `GymSitePipeline.sub_agents` | Verificável por inspeção do grafo |
| **CA-ORCH-08** — `root_agent` responde a pedido de análise com `transfer_to_agent("GymSitePipeline")` e não tenta gerar relatório diretamente | 100% |

---

## 5. Comportamento em Degradação (C4.4)

| Falha | Comportamento |
|-------|---------------|
| A0 falha (Deep Research indisponível) | Pipeline para em A0; sem `market_context` os demais agentes falham em cascata. A0 tem fallback Gemini Search Grounding |
| A3b falha (análise competitiva) | `ParallelAnalysis` reporta erro; A4 pode continuar sem `inteligencia_competitiva`; A6 consolida com dados parciais |
| A4 falha | `ParallelAnalysis` reporta erro; A6 consolida sem cenários financeiros |
| A6 falha | Pipeline para; A9 não executa; JSON local não gerado |
| A9 falha (JSON malformado) | `after_agent_callback` do A9 grava erro no state; pipeline completa sem posicionamento |
| A8 falha | Lógica dentro do `after_agent_callback` do **A9** captura a exceção; relatório de viabilidade é emitido sem `validacao_a8` |
| Retry de modelo esgotado (4 tentativas) | Exceção propagada para o agente → pipeline reporta falha no agente específico |
| `_attach_telemetry` falha em qualquer callback | `try/except: pass` garante que pipeline continua; telemetria parcialmente perdida |

---

## 6. Contexto para IA

**Gotcha #1 — A8 não é nó do grafo, roda no after-A9 (PONTO 29).**
`A8ValidadorCruzado` é invocado pelo `after_agent_callback` do **A9 PositioningStrategist**, não pelo `GymSitePipeline` ou A6. Adicionar `a8_validator_agent` ao `SequentialAgent` seria arquiteturalmente incorreto (A8 não é LlmAgent e duplicaria a validação). A mudança para after-A9 permite validar coerência do framework ERRC e veredito de posicionamento que só existem após o A9 completar.

**Gotcha #2 — `_attach_telemetry` + `build_llm_agent` são redundantes por design.**
`build_llm_agent` já aplica retry + telemetria. `_attach_telemetry` no `agent.py` aplica novamente. `_chain_callbacks` deduplica por identidade e o wrap de retry só roda quando `model` ainda é string (a segunda passagem encontra um objeto `Gemini` e pula). A redundância é intencional: garante que agentes criados sem a factory também fiquem instrumentados.

**Gotcha #3 — `after_model_callback` em BaseAgent determinístico.**
A3a é `BaseAgent` (não chama modelo). `"after_model_callback" in getattr(type(ag), "model_fields", {})` (linha 98) retorna `False` para BaseAgent → skip do chain de telemetria de modelo. Sem essa guarda, o `_attach_telemetry` levantaria `AttributeError` ao tentar setar `after_model_callback` em A3a.

**Gotcha #4 — Ordem de chain nos callbacks importa.**
`_attach_telemetry` encadeia na ordem: `otel_before` → `progress_before` (before); `otel_after` → `state_dump` → `progress_after` (after). Alterar a ordem pode fazer `state_dump` rodar antes do estado ser atualizado pelo `otel_after`.

**Gotcha #5 — `oferta_concorrentes` agora vem do A3b (ex-A3c).**
Com a fusão, `oferta_concorrentes` passa a ser gravado pelo A3b no mesmo passo da análise competitiva (não há mais agente A3c separado). O A9 `_resumo_oferta_e_gaps()` consome a oferta mesclada em `inteligencia_competitiva.concorrentes_detalhados[*].servicos_oferecidos`.

**Gap C6.4 — `InMemorySessionService` (conhecido, sem mitigação atual):**
O state de orquestração vive apenas em memória durante a sessão ADK. Não há checkpoint externo recuperável. Em caso de crash do processo durante o pipeline, o usuário precisa re-submeter a análise do zero. Mitigação futura: `DatabaseSessionService` (Supabase) ou `VertexAISessionService`.

**Gap C7.2 — A0 e A1 sem telemetria de tokens confirmada:**
O `after_model_callback` de tokens (`_telemetry_after_model`) foi wired via `_attach_telemetry`. Porém, conforme memória do projeto (`project_gymsite_pipeline_agents.md`), A0 e A1 não tinham telemetria confirmada. Verificar entradas em `metrics/tokens_pipeline.csv` para A0 e A1 antes de marcar C7.2 como conforme.
