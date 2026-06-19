# Determinização das fases LLM + Narrador Claude headless (subscription)

> Seção de mudanças — junho/2026. Elimina variância e a exposição ao **dunning do Vertex**
> nas fases que só narram, e determiniza o A9 por completo.

## Contexto / dor

- **Dunning Vertex**: `403 Lightning dunning decision is deny for project 258980081869` —
  billing/pagamento travado bloqueia o Gemini (Vertex). O pipeline quebrava nas fases LLM.
- **Auditoria Cocó**: relatórios divergiam run-a-run (aluguel 17k→88k, saturação BAIXO→ALTO).
  Raiz: dado não-determinístico + LLM produzindo dado em vez de só narrar.
- **Regra VEC**: *o LLM raciocina sobre o dado, não PRODUZ dado.*

## O que mudou

### 1. Narrador via Claude Code headless — `tools/narrador_claude.py`

Provider de **narração** (não de dado) para fases que só redigem texto sobre fatos já
determinísticos. Roda `claude -p --output-format json` na **subscription do Claude Code**
(sem `ANTHROPIC_API_KEY`) → **escapa o dunning E o custo por-token**.

- `narrar(fatos_texto, ancoras, fallback, instrucao)` → dict `{texto, fonte, motivo}`.
- **Guardrail anti-alucinação** (2 camadas):
  1. toda âncora textual (veredito/modelo/saturação) aparece literal;
  2. **zero número novo** — qualquer número fora das âncoras → reprova.
- Em qualquer falha (desligado / timeout / guardrail) → **fallback determinístico**. Nunca degrada.
- Flags: `NARRADOR_CLAUDE_ENABLED` (default OFF), `NARRADOR_USE_SUBSCRIPTION` (default ON),
  `NARRADOR_TIMEOUT_S`, `CLAUDE_BIN`.
- **Prod (Cloud Run) sem subscription → flag OFF → texto determinístico intacto.** Ligado só local.

### 2. Variância — provada

Mesmos fatos, 2 execuções de `claude -p`:

| Métrica | Resultado |
|---|---|
| Números (veredito/score/ticket/aluguel) | **IDÊNTICOS** (diff vazio) |
| Prosa | varia (48 vs 69 palavras) |
| Auth | `ANTHROPIC_API_KEY=` vazio → narração saiu (**subscription**) |

→ **variância de conclusão = 0; variância de prosa = irrelevante.**

### 3. Narração fiada — A6 e A9

- **A6** `_resumo_executivo_narrado`: embrulha `_resumo_executivo_deterministico`
  (fonte dos fatos **e** fallback). Veste fluente; números travados pelo guardrail.
- **A9** `_sintese_posicionamento_narrada`: sintetiza veredito + ticket + gaps reais +
  demanda futura (já determinísticos) e narra. Injetado pós-override do veredito.

### 4. A9 determinizado por completo — `LlmAgent → BaseAgent`

**Insight central:** a matéria-prima do A9 ERRC **sempre foi determinística** — o LLM
recebia tudo pronto e só narrava:

| Dimensão ERRC | Matéria-prima determinística |
|---|---|
| CRIAR | `_gaps_reais` (serviço com penetração 0 na praça) |
| mapa_servicos | penetração dos 16 serviços × oferta real dos concorrentes |
| ELIMINAR / REDUZIR | saturação (A3b) + tier |
| AUMENTAR | headroom de renda (IBGE Censo 2022) |
| veredito + ticket | `avaliar_posicionamento` (headroom = renda_pc × pct − ticket_mercado) |

→ **`_errc_deterministica(state)`** monta a ERRC por template ancorado no dado e retorna
o **dict no contrato do A9** (markdown + veredito + ticket[banda+comparativo] + gaps +
mapa_servicos + framework_errc + headroom).

`PositioningStrategistAgent(BaseAgent)` roda `_errc_deterministica` (sem LLM); o
`_a9_after_agent_callback` segue (override idempotente + síntese narrada + persistência).
Campos `ticket_minimo/maximo` + `comparativo_mercado` enriquecidos de dado real →
**zero regressão** no frontend (`PosicionamentoCard.tsx`) e no `pdf/builder.py`.

**Ganho:** A9 roda 100% determinístico — escapa o dunning, zero variância, zero custo Gemini Pro (~R$100/mês).

## Mapa de determinização (estado atual)

| Fase | Antes | Agora |
|---|---|---|
| A1 GeoScout | LlmAgent (passthrough) | **BaseAgent** |
| A4 Financial | LlmAgent (passthrough) | **BaseAgent** |
| A6 resumo executivo | LLM narrava | **determinístico + narrador opcional** |
| A9 Positioning ERRC | LlmAgent Gemini Pro | **BaseAgent determinístico + síntese narrada** |
| A0 ContextBuilder | Gemini | Gemini (orquestra tools/produz dado — determinização BaseAgent é outro job) |
| A3b Inteligência | Gemini | Gemini (pendente) |
| A6 corpo markdown | Gemini | Gemini (pendente) |

## Limites honestos

- Narrador só substitui texto que **já tinha versão determinística**. A0 (assembly de tools)
  e A3b não encaixam — precisam de determinização BaseAgent própria.
- Subscription auth é **local** (Cloud Run não tem) — narrador é ferramenta de runtime local;
  prod fica no fallback determinístico.
- **Caveat concorrência:** 2 `claude -p` simultâneos no mesmo `CLAUDE_CONFIG_DIR` corrompem
  `.claude.json`. O ADK roda fases em sequência → sem race. Paralelizar exige config isolado.
- Dead code: `_a9_before/after_model_callback` + helpers de injeção/LangCache ficaram sem uso
  (sem LLM no A9) — limpeza pendente, baixo risco.

## Próximo passo — Claude Agent SDK

`claude -p` é o headless one-shot; o **Claude Agent SDK** (`claude_agent_sdk`, função `query()`)
é o **mesmo motor programático**, com loop/subagentes/memory/MCP, usando a **mesma subscription
auth** (sem api_key). Tool-scoping controla variância: narração com `tools=[]` ≈ determinística;
curadoria/pesquisa com tools = exploratória. Avançar o narrador para o SDK quando instalado.
