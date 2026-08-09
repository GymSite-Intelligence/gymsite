"""Contrato producer → consumer do pipeline A0–A9 (fonte única do loop reverso).

Ordem de análise (de trás pra frente):
  A9 → A6 → A4 → A3b → A3a → A2 → A1 → A0 → entrypoint

Cada nó declara:
  - writes: chaves de state que o agente produz (contrato)
  - reads:  chaves de state de que depende para rodar (entradas)
  - consumers: quem lê as writes (preenchido pelo grafo; ver `consumers_of`)

Atualizar AQUI + `PIPELINE_AGENTES.md` §4 quando mudar wiring.
"""
from __future__ import annotations

from typing import TypedDict


class AgentDep(TypedDict):
    file: str
    writes: tuple[str, ...]
    reads: tuple[str, ...]
    notes: str


# Ordem canônica do Sequential de viabilidade (frente).
PIPELINE_ORDER: tuple[str, ...] = (
    "A0",
    "A1",
    "A2",
    "A3a",
    "A3b",
    "A4",
    "A6",
    "A9",
)

# Ordem do loop reverso (trás → frente).
REVERSE_ORDER: tuple[str, ...] = tuple(reversed(PIPELINE_ORDER))

# Entrada do entrypoint (não é agente).
ENTRYPOINT_WRITES: tuple[str, ...] = (
    "input_params",
    "demanda_futura",  # api.py enrichment pré-pipeline (CNO → captura T+24)
)

# Terminal: escrita sem consumidor de agente (persistência / PDF / UI).
TERMINAL_WRITES: frozenset[str] = frozenset(
    {
        "relatorio_posicionamento",
        "relatorio_posicionamento_md",
    }
)

AGENT_DEPS: dict[str, AgentDep] = {
    "A0": {
        "file": "agents/a0_context_builder.py",
        "writes": ("market_context",),
        "reads": ("input_params",),
        "notes": (
            "LLM + override CNPJ determinístico. Bundle-only tools. "
            "Número CNPJ sempre da tool, não da boca do LLM."
        ),
    },
    "A1": {
        "file": "agents/a1_geoscout.py",
        "writes": ("candidatos_geoscout_pronto", "candidatos_geoscout"),
        "reads": ("input_params", "market_context"),
        "notes": (
            "BaseAgent. Listing SearchAPI + MRLR. Macro POI morta. "
            "price_raw = display; decisão = MRLR."
        ),
    },
    "A2": {
        "file": "agents/a2_demo_analyst.py",
        "writes": ("analise_demografica",),
        "reads": ("input_params", "market_context"),
        "notes": "BaseAgent. IBGE Censo 2022 + perfil sexo/idade + densidade setor.",
    },
    "A3a": {
        "file": "agents/a3a_competitor_search.py",
        "writes": ("concorrentes_brutos",),
        "reads": ("input_params", "market_context"),
        "notes": (
            "BaseAgent. SearchAPI google_maps + reviews. Contagem R=1000m "
            "centróide + tipo/status (sem gate string bairro)."
        ),
    },
    "A3b": {
        "file": "agents/a3b_competitor_analysis.py",
        "writes": ("inteligencia_competitiva", "oferta_concorrentes"),
        "reads": ("concorrentes_brutos", "market_context", "input_params"),
        "notes": (
            "BaseAgent. Fundiu A3c: oferta site+IG mesclada nos concorrentes. "
            "Alimenta gaps reais do A9."
        ),
    },
    "A4": {
        "file": "agents/a4_financial_estimator.py",
        "writes": ("analise_financeira_pronto", "analise_financeira"),
        "reads": (
            "input_params",
            "market_context",
            "candidatos_geoscout_pronto",
            "candidatos_geoscout",  # fallback se _pronto ausente
        ),
        "notes": (
            "BaseAgent. Aluguel = MRLR Tier 0 (nunca SearchAPI/A7/portais). "
            "A6 lê preferencialmente analise_financeira_pronto."
        ),
    },
    "A6": {
        "file": "agents/a6_report_consolidator.py",
        "writes": ("relatorio_md", "demografia_bairro"),
        "reads": (
            "input_params",
            "market_context",
            "analise_demografica",
            "inteligencia_competitiva",
            "oferta_concorrentes",
            "analise_financeira_pronto",
            "candidatos_geoscout_pronto",
            "candidatos_geoscout",  # fallback Top3
            "concorrentes_brutos",  # contagem / mapa
            "demanda_futura",  # entrypoint enrichment
        ),
        "notes": (
            "LLM narra; números de snapshot/Top3/MRLR/crowdsource injetados. "
            "demografia_bairro: calcula e grava no state p/ A9. "
            "contato_decisor é opcional (A5 fora do Sequential)."
        ),
    },
    "A9": {
        "file": "agents/a9_positioning_strategist.py",
        "writes": ("relatorio_posicionamento_md", "relatorio_posicionamento"),
        "reads": (
            "input_params",
            "market_context",
            "inteligencia_competitiva",
            "oferta_concorrentes",
            "concorrentes_brutos",
            "analise_financeira",
            "relatorio_md",  # A8 pós-A9 + coerência
            "demanda_futura",
            "demografia_bairro",  # Brilliant Basics público maduro
        ),
        "notes": (
            "BaseAgent. ERRC determinística (headroom IBGE × oferta real). "
            "demografia_bairro vem do bridge A6→state (não de analise_demografica)."
        ),
    },
}


def producers() -> dict[str, str]:
    """chave de state → agente (ou 'entrypoint') que escreve."""
    out: dict[str, str] = {k: "entrypoint" for k in ENTRYPOINT_WRITES}
    for agent, dep in AGENT_DEPS.items():
        for key in dep["writes"]:
            out[key] = agent
    return out


def consumers_of(key: str) -> list[str]:
    """Agentes que declaram ler `key`."""
    return [a for a, dep in AGENT_DEPS.items() if key in dep["reads"]]


def reverse_cards() -> list[dict]:
    """Cartões do loop reverso: contrato + consumidores + entradas."""
    prod = producers()
    cards = []
    for agent in REVERSE_ORDER:
        dep = AGENT_DEPS[agent]
        writes = list(dep["writes"])
        consumers: dict[str, list[str]] = {}
        for w in writes:
            cons = consumers_of(w)
            if not cons and w in TERMINAL_WRITES:
                cons = ["persistência/PDF"]
            consumers[w] = cons
        inputs = []
        for r in dep["reads"]:
            inputs.append({"key": r, "from": prod.get(r, "DESCONHECIDO")})
        cards.append(
            {
                "agent": agent,
                "file": dep["file"],
                "writes": writes,
                "consumers": consumers,
                "inputs": inputs,
                "notes": dep["notes"],
            }
        )
    return cards
