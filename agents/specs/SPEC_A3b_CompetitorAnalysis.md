---
id: spec-a3b-001
agente: A3b CompetitorAnalysis
modelo_llm: gemini-2.5-flash-lite
versão: 1.0
data: 2026-06-18
---

# SPEC — A3b CompetitorAnalysis

## 1. Responsabilidade única

O A3b é responsável exclusivamente por **agregar os dados brutos de concorrentes em inteligência competitiva estruturada**: calcula gaps de mercado, dores dominantes, estratégia de counter-programming, nível de saturação e score de concorrência, e adiciona dois campos textuais (`posicionamento_recomendado`, `resumo_executivo`). Não faz busca de dados externos — isso é do A3a. Não gera análise financeira — isso é do A4.

---

## 2. Contrato de entrada

| Chave no `state` | Tipo | Origem |
|---|---|---|
| `concorrentes_brutos` | `dict` (com chave `concorrentes_brutos: list`) ou `list[dict]` direto | A3a CompetitorSearch (`state_delta`) |
| `bairro` | `str` (lido internamente pela macro-tool via `tool_context.state`) | A0 / input |
| `cidade` | `str` (lido internamente pela macro-tool via `tool_context.state`) | A0 / input |

A macro `analisar_concorrentes_completo(tool_context)` acessa `tool_context.state.get("concorrentes_brutos")` diretamente — o LLM NÃO passa o payload como argumento.

---

## 3. Contrato de saída

**output_key:** `inteligencia_competitiva`

| Campo | Tipo | Produtor |
|---|---|---|
| `inteligencia_competitiva.concorrentes_detalhados` | `list[dict]` | macro-tool + LLM (adiciona `reviews_traduzidas`) |
| `inteligencia_competitiva.dores_dominantes` | `list[dict]` | macro-tool (`analisar_gap_competitivo`) |
| `inteligencia_competitiva.servicos_nao_oferecidos` | `list[str]` | macro-tool |
| `inteligencia_competitiva.oportunidades_rankeadas` | `list` | macro-tool |
| `inteligencia_competitiva.score_oportunidade_mercado` | `float` | macro-tool |
| `inteligencia_competitiva.melhor_avaliada` / `pior_avaliada` | `dict` | macro-tool |
| `estrategia_counter_programming` | `dict` | macro-tool (`analisar_picos_competitivos`) |
| `nivel_saturacao` | `str` (`BAIXO\|MEDIO\|ALTO\|SATURADO`) | macro-tool (`classificar_saturacao`) |
| `rating_medio_concorrentes` | `float` | macro-tool |
| `score_concorrencia` | `float` | macro-tool (`calcular_score_concorrencia`) |
| `distribuicao_geografica` | `list[dict]` com `bairro/count/academias` | macro-tool |
| `total_concorrentes_analisados` | `int` | macro-tool |
| `posicionamento_recomendado` | `str` | LLM (texto livre baseado nos gaps) |
| `resumo_executivo` | `str` (max 3 frases) | LLM |

Após emissão do `output_key`, o callback `_a3b_filtrar_concorrentes` aplica filtro autoritativo determinístico sobre `inteligencia_competitiva.concorrentes_detalhados`.

---

## 4. Regras de negócio

**RN-A3b-01 — Macro-tool sem argumentos (anti-MALFORMED)**
O LLM deve chamar `analisar_concorrentes_completo()` **sem argumentos**. Qualquer argumento — especialmente `concorrentes_brutos` — causa `MALFORMED_FUNCTION_CALL` (bug documentado VEC-380, 2026-05-09). O payload de enrichment contém `enrichment_search_grounding_text` de 1k+ chars por concorrente; reenviá-lo na function_call corrompe o protocolo gRPC do ADK. A macro lê o state internamente.

**RN-A3b-02 — Proibição de tools legadas**
O LLM não deve chamar `analisar_gap_competitivo`, `analisar_picos_competitivos`, `classificar_saturacao` ou `calcular_score_concorrencia` separadamente. Essas foram consolidadas na macro. O nome correto é exatamente `analisar_concorrentes_completo` — sem prefixo de namespace (bug `default_api.analisar_concorrentes_completo` documentado no run 56d17ea0).

**RN-A3b-03 — LLM como redator, não como calculador**
Todos os campos numéricos e estruturados (`score_concorrencia`, `nivel_saturacao`, `rating_medio_concorrentes`, `distribuicao_geografica`, etc.) são retornados pela macro-tool e devem ser copiados literalmente. O LLM só é autorizado a redigir `posicionamento_recomendado` e `resumo_executivo`, e a adicionar `reviews_traduzidas` em `concorrentes_detalhados`.

**RN-A3b-04 — Tradução de reviews para PT-BR**
Reviews em idioma estrangeiro (frequentemente inglês no Google Maps) devem ser traduzidas para PT-BR. O campo `reviews_traduzidas` é adicionado pelo LLM sobre os campos da macro. Cada item: `quote_pt_br`, `quote_original`, `idioma_original`, `autor`, `rating`, `data_relativa`, `categoria_dor`. Nomes próprios não são traduzidos.

**RN-A3b-05 — Preservação de campos do slim**
O LLM não deve omitir campos da macro em `concorrentes_detalhados`: `endereco`, `bairro_concorrente`, `tem_24h`, `telefone`, `website`, `horarios_pico`. Esses campos alimentam o CRM e o relatório final.

**RN-A3b-06 — Filtro pós-agente `_a3b_filtrar_concorrentes` (after_agent_callback)**
Após emissão, `_a3b_filtrar_concorrentes` (registrado como `after_agent_callback`) aplica deterministicamente via `filtrar_concorrentes_bairro_tipo` (em `tools/competitor_tools.py`, linha 333):
- Remove academias com status `CLOSED_*` do Places (mantém `OPERATIONAL` e desconhecido).
- Filtra por bairro: mantém apenas quem tem o bairro-alvo no NOME ou ENDEREÇO (não em `bairro_concorrente` — campo corrompível pelo parser de endereço). Salvaguarda: mantém todos se nenhum casa.
- Filtra por tipo: descarta off-type (CrossFit/Artes Marciais em relatório de `academia`) se sobrarem ≥2 on-type.
- É best-effort: qualquer exceção interna é silenciada (`except Exception: pass`), nunca derruba o pipeline.

**RN-A3b-07 — Validação leniente do contrato de saída (C6.2)**
Dentro de `_a3b_filtrar_concorrentes`, após o filtro, é chamado `validar_lenient(InteligenciaCompetitiva, inner, agente="A3b")` (em `models/pipeline_schemas.py`). Divergências são logadas, não excepcionadas.

**RN-A3b-08 — Fallback com concorrentes_brutos vazio**
Se `analisar_concorrentes_completo` receber lista vazia, retorna estrutura de fallback heurística com `score_concorrencia=7.0` e aviso `"concorrentes_brutos vazio — análise heurística de fallback"`. O pipeline continua.

---

## 5. Critérios de aceite mensuráveis

- [ ] `state["inteligencia_competitiva"]` existe após execução e contém `concorrentes_detalhados` como lista.
- [ ] `score_concorrencia` é numérico (float), nunca string ou null.
- [ ] `distribuicao_geografica` está presente e é lista de dicts com `bairro`, `count`, `academias`.
- [ ] Nenhum campo do slim (`endereco`, `telefone`, `website`, `tem_24h`) está ausente em `concorrentes_detalhados` quando a macro os retornou.
- [ ] Academias com `business_status=PERMANENTLY_CLOSED` ou `CLOSED_TEMPORARILY` são removidas pelo callback (verificável comparando tamanho da lista antes/depois via log).
- [ ] Para bairro com academias fora do bairro-alvo (ex: Aldeota em relatório de Cocó), elas são removidas pelo callback se existirem academias no bairro-alvo.
- [ ] Smoke E2E: A3b não emite `OUT=0` (ausência de `output_key` no state) com 3+ concorrentes no A3a.
- [ ] Validação `InteligenciaCompetitiva` (Pydantic) sem erros críticos para saída típica de 5 concorrentes.

---

## 6. Comportamento em degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| `concorrentes_brutos` ausente ou vazio no state | `analisar_concorrentes_completo` retorna fallback heurístico; A3b emite análise de baixa saturação com aviso |
| LLM tenta chamar tool com argumento | ADK retorna `MALFORMED_FUNCTION_CALL`; A3b emite `OUT=0` — este é o failure mode histórico, não uma degradação graceful. Prevenido pela instrução `nota_critica` no prompt |
| LLM omite `posicionamento_recomendado` ou `resumo_executivo` | A6 lê a chave normalmente; campos ficam ausentes no relatório final (degradação visual, não crash) |
| `_a3b_filtrar_concorrentes` lança exceção | `except Exception: pass` silencia; state permanece com a saída original não-filtrada |
| Todos reviews em inglês | LLM adiciona `reviews_traduzidas`; relatório em PT-BR com indicação `[original em inglês]` |

---

## 7. Contexto para IA

**Gotcha 1 — Histórico OUT=0 (MALFORMED):** A3b foi o agente com mais regressões no projeto. Causa raiz documentada (VEC-380): LLM tentava reenviar `concorrentes_brutos` como argumento de function_call, corrompendo o payload. A solução (macro sem args) é frágil — se o prompt mudar e o LLM "ajudar" passando o payload, o bug retorna. O `nota_critica` no fluxo obrigatório é linha de defesa primária.

**Gotcha 2 — Namespace de tool:** O ADK injeta as tools sem namespace. Chamar `default_api.analisar_concorrentes_completo` em vez de `analisar_concorrentes_completo` causa "Tool not found" e OUT=0 (documentado no run 56d17ea0).

**Gotcha 3 — `bairro_concorrente` não confiável:** O filtro `filtrar_concorrentes_bairro_tipo` usa NOME e ENDEREÇO para inferir bairro, não `bairro_concorrente`. Razão: o parser de endereço do Places às vezes taggeia academias de Papicu como "Cocó". O campo `bairro_concorrente` pode existir mas é informativo, não autoritativo para filtro.

**Gotcha 4 — Flash Lite com thinking:** O `_GENERATE_CONFIG` é criado como `types.GenerateContentConfig()` sem `thinking_budget`. O episódio de 2026-05-08 com `thinking_budget=8192` causou OUT=0 (budget consumiu o output). Não adicionar thinking_budget ao A3b sem teste isolado.

**Gotcha 5 — after_agent_callback vs after_tool_callback:** O filtro `_a3b_filtrar_concorrentes` é registrado em `competitor_analysis_agent.after_agent_callback` (pós-emissão do output_key), não como after_tool_callback. Isso garante que o filtro roda sobre o JSON final emitido pelo LLM, não sobre o retorno da tool.
