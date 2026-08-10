---
id: spec-a3b-002
agente: CompetitorAnalysis
modelo_llm: BaseAgent (sem LLM)
versao: 2.0
data: 2026-08-10
constitution: C2.1, C2.3, C4.4, C6.1
---

## 1. Responsabilidade Única

O A3b CompetitorAnalysis é um **agente determinístico (BaseAgent, sem LLM)** responsável por **agregar dados brutos de concorrentes em inteligência competitiva estruturada**: calcula gaps de mercado, dores dominantes, estratégia de counter-programming, nível de saturação e score de concorrência. Produz também `oferta_concorrentes` (fusão do ex-A3c) mapeando modalidades via SearchAPI (site + Instagram). O A3b **não faz busca externa** — isso é do A3a. Não gera análise financeira — isso é do A4.

**Mudança crítica vs v1.0:** A spec v1.0 descrevia um LlmAgent que chamava `analisar_concorrentes_completo()` e re-emitia o JSON + 2 campos de texto (`posicionamento_recomendado`, `resumo_executivo`). O LLM não produzia número — só ecoava a macro, e o fazia mal: dropava campos (`telefone`, `website`, `tipos`), exigindo after_agent_callback corretor. Pior: re-enviar payload grande causava `MALFORMED_FUNCTION_CALL` / `OUT=0` (histórico de regressões 05/2026). Agora é BaseAgent: roda a macro direto, sintetiza textos por template determinístico, funde oferta A3c inline. Elimina crash, zera custo-token e remove conserto pós-LLM.

---

## 2. Contrato de Entrada

| Chave no `state` | Tipo | Origem |
|---|---|---|
| `concorrentes_brutos` | `dict` ou `list[dict]` | A3a CompetitorSearch (`state_delta`) |
| `market_context` | `dict` | A0 ContextBuilder (fallback para bairro/cidade/tipo) |
| `input_params.tipo_negocio` | `str` | usuário via `api.py` (default: `"academia"`) |

A macro `analisar_concorrentes_completo(tool_context)` acessa `tool_context.state.get("concorrentes_brutos")` diretamente — não há function_call do LLM.

---

## 3. Contrato de Saída

**`output_key`**: `inteligencia_competitiva`

**State delta adicional:** `oferta_concorrentes` (fusão A3c)

| Campo | Tipo | Produtor |
|---|---|---|
| `inteligencia_competitiva.concorrentes_detalhados` | `list[dict]` | macro-tool + filtro determinístico |
| `inteligencia_competitiva.dores_dominantes` | `list[dict]` | macro-tool (`analisar_gap_competitivo`) |
| `inteligencia_competitiva.servicos_nao_oferecidos` | `list[str]` | macro-tool |
| `inteligencia_competitiva.oportunidades_rankeadas` | `list` | macro-tool |
| `inteligencia_competitiva.score_oportunidade_mercado` | `float` | macro-tool |
| `inteligencia_competitiva.melhor_avaliada` / `pior_avaliada` | `dict` | macro-tool |
| `estrategia_counter_programming` | `dict` | macro-tool (`analisar_picos_competitivos`) |
| `nivel_saturacao` | `str` (`BAIXO|MEDIO|ALTO|SATURADO`) | macro-tool (`classificar_saturacao`) |
| `rating_medio_concorrentes` | `float` | macro-tool |
| `score_concorrencia` | `float` | macro-tool (`calcular_score_concorrencia`) |
| `distribuicao_geografica` | `list[dict]` | macro-tool |
| `total_concorrentes_analisados` | `int` | macro-tool |
| `posicionamento_recomendado` | `str` | template determinístico (_sintetizar_textos) |
| `resumo_executivo` | `str` | template determinístico |
| `oferta_concorrentes` | `dict` | macro-tool `mapear_oferta_competidores_completo` (fusão A3c) |

---

## 4. Regras de Negócio

**RN-A3b-01 — Macro-tool única, sem LLM**
O agente chama `analisar_concorrentes_completo(_StateShim(state))` diretamente via Python. Não há function_call, não há LLM, não há re-interpretação.

**RN-A3b-02 — Filtro determinístico inline**
`_filtrar_envelope(envelope, state)` aplica in-place o filtro `filtrar_concorrentes_bairro_tipo`:
- Remove academias com status `CLOSED_*` do Places
- Filtra por bairro: mantém quem tem bairro-alvo no NOME ou ENDEREÇO
- Filtra por tipo: descarta off-type (CrossFit/Artes Marciais) se sobrarem ≥2 on-type
- Best-effort: qualquer exceção é silenciada (`except Exception: pass`)

**RN-A3b-03 — Síntese de textos por template**
`_sintetizar_textos(envelope)` monta `posicionamento_recomendado` e `resumo_executivo` deterministicamente a partir dos fatos da macro (dores, serviços, oportunidades, saturação, score). Nenhum número/fato novo — só os do envelope. Mesmo papel do antigo texto-livre do LLM, sem alucinação.

**RN-A3b-04 — Fusão A3c (oferta de concorrentes)**
O agente executa `mapear_oferta_competidores_completo(_StateShim(tmp))` inline, onde `tmp["inteligencia_competitiva"] = envelope`. Resultado em `oferta_concorrentes` é mesclado em `concorrentes_detalhados[*].servicos_oferecidos` via `_mesclar_servicos_na_oferta`. Sem essa fusão, serviço que o concorrente tem (mas só aparece no site/IG) vira gap FALSO → ERRC manda "CRIAR" algo que já existe.

**RN-A3b-05 — Validação leniente do contrato**
Após filtragem e fusão, chama `validar_lenient(InteligenciaCompetitiva, inner, agente="A3b")`. Divergências são logadas, não excepcionadas (C6.2).

**RN-A3b-06 — Fail-soft absoluto**
Qualquer exceção na macro resulta em envelope de erro com `score_concorrencia=7.0`, `nivel_saturacao="BAIXO"` e aviso descritivo. Nunca derrubar o pipeline.

**RN-A3b-07 — Tradução de reviews removida**
Tradução de reviews EN→PT foi removida do caminho determinístico (PONTO 13). Reviews ficam no idioma original com `categoria_dor`. Se quiser PT, religar via narrador opcional (Claude headless + guardrail), como A6/A9.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] `state["inteligencia_competitiva"]` existe após execução e contém `concorrentes_detalhados` como lista.
- [ ] `state["oferta_concorrentes"]` existe (pode ser dict vazio se fallback).
- [ ] `score_concorrencia` é numérico (float), nunca string ou null.
- [ ] `distribuicao_geografica` está presente e é lista de dicts com `bairro`, `count`, `academias`.
- [ ] Campos do slim (`endereco`, `telefone`, `website`, `tem_24h`) estão presentes em `concorrentes_detalhados` quando a macro os retornou.
- [ ] Academias com `business_status=PERMANENTLY_CLOSED` ou `CLOSED_TEMPORARILY` são removidas pelo filtro.
- [ ] Para bairro com academias fora do bairro-alvo, elas são removidas se existirem academias no bairro-alvo.
- [ ] Smoke E2E: A3b não emite `OUT=0` com 3+ concorrentes no A3a.
- [ ] Validação `InteligenciaCompetitiva` (Pydantic) sem erros críticos para saída típica de 5 concorrentes.

---

## 6. Comportamento em Degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| `concorrentes_brutos` ausente ou vazio | `analisar_concorrentes_completo` retorna fallback heurístico com `score_concorrencia=7.0` e aviso; pipeline segue |
| Macro lança exceção | Envelope de erro com estrutura mínima preenchida; `aviso` com `<ExceptionType>: <msg>` |
| Filtro `_filtrar_envelope` lança exceção | `except Exception: pass` silencia; envelope permanece não-filtrado |
| Fusão A3c (`mapear_oferta_competidores_completo`) falha | `oferta_concorrentes = {}`; análise competitiva segue sem oferta |
| Todos reviews em inglês | Reviews permanecem em inglês com `categoria_dor`; sem tradução (fora de escopo) |

---

## 7. Contexto para IA

**Gotcha #1 — BaseAgent, não LlmAgent:**
O A3b foi migrado de LlmAgent para BaseAgent em 2026-08. O código em `agents/a3b_competitor_analysis.py` é um `BaseAgent` puro que chama a macro diretamente. Não há `tools=[]`, não há `before_model_callback`, não há function_call. Qualquer spec que mencione LLM para A3b está obsoleta.

**Gotcha #2 — Histórico OUT=0 (MALFORMED):**
A3b foi o agente com mais regressões no projeto. Causa raiz: LLM tentava reenviar `concorrentes_brutos` como argumento de function_call, corrompendo o payload. A solução (macro sem args) era frágil. Agora, sem LLM, o bug é impossível.

**Gotcha #3 — Namespace de tool não se aplica:**
Na v1.0, o ADK injetava tools sem namespace. Chamar `default_api.analisar_concorrentes_completo` causava "Tool not found". Na v2.0, a macro é importada e chamada diretamente — sem risco de namespace.

**Gotcha #4 — `bairro_concorrente` não confiável:**
O filtro `filtrar_concorrentes_bairro_tipo` usa NOME e ENDEREÇO para inferir bairro, não `bairro_concorrente`. Razão: o parser de endereço do Places às vezes taggeia academias de Papicu como "Cocó".

**Gotcha #5 — after_agent_callback virou inline:**
Na v1.0, o filtro `_a3b_filtrar_concorrentes` era registrado em `after_agent_callback`. Na v2.0, roda inline antes do yield — mais simples, sem chain de callback.

**Gap C6.4 conhecido:**
`InMemorySessionService` — estado A3b vive em memória durante a sessão ADK. Crash entre A3b completar e A4 iniciar pode perder `inteligencia_competitiva`. O `output_key` é a fonte de verdade primária.

---

## 8. Fora de Escopo

**Fora de escopo do A3b:**
- Buscar concorrentes brutos (A3a)
- Calcular viabilidade financeira (A4)
- Gerar relatório final (A6)
- Validar posicionamento (A9)
- Traduzir reviews EN→PT (fora de escopo, ver PONTO 13)
- Investigar web de endereços específicos (Playwright)
