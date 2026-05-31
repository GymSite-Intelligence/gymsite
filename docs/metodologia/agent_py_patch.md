# Patch de Integração do A9 PositioningStrategist no Pipeline

Este documento descreve as modificações necessárias no arquivo `gymsite_intelligence/agent.py` para integrar o novo agente A9 ao pipeline existente.

---

## 1. Import do novo agente

**Arquivo:** `gymsite_intelligence/agent.py`

Adicionar a importação do A9 após as imports existentes:

```python
from agents.a6_report_consolidator import report_consolidator_agent
# A9 — gera relatório de posicionamento estratégico (Framework ERRC)
from agents.a9_positioning_strategist import positioning_strategist_agent
```

---

## 2. Adicionar A9 ao telemetry hook

Na chamada `_attach_telemetry(...)`, adicionar `positioning_strategist_agent`:

```python
_attach_telemetry(
    context_builder_agent, geoscout_agent, demo_analyst_agent,
    competitor_search_agent, competitor_analysis_agent, competitor_mapper_agent,
    financial_estimator_agent,
    contact_hunter_agent, report_consolidator_agent,
    positioning_strategist_agent,  # ← NOVO
)
```

---

## 3. Modificar o pipeline sequencial

O pipeline atual termina em A6. O A9 deve ser adicionado como passo final:

```python
# ── Pipeline completo: A0 → A1 → Análise Paralela → A5 → A6 → A9 ──
pipeline = SequentialAgent(
    name="GymSitePipeline",
    description=(
        "Pipeline sequencial: contexto de mercado (Deep Research) → "
        "localização → análise paralela → contato → relatório final → "
        "posicionamento estratégico (ERRC)."
    ),
    sub_agents=[
        context_builder_agent,        # A0 — Deep Research
        geoscout_agent,                # A1
        parallel_analysis,             # A2 + A3 + A4
        contact_hunter_agent,          # A5
        report_consolidator_agent,     # A6
        positioning_strategist_agent,  # A9 — Posicionamento (NOVO)
    ],
)
```

---

## 4. Atualizar a instrução do Root Agent

Na instrução do `root_agent`, adicionar A9 à lista de agentes:

```
## AGENTES NO PIPELINE (v0.5)

1. **ContextBuilder (A0)** — Deep Research de mercado
2. **GeoScout (A1)** — Localiza zonas comerciais via Google Maps
3. **DemoAnalyst (A2)** — Analisa potencial demográfico via IBGE (paralelo)
4. **CompetitorIntel (A3)** — Mapeia concorrência + reviews + horários pico (paralelo)
5. **FinancialEstimator (A4)** — Estima viabilidade financeira em 3 cenários (paralelo)
6. **ContactHunter (A5)** — Identifica decisores e gera scripts de abordagem
7. **ReportConsolidator (A6)** — Sintetiza tudo num relatório executivo
8. **PositioningStrategist (A9)** — Gera análise de posicionamento via Framework ERRC
```

---

## 5. Estrutura de arquivos resultante

```
agents/
├── __init__.py
├── a0_context_builder.py       # Deep Research de mercado
├── a1_geoscout.py              # Localização
├── a2_demo_analyst.py          # Demografia IBGE
├── a3a_competitor_search.py    # Busca de concorrentes
├── a3b_competitor_analysis.py  # Análise de reviews
├── a3c_competitor_mapper.py    # Mapeamento de oferta (shadow)
├── a4_financial_estimator.py   # Viabilidade financeira
├── a5_contact_hunter.py        # Decisores e scripts
├── a6_report_consolidator.py   # Relatório executivo
├── a7_market_research.py       # Função de fallback
├── a8_validator.py             # Validação de dados
└── a9_positioning_strategist.py # ← NOVO: Posicionamento ERRC
```

---

## 6. State produzido pelo A9

Após a execução do pipeline, o state conterá a nova chave:

```python
state["relatorio_posicionamento"] = {
    "framework_errc": {
        "eliminar": ["...", "..."],
        "reduzir": ["...", "..."],
        "aumentar": ["...", "..."],
        "criar": ["...", "..."],
    },
    "mapa_servicos": [
        {"concorrente": "...", "servicos": {"musculacao": 9, ...}},
    ],
    "gaps_identificados": [
        {"gap": "...", "descricao": "...", "potencial_ticket": "...", "dificuldade_implementacao": "..."},
    ],
    "recomendacao_ticket": {
        "ticket_recomendado": 249,
        "ticket_minimo": 199,
        "ticket_maximo": 299,
        "justificativa": "...",
        "comparativo_mercado": {"smart_fit": 79, "selfit": 99, ...},
    },
    "veredito_posicionamento": "OCEANO_AZUL",  # ou "TRANSICAO" / "VERMELHO"
    "justificativa_veredito": "...",
    "markdown": "# Relatório Completo em Markdown...",
}

# Também disponível separadamente:
state["relatorio_posicionamento_md"] = "# Markdown do relatório..."
```

---

## 7. Fluxo completo do pipeline (v0.5)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────────────┐
│  A0 Context │────→│  A1 GeoScout│────→│         Parallel Analysis           │
│   Builder   │     │             │     │  ┌─────────┐ ┌────────────┐ ┌─────┐ │
│ (Deep Res.) │     │(Localização)│     │  │ A2 Demo │ │A3 Competitor│ │A4   │ │
└─────────────┘     └─────────────┘     │  │Analyst  │ │   Intel     │ │Fin. │ │
                                        │  └─────────┘ └────────────┘ └─────┘ │
                                        └─────────────────────────────────────┘
                                                           │
                                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              A5 ContactHunter                                │
│                         (Decisores + Scripts)                                │
└──────────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         A6 ReportConsolidator                                │
│                    (Relatório Executivo Markdown)                              │
└──────────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  A9 PositioningStrategist                                                    │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │Framework    │  │Mapa de       │  │GAPs         │  │Veredito + Ticket  │  │
│  │ERRC         │  │Serviços      │  │Identificados│  │Recomendado        │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```
