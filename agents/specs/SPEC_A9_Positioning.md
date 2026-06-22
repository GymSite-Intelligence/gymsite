# SPEC_A9_Positioning.md

| Campo | Valor |
|-------|-------|
| **ID** | spec-a9-001 |
| **Agente / Área** | A9 PositioningStrategist — Análise estratégica de posicionamento (Framework ERRC) |
| **Modelo LLM** | `gemini-2.5-pro` com `ThinkingConfig(thinking_budget=8192)` |
| **Versão** | 1.0 |
| **Data** | 2026-06-18 |

---

## 1. Responsabilidade Única (C6.1)

O A9 consome os outputs de A0–A6 já presentes no state ADK e gera um **relatório estratégico de posicionamento** via Framework ERRC (Eliminar / Reduzir / Aumentar / Criar), mapa de serviços dos concorrentes, gaps reais de mercado, ticket recomendado e veredito de posicionamento (`OCEANO_AZUL` / `TRANSICAO` / `VERMELHO`). Não realiza scraping, não acessa APIs externas de dados, não altera o relatório de viabilidade do A6.

---

## 2. Contrato de Entrada / Saída

### Entradas (state keys consumidas)

| Chave no State | Origem | Descrição |
|----------------|--------|-----------|
| `market_context` | A0 ContextBuilder | Deep Research de mercado (parse via `_parse_market_context`) |
| `candidatos_geoscout` | A1 GeoScout | Candidatos de localização |
| `analise_demografica` | A2 DemoAnalyst | Perfil demográfico IBGE |
| `inteligencia_competitiva` | A3b CompetitorAnalysis | Concorrentes + reviews + scores |
| `oferta_concorrentes` | A3b CompetitorAnalysis (oferta fundida do ex-A3c) | Oferta real por concorrente (quando disponível) |
| `analise_financeira` | A4 FinancialEstimator | Cenários financeiros (payback, capex, aluguel) |
| `contato_decisor` | A5 ContactHunter | Decisores (informativo) |
| `relatorio_md` | A6 ReportConsolidator | Relatório de viabilidade |
| `demanda_futura` | A6 / pipeline | Obras residenciais no raio (Apêndice B) |
| `input_params` / `cidade` / `bairro` / `uf` | root_agent | Localização para override determinístico |
| `relatorio_local_id` | A6 | ID local para patch do JSON |
| `relatorio_id` | A6 | UUID Supabase para persistência |

**Injeções no prompt pelo `before_model_callback`:**
- `_a9_inject_oferta_e_gaps()` (linha 361): bloco `[DADO REAL — OFERTA DOS CONCORRENTES]` calculado deterministicamente via `_resumo_oferta_e_gaps()` + `_servicos_do_concorrente()` + `_detectar_modalidades()`
- `_a9_inject_demanda_futura()` (linha 373): bloco `DEMANDA FUTURA DATADA` quando `state["demanda_futura"]` disponível

### Saída

**Output key ADK:** `relatorio_posicionamento_md` (string JSON bruta do LLM)

**State após `after_agent_callback`:**
```python
state["relatorio_posicionamento"] = {
  "framework_errc": {"eliminar": [...], "reduzir": [...], "aumentar": [...], "criar": [...]},
  "mapa_servicos": [{"concorrente": str, "servicos": {str: int}}],  # escala 0-10
  "gaps_identificados": [...],          # sobreposto por _gaps_reais() se disponível
  "gaps_identificados_llm": [...],      # backup do gaps LLM quando sobreposto
  "fonte_gaps": str,                    # "deterministico_oferta_concorrentes (planos+IG)"
  "recomendacao_ticket": {"ticket_recomendado": int, "ticket_minimo": int, "ticket_maximo": int, ...},
  "veredito_posicionamento": str,       # sobreposto por _a9_override_veredito_deterministico
  "veredito_posicionamento_llm": str,   # backup do veredito LLM quando sobreposto
  "fonte_veredito": str,                # "deterministico_headroom_renda (IBGE Censo 2022)"
  "headroom_renda": dict,               # output de tools/posicionamento_renda.avaliar_posicionamento
  "justificativa_veredito": str,
  "janela_de_entrada": dict,
  "markdown": str,
  "fonte_geracao": "langcache" | ausente,
}
```

**Persistência downstream:**
- `metrics/relatorios/<relatorio_local_id>.json` — patched via `_patch_relatorio_json()` (linha 65): `output_consolidado.posicionamento_estrategico = parsed`
- Supabase `relatorios` — via `db/supabase_writer.write_posicionamento_failsafe()` (linha 527)
- Schema validado leniente via `models/pipeline_schemas.A9Output` + `validar_lenient()` (linha 494)

---

## 3. Regras de Negócio

**RN-A9-001 — Veredito determinístico sobrepõe LLM**
`_a9_override_veredito_deterministico()` (linha 147): calcula headroom de renda via `tools/posicionamento_renda.avaliar_posicionamento(cidade, uf, bairro, concorrentes)`. Se `hr["status"] == "ok"` e `hr["veredito_posicionamento"] != "INDETERMINADO"`, o veredito do LLM é salvo em `veredito_posicionamento_llm` e substituído pelo determinístico em `veredito_posicionamento`. O LLM mantém ERRC/markdown/gaps — só o rótulo e `headroom_renda` viram sourced/auditáveis. Padrão idêntico ao A4 (tool computa, LLM narra).

**RN-A9-002 — Gaps reais sobrepõem gaps LLM**
`_a9_override_veredito_deterministico()` chama `_gaps_reais()` (linha 297): contagem de penetração por serviço do catálogo `_SERVICOS_CATALOGO` (16 entradas) via `_servicos_do_concorrente()`. Serviços com `penetração == 0` são os gaps reais. O LLM recebia "Nutrição/Recovery/Silver" por reflexo; o override substitui pelo dado real da praça.

**RN-A9-003 — Catálogo de 16 serviços é fechado**
`_SERVICOS_CATALOGO` (linha 267): mapeamento fixo de chaves de modalidade para rótulos do catálogo. GAP = serviço com penetração < 3 em todos os concorrentes (prompt, linha 614). A instrução proíbe explicitamente inventar serviço fora da lista real injetada.

**RN-A9-004 — LangCache com threshold 0.97**
`_a9_before_model_callback()` (linha 385): busca no LangCache com `similarity_threshold=0.97` (configurável via `LANGCACHE_A9_SIMILARITY`). Threshold elevado (vs 0.88 padrão) para evitar false positive entre bairros com chave parecida (incidente Fortaleza documentado no comentário da linha 403). Chave inclui `relatorio_id`, `cidade`, `bairro`, `tipo_negocio`, `hash_top5_concorrentes` (linha 195–237).

**RN-A9-005 — Cache hit preserva after_model_callback**
`_a9_after_model_callback()` (linha 440): verifica `meta.get("langcache_hit")` antes de chamar `langcache_set` — evita re-persistir hit como novo entry. `fonte_geracao = "langcache"` é marcado no output final.

**RN-A9-006 — Output deve ser JSON puro, sem texto fora do bloco**
Instrução linha 628: `retorne APENAS JSON válido (sem texto fora do JSON)`. `_parse_json_from_text()` (linha 50) suporta fence ```json``` mas o ideal é JSON puro. JSON array (não objeto) na raiz levanta `JSONDecodeError`.

**RN-A9-007 — Coerência financeira obrigatória**
Instrução linhas 679–686: aluguel SEMPRE no formato `R$ X/m² para Y–Z m² (≈ R$ W/mês)`. Proibido recalcular — usar exclusivamente `analise_financeira` (A4). Números financeiros no markdown devem bater com o JSON do A4. Entidades com nome completo na primeira menção.

**RN-A9-008 — `janela_de_entrada` só com dado real**
Instrução linha 669: se não houver bloco `DEMANDA FUTURA DATADA` no contexto → `janela_de_entrada: {"tem_demanda_futura": false}`. Proibido inventar obras.

**RN-A9-009 — `after_agent_callback` valida schema leniente**
`_a9_after_agent_callback()` (linha 479) importa `A9Output` de `models/pipeline_schemas` e chama `validar_lenient()` — loga divergência de contrato mas nunca rejeita o dado (C6.2 observável, tolerante).

**RN-A9-010 — Falha no parse JSON é degradação silenciosa**
`_a9_after_agent_callback()` (linha 544): `JSONDecodeError` → grava `{"erro": "...", "raw_output": ...[:2000]}` no state; `Exception` genérica → `{"erro": "..."}`. O pipeline continua; posicionamento fica indisponível mas viabilidade não é afetada.

---

## 4. Critérios de Aceite Mensuráveis

| Critério | Limiar |
|----------|--------|
| **CA-A9-01** — `veredito_posicionamento` final quando `headroom_renda.status == "ok"` deve ter `fonte_veredito == "deterministico_headroom_renda (IBGE Censo 2022)"` | 100% |
| **CA-A9-02** — `gaps_identificados` quando `_gaps_reais()` retorna lista não-vazia deve ter `fonte_gaps == "deterministico_oferta_concorrentes (planos+IG)"` | 100% |
| **CA-A9-03** — LangCache HIT não gera nova entrada no cache (idempotência) | 100% |
| **CA-A9-04** — LangCache threshold mínimo para keys `positioning_a9:*` | >= 0.97 (configurável, default) |
| **CA-A9-05** — `janela_de_entrada.tem_demanda_futura == false` quando `demanda_futura` ausente no state | 100% |
| **CA-A9-06** — JSON malformado do LLM não interrompe o pipeline A6→A9 | A9 em degradação, pipeline completa |
| **CA-A9-07** — `_patch_relatorio_json()` atualiza `output_consolidado.posicionamento_estrategico` sem sobrescrever o resto | 100% (read-modify-write com `setdefault`) |
| **CA-A9-08** — Cobertura de testes unitários de `_a9_override_veredito_deterministico`, `_gaps_reais`, `_a9_cache_prompt` | >= 80% (C4.1) |

---

## 5. Comportamento em Degradação (C4.4)

| Falha | Comportamento |
|-------|---------------|
| `tools/posicionamento_renda` indisponível ou `status != "ok"` | `_a9_override_veredito_deterministico()` captura `Exception`, loga WARNING, mantém veredito do LLM |
| `_gaps_reais()` retorna `None` (sem concorrentes no state) | `gaps_identificados` do LLM é preservado sem override |
| LangCache indisponível (serviço down) | `before_model_callback` captura `Exception`, retorna `None`, LLM é chamado normalmente |
| `json.JSONDecodeError` no output do LLM | `after_agent_callback` grava `{"erro": ..., "raw_output": ...}` no state; Supabase persist não é chamado |
| `supabase_writer.write_posicionamento_failsafe()` falha | Loga WARNING; JSON local já foi patched e é fonte de verdade |
| `_patch_relatorio_json()` — arquivo não encontrado | Loga WARNING; state `relatorio_posicionamento` já gravado |
| Modelo gemini-2.5-pro retorna 429/503/500 | `build_llm_agent` wraps no `Gemini(retry_options=HttpRetryOptions(attempts=4, ...))` — retenta a chamada, não o pipeline |

---

## 6. Contexto para IA

**Gotcha #1 — `output_key` grava string, não dict.**
`relatorio_posicionamento_md` no state é a string JSON bruta emitida pelo LLM (inclui possível fence ` ```json ` ). `_parse_json_from_text()` (linha 50) faz o parse. `_parse_market_context()` é o parser tolerante para outras keys. Se `state.get("relatorio_posicionamento_md")` já for dict (re-run), `after_agent_callback` detecta e usa direto (linha 487).

**Gotcha #2 — `after_model_callback` chain duplo (C7.2).**
O A9 define `_a9_after_model_callback` para LangCache. `build_llm_agent` encadeia `_telemetry_after_model` após (via `_injetar_telemetria`, linha 49–65 de `agent_factory.py`). O `_attach_telemetry` do orchestrator também encadeia. A deduplicação é por identidade de função — callbacks distintos são encadeados, não substituídos. Antes desta correção, A9 ficava cego para telemetria de tokens (C7.2 gap).

**Gotcha #3 — LangCache false positive entre bairros.**
Threshold 0.88 causava o mesmo JSON de posicionamento para Parangaba e Meireles (Fortaleza) porque os primeiros 1024 chars das chaves eram iguais. Fix: threshold 0.97 + inclusão do `relatorio_id` e `hash_top5_concorrentes` na chave (linha 195–237).

**Gotcha #4 — `_resolve_location_from_state` fallback em cascata.**
`cidade`/`bairro` podem estar em `state["input_params"]`, `state["cidade"]`, ou dentro de `market_context` (extraído via `_parse_market_context`). A função `_resolve_location_from_state()` (linha 108) tenta as três fontes. Se nenhuma retorna, `_a9_override_veredito_deterministico()` retorna sem ação (sem erro).

**Gotcha #5 — `oferta_concorrentes` vem do A3b (ex-A3c fundido).**
O agente A3c foi removido; o A3b determinístico passou a mapear a oferta (site via httpx + Instagram via SearchAPI, sem Playwright) e gravar `oferta_concorrentes`. `_resumo_oferta_e_gaps()` lê `planos_precos.inclui` + as modalidades já mescladas em `inteligencia_competitiva.concorrentes_detalhados[*].servicos_oferecidos` (A3b). Mesmo se a oferta vier vazia, a função degrada sem erro.

**Gap C6.4 conhecido:** `InMemorySessionService` — estado A9 (posicionamento parsed) vive em memória durante a sessão ADK. Crash entre A9 completar e `_patch_relatorio_json` completar pode perder o posicionamento do JSON local. Supabase via `write_posicionamento_failsafe` é o fallback de recuperação.
