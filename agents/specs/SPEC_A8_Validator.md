# SPEC_A8_Validator.md

| Campo | Valor |
|-------|-------|
| **ID** | spec-a8-001 |
| **Agente / Área** | A8 ValidadorCruzado — Validação pós-A6 |
| **Modelo LLM** | Determinístico (sem LLM no caminho crítico; kimi_search opcional/corroboração) |
| **Versão** | 1.0 |
| **Data** | 2026-06-18 |

---

## 1. Responsabilidade Única (C6.1)

O A8 executa **validação cruzada automática do relatório emitido pelo A6**, detectando inconsistências entre o markdown narrativo e o state estruturado do pipeline. Não gera conteúdo novo, não reescreve o relatório, não entra no grafo de agentes ADK. Produz um dict `validacoes` que é persistido no Supabase e anexado ao JSON local do relatório.

---

## 2. Contrato de Entrada / Saída

### Entradas (consumidas pelo `A8ValidadorCruzado.validar()`)

| Parâmetro | Tipo | Origem | Descrição |
|-----------|------|--------|-----------|
| `relatorio_markdown` | `str` | `state["relatorio_md"]` (A6) | Texto markdown completo do relatório |
| `state_json` | `dict` / `google.adk.sessions.State` | ADK session state | State completo do pipeline; normalizado por `_state_to_dict()` + `_normalize_state()` |
| `relatorio` | `dict \| None` | JSON local (`metrics/relatorios/<id>.json`) | Output consolidado do A6; fonte para `output_consolidado.*` |
| `custo_brl` | `float \| None` | Calculado pelo A6 | Custo total da pipeline (opcional, gravado na saída) |

**Chaves do state normalizadas por `_normalize_state()` (linha 63–88):**
- `score_bairro`, `score_concorrencia`, `score_demografico`, `score_viabilidade`
- `veredito`, `posicionamento_recomendado`, `resumo_executivo`
- `total_concorrentes_analisados`, `bairros_alternativos`, `top_3_candidatos`
- `cobertura_redes_a0`, `cenarios_financeiros`
- `inteligencia_competitiva` (para `_validar_evidencia_oportunidade`)

### Saída (dict retornado por `validar()`, linha 121–135)

```python
{
  "validacao_id": "val_YYYYMMDD_HHMMSS",
  "status_validacao": "APROVADO_LIMPO" | "APROVADO_MINOR_ISSUES" | "APROVADO_COM_RESSALVAS" | "REPROVADO_VALIDACAO",
  "score_validacao": float,          # 0.0–1.0 (penalidades descontadas via param())
  "alertas": [AlertaValidacao],       # lista de asdict(AlertaValidacao)
  "claims_verificadas": int,
  "claims_com_alertas": int,          # severidade CRITICO ou ALTA
  "fontes_independentes": [str],      # snippets do kimi_search (<=200 chars cada)
  "resumo_executivo_validacao": str,
  "revisar_manual": bool,             # True se qualquer alerta CRITICO
  "a0_research_provider": str,        # ex: "gemini"
  "custo_brl": float | None,
}
```

**Persistência downstream (via `tools/a8_runner.py`):**
- `validacoes` (tabela Supabase) — INSERT via `_persist_validacao_sync()` em daemon thread
- `relatorio["validacao_a8"]` — anexado ao JSON local pelo A6 (linha 3032 de `a6_report_consolidator.py`)

---

## 3. Regras de Negócio

**RN-A8-001 — Execução fora do grafo ADK**
O A8 não é um `Agent` ADK. É invocado como função Python pelo `after_agent_callback` do A6 via `tools/a8_runner.run_a8_validation()`. Não aparece no `GymSitePipeline` SequentialAgent.

**RN-A8-002 — Determinismo é primário; kimi é corroboração**
Todas as validações de coerência (financeira, demográfica, competitiva, veredito, narrativa) são implementadas como regras Python puras. O `kimi_search` (OpenClaw) é chamado **apenas** para as 2 claims de maior severidade (`_validar_fontes_externas`, linha 258–279) e só quando `A8_USE_KIMI=1` (default) e OpenClaw estiver configurado. Uma falha do kimi não bloqueia nem altera o score.

**RN-A8-003 — Normalização de State obrigatória**
O state do ADK mudou de `dict` para `google.adk.sessions.State` em ~2026-05-29. `_state_to_dict()` (linha 36–60) tenta: `to_dict()`, `_value`, `dict(state)`, nesta ordem. Sem ela, `dict(State)` cai no protocolo de sequência e `state[0]` gera `KeyError: 0`, esvaziando `validacoes` silenciosamente.

**RN-A8-004 — Inconsistência financeira (payback < 80% do break-even)**
`_validar_coerencia_financeira()` (linha 181): payback extraído do markdown via regex. Se `payback < breakeven * 0.8` → alerta ALTA.

**RN-A8-005 — Veredito APROVADO sem candidatos**
`_validar_dados_operacionais()` (linha 216): `APROVADO + top_3_candidatos == []` → alerta CRITICO. `APROVADO + total_concorrentes_analisados == 0` → alerta ALTA.

**RN-A8-006 — Score regional abaixo do limiar com APROVADO**
`_validar_veredito()` (linha 281): `score_bairro < param("validacao_score_minimo_aprovado")` (default 6.0) com veredito APROVADO → alerta CRITICO.

**RN-A8-007 — Saturação sem bairros alternativos**
`_validar_veredito()` (linha 301): `score_concorrencia < param("validacao_score_concorrencia_minimo")` (default 4.0) sem `bairros_alternativos` → alerta ALTA.

**RN-A8-008 — Narrativa otimista em relatório REPROVADO**
`_validar_narrativa_vs_financeiro()` (linha 322): REPROVADO + termos em `_TERMOS_OTIMISTAS` (ex: "oportunidade excepcional") sem marcadores condicionais (`_MARCADORES_CONDICIONAL`) → alerta ALTA. Caso motivador: run `rpt_1778371974` Meireles (payback 999 + "oportunidade excepcional").

**RN-A8-009 — Score de oportunidade máximo sem reviews informativos**
`_validar_evidencia_oportunidade()` (linha 345): `score_oportunidade_mercado >= 9` com menos de 3 reviews com `categoria_dor` não vazia ou `quote_pt_br` >= 40 chars → alerta ALTA. Previne falso positivo de mercado.

**RN-A8-010 — Cálculo do score de validação**
`_calcular_score_validacao()` (linha 390): `score = max(0.0, 1.0 - sum(pesos))`. Pesos via `param()`: CRITICO=0.40, ALTA=0.25, MEDIA=0.15, BAIXA=0.05. Valores recalibráveis em `parametros_metodologia` (linhas 228–231 do seed).

**RN-A8-011 — Status final**
`_status_final()` (linha 402): qualquer CRITICO → `REPROVADO_VALIDACAO`; qualquer ALTA sem CRITICO → `APROVADO_COM_RESSALVAS`; sem ALTA → `APROVADO_MINOR_ISSUES`; sem alertas → `APROVADO_LIMPO`.

**RN-A8-012 — `revisar_manual` obrigatório para CRITICO**
`revisar_manual: True` sempre que `any(a.severidade == "CRITICO")`. Sinaliza revisão humana (CONSTITUTION C6.3 HITL).

**RN-A8-013 — Timeout e persistência assíncrona**
`run_a8_validation()` (linha 101): detecta se há loop asyncio rodando; se sim, executa em `ThreadPoolExecutor` com timeout `A8_VALIDATION_TIMEOUT_SEC` (default 120s). `persist_validacao()` (linha 201) é sempre em daemon thread para não bloquear o A6.

---

## 4. Critérios de Aceite Mensuráveis

| Critério | Limiar |
|----------|--------|
| **CA-A8-01** — Relatório APROVADO com `top_3_candidatos == []` gera alerta CRITICO | 100% dos casos |
| **CA-A8-02** — `score_validacao` para relatório sem alertas | = 1.0 |
| **CA-A8-03** — `score_validacao` com 1 alerta CRITICO | <= 0.60 (1.0 - 0.40) |
| **CA-A8-04** — `status_validacao` correto por combinação de alertas | 100% conformidade com RN-A8-011 |
| **CA-A8-05** — Timeout respeitado quando loop asyncio rodando | resultado retornado ou `None` em <= 120s |
| **CA-A8-06** — `_state_to_dict()` retorna dict não-vazio para `google.adk.sessions.State` real | 100% |
| **CA-A8-07** — Narrativa otimista em REPROVADO sem condicional gera alerta ALTA | 100% dos termos em `_TERMOS_OTIMISTAS` |
| **CA-A8-08** — Cobertura de testes unitários das regras de negócio (RN-A8-004 a RN-A8-009) | >= 80% (C4.1) |

---

## 5. Comportamento em Degradação (C4.4)

| Falha | Comportamento |
|-------|---------------|
| `kimi_search` indisponível / `A8_USE_KIMI=0` | Validação prossegue sem corroboração externa; `fontes_independentes = []` |
| OpenClaw não configurado (`_openclaw_configured() == False`) | Idem acima; nenhum alerta gerado por ausência do kimi |
| `supabase-client` ausente ou `SUPABASE_URL`/`KEY` vazios | `persist_validacao()` loga WARNING e retorna sem persistir; JSON local continua como fonte de verdade |
| Erro em `run_a8_validation_async()` | Capturado; retorna `None`; A6 loga WARNING (linha 3045–3050 de `a6_report_consolidator.py`) sem interromper o pipeline |
| Timeout (`A8_VALIDATION_TIMEOUT_SEC`) excedido | `future.result(timeout=...)` lança exceção → capturada → retorna `None` |
| `A8_VALIDATOR_ENABLED=0` | `run_a8_validation_async()` retorna `None` imediatamente (linha 65–67 de `a8_runner.py`) |

---

## 6. Contexto para IA

**Gotcha #1 — A8 não é Agent ADK.**
Não adicione `a8_validator` ao `pipeline` SequentialAgent. Ele é chamado pelo `after_agent_callback` do A6 via `tools/a8_runner.run_a8_validation()` (linha 3024–3044 de `a6_report_consolidator.py`). Colocá-lo no grafo quebraria a sequência e duplicaria a validação.

**Gotcha #2 — `_state_to_dict()` é invariante crítico.**
A mudança de `dict` para `google.adk.sessions.State` no ADK (~2026-05-29) é silenciosa. Sem `_state_to_dict()`, `dict(State)` retorna `{0: ...}` (protocolo de sequência) e todos os `state.get("campo")` retornam `None`. O resultado é `validacoes` vazia sem erro visível.

**Gotcha #3 — `_parse_market_context` para `inteligencia_competitiva`.**
O `output_key` do ADK grava o echo do LLM como string no state. `state.get("inteligencia_competitiva")` pode ser `str` (JSON fence ou texto puro). `_parse_market_context()` (importado de `tools/competitor_tools`) tolera str/JSON/fence/dict — usar direto sem parse causava `isinstance(ic_raw, dict) == False` e abortava `_validar_evidencia_oportunidade` em 100% dos runs (regressão documentada na linha 347–351 de `a8_validator.py`).

**Gotcha #4 — Pesos e limiares são `param()`, não constantes.**
`validacao_score_minimo_aprovado` (6.0), `validacao_score_concorrencia_minimo` (4.0), `validacao_peso_critico` (0.40) etc. vivem em `parametros_metodologia` (linhas 226–231 do seed). Recalibrar no banco altera o comportamento sem deploy.

**Gotcha #5 — `_validar_narrativa_vs_financeiro` requer caso motivador.**
A validação foi introduzida especificamente para o run Meireles (`rpt_1778371974`) onde payback=999 coexistia com "oportunidade excepcional" no resumo. A lista `_TERMOS_OTIMISTAS` (linha 312) e `_MARCADORES_CONDICIONAL` (linha 320) são o critério exato — qualquer modificação exige atualizar esta SPEC.

**Gap C6.4 conhecido:** O resultado do A8 é gravado em `relatorio["validacao_a8"]` (dict em memória/JSON local) e no Supabase via daemon thread. Não há recuperação de estado em caso de crash do processo entre A6 e a persistência — inconsistência possível entre JSON local e Supabase se o processo morrer durante `persist_validacao`.
