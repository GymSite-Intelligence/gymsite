# A9 — Contrato de Dados do Relatório PDF (passo zero)

> **Pré-requisito de `A9_CHARTS_TABLES_SPEC.md` e `A9_CONFIDENCE_BADGES_SPEC.md`.**
> Mapeia cada visual/selo ao campo REAL emitido pelos agentes (output_consolidado →
> `pdf/adapters.py` → `pdf/models.py`). Sem isto, risco de construir gráfico sem dado.
> Verificado contra o código em 2026-06-16 (não presumido).

## Legenda de status
- ✅ **READY** — dado existe no `output_consolidado` E exposto em `pdf/models.py` (ou trivial de expor). Construir já.
- 🔧 **ADAPTER** — agente EMITE o dado, mas `pdf/adapters.py`/`models.py` descartam. Estender adapter+model (barato, sem tocar pipeline).
- ⛔ **MISSING** — nenhum agente emite. Exige nova computação no pipeline (caro) — adiar ou cortar do MVP.

## Charts (de `A9_CHARTS_TABLES_SPEC.md`)

| # | Visual | Campo necessário | Onde está (real) | Status |
|---|--------|------------------|------------------|--------|
| 1 | Gauge score geral | `score_bairro` | `RelatorioPdfModel.score_bairro` | ✅ READY |
| 2 | KPIs table | pop raio, nº conc., ticket, payback | `total_raio`, `total_concorrentes`, `market.ticket_mercado`, `cenarios[].payback_meses` | ✅ READY |
| 3 | Colunas receita/resultado 3 cenários | receita/lucro por cenário | `cenarios[].receita_mensal/lucro_mensal` | ✅ READY |
| 4 | Tabela comparativo concorrentes (básico) | nome, rating, avaliações, bairro, 24h | `CompetidorPdf` (todos) | ✅ READY |
| 5 | DRE comparativa | custos detalhados 3 cenários | A4 emite `analise_financeira.cenarios[].custos_detalhados` (12 linhas) — **adapter dropa** | 🔧 ADAPTER |
| 6 | Sensibilidade tornado | 3 stress tests por cenário | A4 emite `cenarios[].sensibilidade` — **CenarioPdf não carrega** | 🔧 ADAPTER |
| 7 | Scatter distância (sem preço) | distância por concorrente | A3 emite `concorrentes[].distancia_km` — **CompetidorPdf não carrega** | 🔧 ADAPTER |
| 8 | Radar perfil praça | 3 de 6 eixos | `scores[]` tem demográfico/competitivo/viabilidade (3); faltam custo-ocupação, acessibilidade, potencial-digital | 🔧 ADAPTER (3) / ⛔ (3) |
| 9 | Heatmap regional + pin | lat/lng da praça | asset estático OK; latlng do candidato top-1 existe no state mas **não em `CandidatoPdf`** | 🔧 ADAPTER |
| 10 | Donut composição demográfica | pirâmide etária | A2/`ibge_tools` dá só **faixa-alvo única** (1 %), não pirâmide | ⛔ MISSING |
| 11 | Barras população por raio (1/3/5 km) | pop por faixa de raio | só agregado `total_raio` (único); censo_setor agrega por raio internamente mas **não expõe os 3** | ⛔ MISSING |
| 12 | Tabela raio×pop×domic×renda | métricas por raio | idem #11 | ⛔ MISSING |
| 13 | Scatter PREÇO×distância | preço por concorrente | só via A3c `oferta.planos[].preco_mensal` — **A3c DESABILITADO** (Playwright Windows, GymSite #127) | ⛔ MISSING (bloqueado) |
| 14 | Fluxo de caixa acumulado + break-even | série mensal de caixa | A4 dá só `payback_meses` escalar; **sem série mensal** | ⛔ MISSING |
| 15 | Matriz 2×2 atratividade×esforço | classificação praça | nenhum agente computa | ⛔ MISSING |
| 16 | Roadmap timeline | fases | nenhum agente computa | ⛔ MISSING |

## Selos de confiança (de `A9_CONFIDENCE_BADGES_SPEC.md`)

O selo exige um **nível de confiança por métrica** (medido / estimativa / projeção). Hoje:

| Fonte de confiança | Existe? | Cobre |
|--------------------|---------|-------|
| `aluguel_pesquisa_detalhes.tier` + `fonte_aluguel` | ✅ | aluguel (medido vs benchmark) |
| `param_meta.categoria` (benchmark/calibracao/aberto) via `metodologia_explain` | ✅ | toda métrica derivada de `param()` |
| Contagens diretas (nº concorrentes, pop) | ✅ (implícito = "medido") | KPIs de contagem |
| Scores compostos (score_bairro etc.) | ⚠️ sem campo explícito | precisa **regra de derivação** (ex.: score com dimensão faltante → "projeção") |

→ **Não há campo único de confiança.** Construível via mapa determinístico:
`categoria param → nível selo` (benchmark→ESTIMATIVA, calibracao→ESTIMATIVA, aberto→PROJEÇÃO; contagem direta→MEDIDO; tier 1 aluguel→MEDIDO). Esse mapa **não existe ainda** — é o primeiro item a criar antes dos selos.

## Veredito do contrato (ordem de construção derivada)

**Fase A — construir já (✅ READY, dado existe e exposto):**
Gauge veredito · KPIs table · Colunas 3 cenários · Tabela concorrentes básica.

**Fase B — adapter barato (🔧, agente emite, só estender `models.py`+`adapters.py`):**
DRE (carregar `custos_detalhados`) · Tornado (carregar `sensibilidade`) · Scatter distância (carregar `distancia_km`) · Radar 3 eixos · pin no heatmap (latlng candidato). **Não toca o pipeline.**

**Fase C — exige novo dado no pipeline (⛔, adiar/cortar):**
Pop por raio 1/3/5km · série de fluxo de caixa mensal · pirâmide etária · matriz 2×2 · roadmap · radar eixos 4-6. Scatter-preço **bloqueado** até A3c voltar (fix Playwright Windows).

**Selos:** criar primeiro o **mapa `categoria→nível`** (determinístico, usa `param_meta`/`tier`); depois aplicar os badges nas métricas das Fases A/B.

---

*Verificado contra `pdf/models.py`, `pdf/adapters.py`, `tools/financial_tools.py`,
`tools/competitor_tools.py`, `tools/ibge_tools.py`. Atualizar quando um agente passar a
emitir um campo hoje ⛔.*
