"""
GymSite Intelligence — Root Orchestrator
Coordena os 5 agentes especializados para encontrar o ponto perfeito para academias.
"""
import sys
import os

# Garante que os módulos do projeto raiz sejam encontrados
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google.adk.agents import Agent, SequentialAgent, ParallelAgent

from agents.a0_context_builder import context_builder_agent
from agents.a1_geoscout import geoscout_agent
from agents.a2_demo_analyst import demo_analyst_agent
# A3 monolítico DEPRECATED — substituído por A3a + A3b (resolve AFC=10 + MALFORMED)
# from agents.a3_competitor_intel import competitor_intel_agent
from agents.a3a_competitor_search import competitor_search_agent
from agents.a3b_competitor_analysis import competitor_analysis_agent
# A3c enriquece concorrentes com oferta real (site + IG). Modo SHADOW —
# grava `oferta_concorrentes` no state mas A6 ainda não consome (GymSite #127).
from agents.a3c_competitor_mapper import competitor_mapper_agent
from agents.a4_financial_estimator import financial_estimator_agent
from agents.a5_contact_hunter import contact_hunter_agent
from agents.a6_report_consolidator import report_consolidator_agent
from agents.a9_positioning_strategist import positioning_strategist_agent
# a7_market_research é importado dentro de a3a/a4 como função (não AgentTool)

# Telemetria de tokens — registra consumo por agente em metrics/tokens_pipeline.csv
# Usa after_model_callback (recebe llm_response com usage_metadata).
# before_agent_callback inicializa run_id da sessão.
from tools.token_telemetry import (
    before_agent_callback as _telemetry_before,
    after_model_callback as _telemetry_after_model,
)
# Diagnóstico de state (debug #124): registra keys do state após cada agente.
from tools.state_diagnostics import after_agent_state_dump as _state_dump
# OpenTelemetry spans por agente (A0–A6)
from tools.agent_telemetry import before_agent_callback as _otel_before, after_agent_callback as _otel_after


def _chain_callbacks(existing, new):
    """Encadeia dois callbacks: chama existing primeiro, depois new."""
    if existing is None:
        return new
    if existing is new:
        return existing
    def _chained(ctx):
        existing(ctx)
        new(ctx)
    return _chained


def _attach_telemetry(*agents):
    """Anexa callbacks: before_agent (run_id + otel) + after_model (tokens) + after_agent (otel + state dump)."""
    for ag in agents:
        try:
            ag.before_agent_callback = _chain_callbacks(
                getattr(ag, "before_agent_callback", None), _otel_before
            )
            if getattr(ag, "after_model_callback", None) is None:
                ag.after_model_callback = _telemetry_after_model
            ag.after_agent_callback = _chain_callbacks(
                getattr(ag, "after_agent_callback", None), _otel_after
            )
            # State dump vai depois do otel_after para manter ordem
            ag.after_agent_callback = _chain_callbacks(
                ag.after_agent_callback, _state_dump
            )
        except Exception:
            pass  # falha silenciosa — telemetria não bloqueia


_attach_telemetry(
    context_builder_agent, geoscout_agent, demo_analyst_agent,
    competitor_search_agent, competitor_analysis_agent, competitor_mapper_agent,
    financial_estimator_agent,
    contact_hunter_agent, report_consolidator_agent,
    positioning_strategist_agent,
)

# ── Sub-pipeline competitivo: A3a (busca) → A3b (análise) → A3c (oferta real) ──
# Quebra do A3 monolítico que estourava AFC=10 e gerava MALFORMED_FUNCTION_CALL.
# A3c (shadow) visita site+IG dos top 10 pra A6 saber o que cada concorrente
# JÁ oferece antes de recomendar diferenciais.
competitor_subpipeline = SequentialAgent(
    name="CompetitorPipeline",
    description="A3a busca → A3b análise reviews → A3c oferta real (modo shadow).",
    sub_agents=[
        competitor_search_agent,      # A3a
        competitor_analysis_agent,    # A3b
        competitor_mapper_agent,      # A3c (shadow — GymSite #127)
    ],
)
_attach_telemetry(competitor_subpipeline)

# ── Fase 2: análise paralela (demografia + competitivo + financeiro ao mesmo tempo) ──
parallel_analysis = ParallelAgent(
    name="ParallelAnalysis",
    description="Executa análise demográfica, competitiva (A3a→A3b) e financeira em paralelo.",
    sub_agents=[
        demo_analyst_agent,
        competitor_subpipeline,       # A3a→A3b sequencial dentro do paralelo
        financial_estimator_agent,
    ],
)

# ── Pipeline completo: ContextBuilder → GeoScout → Análise Paralela → ContactHunter → Relatório ──
pipeline = SequentialAgent(
    name="GymSitePipeline",
    description=(
        "Pipeline sequencial: contexto de mercado (Deep Research) → "
        "localização → análise paralela → contato → relatório final → "
        "posicionamento estratégico (ERRC)."
    ),
    sub_agents=[
        context_builder_agent,        # A0 — Deep Research (NOVO em v0.4)
        geoscout_agent,                # A1
        parallel_analysis,             # A2 + A3 + A4
        contact_hunter_agent,          # A5
        report_consolidator_agent,     # A6
        positioning_strategist_agent,  # A9 — Posicionamento ERRC
    ],
)

# ── Root Agent: ponto de entrada do ADK ──
root_agent = Agent(
    name="GymSiteIntelligence",
    model="gemini-2.5-flash",
    description=(
        "Agente raiz do GymSite Intelligence. Orquestra a busca completa de pontos "
        "comerciais ideais para academias de ginástica no Brasil."
    ),
    instruction="""
Você é o GymSite Intelligence — sistema de IA para encontrar o ponto comercial perfeito
para academias de ginástica no Brasil.

## COMO USAR
O usuário deve informar:
- **Cidade e estado** onde buscar (obrigatório)
- Bairros preferenciais (opcional)
- Área mínima/máxima em m² (padrão deriva do `tamanho_preset` + `tipo_negocio`)
- Faixa etária alvo (padrão: 25-40)
- **Gênero alvo** (opcional, default "misto") — valores possíveis:
  * `misto` — público 50/50 (default)
  * `predominantemente_feminino` — Pilates, dança, funcional feminino; ticket Mid/Premium
  * `predominantemente_masculino` — musculação pesada, lutas, CrossFit; ticket Low/Mid
  * `exclusivamente_feminino` — academia só-mulheres (Curves, ContornoFit); nicho premium
  * `exclusivamente_masculino` — raríssimo no mercado BR; geralmente CT de lutas
- **Tipo de negócio** (opcional, default "academia") — valores possíveis:
  academia | crossfit_box | studio_pilates | studio_funcional | outro
- **Tamanho preset** (opcional, default "m" — mais comum) — Smart Fit-style:
  * `pp` — micro (Smart Fit Express, Box garagem, Pilates solo)
  * `p` — pequeno (Selfit P, Box pequeno)
  * `m` — ★ médio padrão de mercado (Smart Fit Standard, F45)
  * `g` — grande (Bodytech, Cia Athletica padrão)
  * `gg` — mega centro (Cia Athletica flagship)
- Exigências específicas (térreo, estacionamento, etc.)

## SEU PAPEL
Você recebe a solicitação do usuário, extrai os parâmetros (cidade, estado,
bairro, área, faixa etária) e delega ao pipeline de 6 agentes especializados.

## MODO CROWDSOURCE (detecção automática)
Se o usuário mencionar "indicações da comunidade", "formulário", "campanha",
"pesquisa", "votação" ou listar bairros sugeridos por terceiros, ative o
**Modo Crowdsource**: extraia esses bairros e inclua na delegação ao pipeline
como `bairros_indicados=[...]`. O ReportConsolidator (A6) renderá uma seção
especial "📣 Demanda Social Detectada" no relatório final.

## AGENTES NO PIPELINE (v0.5)

1. **ContextBuilder (A0)** — Deep Research de mercado — primeiro do pipe
2. **GeoScout (A1)** — Localiza zonas comerciais via Google Maps
3. **DemoAnalyst (A2)** — Analisa potencial demográfico via IBGE (paralelo)
4. **CompetitorIntel (A3)** — Mapeia concorrência + reviews + horários pico (paralelo)
5. **FinancialEstimator (A4)** — Estima viabilidade financeira em 3 cenários (paralelo)
6. **ContactHunter (A5)** — Identifica decisores e gera scripts de abordagem
7. **ReportConsolidator (A6)** — Sintetiza tudo num relatório executivo
8. **PositioningStrategist (A9)** — Análise de posicionamento via Framework ERRC

## ROTEAMENTO

Para QUALQUER pedido de análise (academia em X bairro, avaliação de imóvel,
prospecção, "quanto custa", "horários de pico", "o que falam dessa academia") →
**transfer_to_agent("GymSitePipeline")**.

O pipeline é completo: GeoScout (A1) → Análise Paralela (A2/A3/A4) → ContactHunter (A5) → ReportConsolidator (A6) → PositioningStrategist (A9).

Internamente, o **A3 CompetitorIntel já usa Gemini Search Grounding (A7)** como
fallback automático quando o Playwright scraper falha. Você não precisa
rotear pra A7 — o A3 cuida disso sozinho.

## RESPOSTA AO USUÁRIO
Sua função é apenas **delegar ao pipeline** — não tente reescrever ou resumir
o output dos sub-agentes. Seja conciso na sua mensagem inicial: confirme os
parâmetros recebidos e faça o transfer_to_agent("GymSitePipeline").
""",
    sub_agents=[pipeline],
)
