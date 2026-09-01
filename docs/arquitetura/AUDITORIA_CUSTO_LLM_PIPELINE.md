# Auditoria de Custo LLM — Pipeline A0-A9 (12/06/2026)

> Contexto: billing 1-10/jun = R$ 357,14, sendo Vertex AI R$ 193,86 (SKU
> dominante: Gemini 3.6 Flash Text Input). Run rate ~R$ 1.070/mês. Meta:
> ~R$ 400/mês sem perder qualidade. Mudanças AQUI especificadas; aplicação
> pós-reunião (pipeline é rota da demo).

## Mapa real (verificado em agents/*.py)

| Agente | Modelo hoje | Veredito |
|---|---|---|
| a0_context_builder | flash | ✅ certo |
| a1_geoscout | flash | ✅ certo |
| a2_demo_analyst | flash | ✅ certo |
| a3 / a3a / a3c | flash | ✅ certo |
| a3b_competitor_analysis | flash-lite | ✅ certo (batch mecânico) |
| a5_contact_hunter | flash | ✅ certo |
| a7_market_research | flash | ✅ certo |
| **a4_financial_estimator** | **pro** | 🔻 **downgrade pra flash** (ver abaixo) |
| **a6_report_consolidator** | **pro** | ✅ manter — síntese final é a cara do produto |
| **a9_positioning_strategist** | **pro** | ✅ manter Pro, mas **ligar LangCache A9** |

`tools/cost_optimizations.py` já sugere este mapa (a4 lá ainda como pro
"raciocínio complexo" — recomendação abaixo diverge e explica por quê).

## Recomendação 1 — a4: Pro → Flash (maior corte)

O "raciocínio complexo" do a4 é na prática aritmética estruturada: 3
cenários com fórmulas de CAPEX/OPEX/payback sobre inputs já coletados. O
front RECALCULA cenários em JS (FinanceiroKpiStrip + cenariosRecalc) — ou
seja, a matemática nem é responsabilidade exclusiva do LLM. Flash com
prompt atual + temperatura baixa resolve.

Gate de aplicação (1 golden case): rodar o MESMO input (Cocó) com Pro e
Flash, comparar `viabilidade_3_cenarios` campo a campo — divergência só
de arredondamento = aprovado. Output Pro custa ~4× o Flash por token; a4
é um dos maiores consumidores de output do pipeline.

## Recomendação 2 — a9: ligar LangCache em produção

`.env`: `LANGCACHE_A9_ENABLED=0` (desligado em dev pra não servir JSON
velho). A9 é chamada Pro de 30-90s; bairros repetidos (re-análises,
demos) pagam Pro de novo à toa. Em produção: `LANGCACHE_A9_ENABLED=1`
com `LANGCACHE_A9_SIMILARITY=0.97` (já configurado). Pré-requisito:
reprocessar bairros após a próxima mexida de prompt do A9, senão o cache
serve a versão antiga do texto.

## Recomendação 3 — thinking budget nos agentes Pro

BUG-009 provou: thought tokens consomem `max_output_tokens` e são
cobrados como output (Pro: R$ 10/M vs input R$ 1,25/M — no nosso pricing
local). a6/a9 rodam com thinking dinâmico ilimitado. Ação: medir
`thoughts_token_count` num run e, se >20% do output, fixar
`thinking_budget` moderado (ex.: 4096) — qualidade de síntese não precisa
de teto livre.

## Recomendação 4 — Places API (R$ 145,56/10d, 2º maior custo)

Não é LLM mas está no mesmo bolso. FieldMask das chamadas Place Details
inclui contact data (telefone/website/horários) em TODA chamada — campos
de tier mais caro. Ação: auditar `tools/maps_tools.py` — pedir contact
data SÓ na primeira coleta do place (cache local já existe por place_id);
re-consultas usam máscara básica.

## Impacto estimado

| Ação | Economia/mês (estim.) |
|---|---|
| a4 Pro→Flash | ~R$ 150–250 |
| LangCache A9 em prod | ~R$ 50–150 (depende da taxa de repetição) |
| Thinking budget a6/a9 | ~R$ 30–80 |
| FieldMask Places | ~R$ 100–200 |
| **Total** | **R$ 1.070 → ~R$ 400-500/mês** |

## Ordem de aplicação (pós-reunião)

1. a4 Pro→Flash com golden case (30 min, maior retorno)
2. FieldMask Places (1h, segundo maior)
3. Thinking budget: medir primeiro, fixar se justificar
4. LangCache A9: só junto do deploy de produção
