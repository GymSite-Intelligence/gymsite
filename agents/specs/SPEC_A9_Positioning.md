---
id: spec-a9-002
agente: PositioningStrategist
modelo_llm: BaseAgent (sem LLM)
versao: 2.0
data: 2026-08-10
constitution: C2.1, C2.3, C4.4, C6.1
---

## 1. Responsabilidade Única

O A9 PositioningStrategist é um **agente determinístico (BaseAgent, sem LLM)** responsável por gerar **relatório estratégico de posicionamento via Framework ERRC** (Eliminar/Reduzir/Aumentar/Criar), mapa de serviços dos concorrentes, gaps reais de mercado, ticket recomendado e veredito de posicionamento (`OCEANO_AZUL` / `TRANSICAO` / `VERMELHO`). Consome outputs de A0–A6 já presentes no state ADK. Não realiza scraping, não acessa APIs externas de dados, não altera o relatório de viabilidade do A6.

**Mudança crítica vs v1.0:** A spec v1.0 descrevia um LlmAgent Pro (`gemini-2.5-pro` com `thinking_budget=8192`) que gerava ERRC/markdown/gaps via texto livre. O código real já era híbrido: tool computa headroom de renda e gaps reais deterministicamente, LLM só ecoava. Agora é BaseAgent puro: `_errc_deterministica()` monta ERRC/template a partir dos fatos de `inteligencia_competitiva` + `oferta_concorrentes`, `_avaliar_headroom_renda()` calcula veredito via `tools/posicionamento_renda`, `_gaps_reais()` contagem de penetração por serviço do catálogo fechado (16 entradas). Elimina variância, custo (Pro a menos/run) e risco de alucinação.

---

## 2. Contrato de Entrada

| Chave no `state` | Tipo | Origem |
|---|---|---|
| `market_context` | `dict` | A0 ContextBuilder |
| `candidatos_geoscout` | `dict` | A1 GeoScout |
| `analise_demografica` | `dict` | A2 DemoAnalyst |
| `inteligencia_competitiva` | `dict` | A3b CompetitorAnalysis |
| `oferta_concorrentes` | `dict` | A3b CompetitorAnalysis (fusão ex-A3c) |
| `concorrentes_brutos` | `list` | A3a CompetitorSearch (praça inteira p/ gaps) |
| `analise_financeira` | `dict` | A4 FinancialEstimator |
| `relatorio_md` | `str` | A6 ReportConsolidator |
| `demanda_futura` | `dict` | enrichment api.py (obras residenciais) |
| `demografia_bairro` | `dict` | A6 bridge after_agent (opcional p/ Brilliant Basics) |
| `input_params` / `cidade` / `bairro` / `uf` | `str` | root_agent / api.py |
| `relatorio_local_id` | `str` | A6 (ID local para patch do JSON) |
| `relatorio_id` | `str` | A6 (UUID Supabase para persistência) |

---

## 3. Contrato de Saída

**`output_key`**: `relatorio_posicionamento`

| Campo | Tipo | Produtor |
|---|---|---|
| `framework_errc` | `dict` (eliminar/reduzir/aumentar/criar: list[str]) | template determinístico (_errc_deterministica) |
| `mapa_servicos` | `list[dict]` (`{concorrente, servicos: {str: int}}`) | contagem de penetração (_servicos_do_concorrente) |
| `gaps_identificados` | `list[str]` | `_gaps_reais()` (penetração == 0 no catálogo) |
| `fonte_gaps` | `str` | `"deterministico_oferta_concorrentes (planos+IG)"` |
| `recomendacao_ticket` | `dict` (`ticket_recomendado`, `ticket_minimo`, `ticket_maximo`) | `_avaliar_headroom_renda()` |
| `veredito_posicionamento` | `str` (`OCEANO_AZUL` \| `TRANSICAO` \| `VERMELHO` \| `INDETERMINADO`) | `_avaliar_headroom_renda()` |
| `fonte_veredito` | `str` | `"deterministico_headroom_renda (IBGE Censo 2022)"` |
| `headroom_renda` | `dict` | output de `tools/posicionamento_renda.avaliar_posicionamento` |
| `justificativa_veredito` | `str` | template determinístico |
| `janela_de_entrada` | `dict` | `_montar_janela_entrada()` (usa `demanda_futura` se disponível) |
| `markdown` | `str` | template Markdown (_markdown_deterministico) |
| `fonte_geracao` | `str` | `"langcache"` (se cache hit) ou ausente |

---

## 4. Regras de Negócio

**RN-A9-01 — Veredito determinístico via headroom de renda**
`_avaliar_headroom_renda(cidade, uf, bairro, concorrentes)` chama `tools/posicionamento_renda.avaliar_posicionamento()`. Se `hr["status"] == "ok"` e `hr["veredito_posicionamento"] != "INDETERMINADO"`, o veredito é usado diretamente. Caso contrário, fallback para template padrão. Padrão idêntico ao A4 (tool computa, LLM narra → agora tool computa, template narra).

**RN-A9-02 — Gaps reais sobrepõem gaps LLM**
`_gaps_reais()` conta penetração por serviço do catálogo `_SERVICOS_CATALOGO` (16 entradas) via `_servicos_do_concorrente()`. Serviços com `penetração == 0` são os gaps reais. O LLM recebia "Nutrição/Recovery/Silver" por reflexo; agora substitui pelo dado real da praça.

**RN-A9-03 — Catálogo de 16 serviços é fechado**
`_SERVICOS_CATALOGO` (linha 267 do código original): mapeamento fixo de chaves de modalidade para rótulos. GAP = serviço com penetração < 3 em todos os concorrentes. Proibido inventar serviço fora da lista real injetada.

**RN-A9-04 — LangCache com threshold 0.97**
Busca no LangCache com `similarity_threshold=0.97` (configurável via `LANGCACHE_A9_SIMILARITY`). Threshold elevado (vs 0.88 padrão) para evitar false positive entre bairros com chave parecida (incidente Fortaleza documentado). Chave inclui `relatorio_id`, `cidade`, `bairro`, `tipo_negocio`, `hash_top5_concorrentes`.

**RN-A9-05 — Cache hit preserva idempotência**
Verifica `meta.get("langcache_hit")` antes de chamar `langcache_set` — evita re-persistir hit como novo entry. `fonte_geracao = "langcache"` é marcado no output final.

**RN-A9-06 — Output deve ser JSON puro (dict), sem markdown fence**
`relatorio_posicionamento` no state é dict parsed, não string JSON bruta. `_parse_json_from_text()` foi removido — o BaseAgent grava dict direto.

**RN-A9-07 — Coerência financeira obrigatória**
Aluguel SEMPRE no formato `R$ X/m² para Y–Z m² (≈ R$ W/mês)`. Proibido recalcular — usar exclusivamente `analise_financeira` (A4). Números financeiros no markdown devem bater com o JSON do A4. Entidades com nome completo na primeira menção.

**RN-A9-08 — `janela_de_entrada` só com dado real**
Se não houver `demanda_futura` no state → `janela_de_entrada: {"tem_demanda_futura": false}`. Proibido inventar obras.

**RN-A9-09 — Validação leniente do schema**
Chama `validar_lenient(A9Output, relatorio, agente="A9")`. Divergências são logadas, não excepcionadas (C6.2).

**RN-A9-10 — Fail-soft absoluto**
Qualquer exceção resulta em `{"erro": "<ExceptionType>: <msg>", "raw_output": ...}` no state. O pipeline continua; posicionamento fica indisponível mas viabilidade não é afetada.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] `state["relatorio_posicionamento"]` existe após execução e é um dict.
- [ ] `veredito_posicionamento` final quando `headroom_renda.status == "ok"` deve ter `fonte_veredito == "deterministico_headroom_renda (IBGE Censo 2022)"`.
- [ ] `gaps_identificados` quando `_gaps_reais()` retorna lista não-vazia deve ter `fonte_gaps == "deterministico_oferta_concorrentes (planos+IG)"`.
- [ ] LangCache HIT não gera nova entrada no cache (idempotência).
- [ ] LangCache threshold mínimo para keys `positioning_a9:*` >= 0.97 (configurável, default).
- [ ] `janela_de_entrada.tem_demanda_futura == false` quando `demanda_futura` ausente no state.
- [ ] JSON malformado do LLM não interrompe o pipeline (não há LLM — erro de template vira `{"erro": ...}`).
- [ ] `_patch_relatorio_json()` atualiza `output_consolidado.posicionamento_estrategico` sem sobrescrever o resto.
- [ ] Cobertura de testes unitários de `_avaliar_headroom_renda`, `_gaps_reais`, `_errc_deterministica` >= 80% (C4.1).

---

## 6. Comportamento em Degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| `tools/posicionamento_renda` indisponível ou `status != "ok"` | `_avaliar_headroom_renda()` captura `Exception`, loga WARNING, mantém veredito padrão `"INDETERMINADO"` |
| `_gaps_reais()` retorna `None` (sem concorrentes no state) | `gaps_identificados = []`; `fonte_gaps = "nenhum_concorrente_mapeado"` |
| LangCache indisponível (serviço down) | Callback captura `Exception`, retorna `None`; geração segue sem cache |
| Exception genérica no template | Grava `{"erro": "<ExceptionType>: <msg>"}` no state; Supabase persist não é chamado |
| `supabase_writer.write_posicionamento_failsafe()` falha | Loga WARNING; JSON local já foi patched e é fonte de verdade |
| `_patch_relatorio_json()` — arquivo não encontrado | Loga WARNING; state `relatorio_posicionamento` já gravado |

---

## 7. Contexto para IA

**Gotcha #1 — BaseAgent, não LlmAgent:**
O A9 foi migrado de LlmAgent para BaseAgent em 2026-08. O código em `agents/a9_positioning_strategist.py` é um `BaseAgent` puro que chama as macros diretamente. Não há `tools=[]`, não há `before_model_callback`, não há function_call. Qualquer spec que mencione LLM para A9 está obsoleta.

**Gotcha #2 — `output_key` grava dict, não string:**
`relatorio_posicionamento` no state é dict parsed, não string JSON bruta. `_parse_json_from_text()` foi removido — o BaseAgent grava dict direto via `EventActions(state_delta={...})`.

**Gotcha #3 — LangCache false positive entre bairros:**
Threshold 0.88 causava o mesmo JSON de posicionamento para Parangaba e Meireles (Fortaleza) porque os primeiros 1024 chars das chaves eram iguais. Fix: threshold 0.97 + inclusão do `relatorio_id` e `hash_top5_concorrentes` na chave.

**Gotcha #4 — `_resolve_location_from_state` fallback em cascata:**
`cidade`/`bairro` podem estar em `state["input_params"]`, `state["cidade"]`, ou dentro de `market_context` (extraído via `_parse_market_context`). A função tenta as três fontes. Se nenhuma retorna, `_avaliar_headroom_renda()` retorna sem ação (sem erro).

**Gotcha #5 — `oferta_concorrentes` vem do A3b (ex-A3c fundido):**
O agente A3c foi removido; o A3b determinístico passou a mapear a oferta (site via httpx + Instagram via SearchAPI, sem Playwright) e gravar `oferta_concorrentes`. `_resumo_oferta_e_gaps()` lê `planos_precos.inclui` + as modalidades já mescladas em `inteligencia_competitiva.concorrentes_detalhados[*].servicos_oferecidos` (A3b). Mesmo se a oferta vier vazia, a função degrada sem erro.

**Gap C6.4 conhecido:**
`InMemorySessionService` — estado A9 (posicionamento parsed) vive em memória durante a sessão ADK. Crash entre A9 completar e `_patch_relatorio_json` completar pode perder o posicionamento do JSON local. Supabase via `write_posicionamento_failsafe` é o fallback de recuperação.

---

## 8. Fora de Escopo

**Fora de escopo do A9:**
- Buscar concorrentes (A3a)
- Calcular viabilidade financeira (A4)
- Gerar relatório de viabilidade (A6)
- Validar zoneamento/certas (fora de escopo — usar dado A4)
- Traduzir reviews EN→PT (fora de escopo, ver PONTO 13)
- Investigar web de endereços específicos (Playwright)
- Rodar antes do A6 (A9 é pós-A6, after-A9 tem A8 validator)
