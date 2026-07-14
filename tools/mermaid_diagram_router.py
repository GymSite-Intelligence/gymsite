"""Deterministic Mermaid diagram type routing (no LLM).

Agents/scripts call `escolher_diagrama(...)` with an optional explicit intent
and/or free text + data shape signals. First matching rule wins (ordered by
priority). Rendering stays outside: use `scripts/batch/render_mermaid_diagram.py`
against Mermaid Chart MCP (`validate_and_render_mermaid_diagram`).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from tools.bairro_normalize import fold_texto

# Explicit intents agents may pass (stable vocabulary — never invent ad-hoc strings).
INTENTS = frozenset({
    "fluxo",
    "sequencia",
    "cronograma",
    "classes",
    "git",
    "entidades",
    "jornada",
    "priorizacao",
    "serie_temporal",
    "proporcao",
    "estados",
    "mapa_mental",
})

# (tipo_mermaid, intent_canonico, keywords_pt, signals_obrigatorios, priority)
# priority: maior = primeiro. keywords viram fold_texto.
_RULES: tuple[dict[str, Any], ...] = (
    {
        "tipo": "sequenceDiagram",
        "intent": "sequencia",
        "keywords": (
            "sequence", "sequencia", "turno a turno", "handshake", "mensagem entre",
            "alice", "request response", "quem chama quem no tempo",
        ),
        "signals": ("actors_messages",),
        "priority": 100,
        "quando": "Conversas/chamadas entre atores no tempo (agente↔tool↔API).",
    },
    {
        "tipo": "gantt",
        "intent": "cronograma",
        "keywords": (
            "gantt", "cronograma", "roadmap", "timeline de projeto",
            "fase 1", "marco", "deadline",
        ),
        "signals": ("time_ranges",),
        "priority": 90,
        "quando": "Datas de início/fim, fases, marcos.",
    },
    {
        "tipo": "erDiagram",
        "intent": "entidades",
        "keywords": (
            "er diagram", "entidade-relacionamento", "diagrama er",
            "1:n", "n:n", "modelo de dados", "schema supabase",
        ),
        "signals": ("entities_relations",),
        "priority": 85,
        "quando": "Tabelas/entidades e cardinalidade.",
    },
    {
        "tipo": "classDiagram",
        "intent": "classes",
        "keywords": (
            "class diagram", "diagrama de classes", "heranca", "uml",
        ),
        "signals": ("oop_types",),
        "priority": 80,
        "quando": "Tipos/classes/métodos do código.",
    },
    {
        "tipo": "gitGraph",
        "intent": "git",
        "keywords": (
            "git graph", "gitgraph", "release branch", "main develop",
            "historico de branches", "merge commit graph",
        ),
        "signals": ("git_refs",),
        "priority": 75,
        "quando": "Histórico de branches/commits.",
    },
    {
        "tipo": "journey",
        "intent": "jornada",
        "keywords": (
            "jornada", "user journey", "experiencia do usuario", "onboarding",
            "cliente percorre", "setor por secao",
        ),
        "signals": ("journey_steps",),
        "priority": 70,
        "quando": "Passos da experiência do usuário com score.",
    },
    {
        "tipo": "quadrantChart",
        "intent": "priorizacao",
        "keywords": (
            "quadrant", "matriz 2x2", "eixo x", "eixo y", "priorizacao",
            "impacto vs esforco", "impacto versus esforco",
        ),
        "signals": ("xy_points",),
        "priority": 65,
        "quando": "Itens plotados em 2 eixos contínuos 0–1.",
    },
    {
        "tipo": "xychart-beta",
        "intent": "serie_temporal",
        "keywords": (
            "xychart", "serie temporal", "grafico de barras",
            "linha do tempo numerica", "kpi mensal",
        ),
        "signals": ("numeric_series",),
        "priority": 60,
        "quando": "Série numérica rotulada (ex.: créditos/mês).",
    },
    {
        "tipo": "pie",
        "intent": "proporcao",
        "keywords": (
            "pie chart", "grafico de pizza", "proporcao", "% do total",
            "distribuicao percentual", "parts of whole",
        ),
        "signals": ("parts_of_whole",),
        "priority": 55,
        "quando": "Partes de um todo (somas para 100%).",
    },
    {
        "tipo": "stateDiagram-v2",
        "intent": "estados",
        "keywords": (
            "state diagram", "maquina de estados", "diagrama de estados",
            "transicao de estado",
        ),
        "signals": ("state_machine",),
        "priority": 50,
        "quando": "Estados e transições.",
    },
    {
        "tipo": "mindmap",
        "intent": "mapa_mental",
        "keywords": ("mindmap", "mapa mental", "brainstorm", "arvore de topicos"),
        "signals": ("topic_tree",),
        "priority": 40,
        "quando": "Hierarquia de tópicos sem fluxo temporal.",
    },
    {
        "tipo": "flowchart",
        "intent": "fluxo",
        "keywords": (
            "flowchart", "fluxo", "pipeline", "arquitetura", "cascata",
            "orquestracao", "decisao", "se entao", "diagrama de fluxo",
        ),
        "signals": ("nodes_edges",),
        "priority": 30,
        "quando": "Fluxo/processo/arquitetura (default seguro).",
    },
)

# Tokens curtos demais para substring livre (evita "status", "commit", "tabela").
_MIN_TOKEN_LEN = 4


@dataclass(frozen=True)
class DiagramChoice:
    tipo: str
    intent: str
    fonte: str  # intent_explicito | signal | keyword | default
    confianca: str  # alta | media | baixa
    quando: str
    regras_aplicadas: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def detectar_sinais(dados: Optional[dict[str, Any]] = None) -> set[str]:
    """Infer data-shape signals from a structured payload (never from LLM)."""
    d = dados or {}
    signals: set[str] = set()

    if d.get("messages") or d.get("actors") or d.get("turnos"):
        signals.add("actors_messages")
    if d.get("tasks") or d.get("fases") or d.get("cronograma") or d.get("dateFormat"):
        signals.add("time_ranges")
    if d.get("entities") or d.get("tabelas") or d.get("relations"):
        signals.add("entities_relations")
    if d.get("classes") or d.get("types"):
        signals.add("oop_types")
    if d.get("commits") or d.get("branches"):
        signals.add("git_refs")
    if d.get("sections") and d.get("steps"):
        signals.add("journey_steps")
    pts = d.get("points") or d.get("campanhas")
    if isinstance(pts, list) and pts and isinstance(pts[0], (list, tuple, dict)):
        signals.add("xy_points")
    series = d.get("series") or d.get("valores") or d.get("barras")
    if isinstance(series, (list, tuple)) and series and all(
        isinstance(x, (int, float)) for x in series
    ):
        signals.add("numeric_series")
    parts = d.get("slices") or d.get("partes")
    if isinstance(parts, dict) and parts:
        signals.add("parts_of_whole")
    if d.get("states") or d.get("transicoes"):
        signals.add("state_machine")
    if d.get("topics") or d.get("arvore"):
        signals.add("topic_tree")
    if d.get("nodes") or d.get("edges") or d.get("pipeline"):
        signals.add("nodes_edges")
    return signals


def _kw_hit(texto_fold: str, keywords: tuple[str, ...]) -> str | None:
    """Match keywords; single-token hits use word boundaries (no bare substrings)."""
    for kw in keywords:
        fk = fold_texto(kw)
        if not fk:
            continue
        if " " in fk or "-" in fk or ":" in fk:
            if fk in texto_fold:
                return kw
            continue
        if len(fk) < _MIN_TOKEN_LEN:
            continue
        if re.search(rf"(?<![a-z0-9_]){re.escape(fk)}(?![a-z0-9_])", texto_fold):
            return kw
    return None


def escolher_diagrama(
    texto: str = "",
    *,
    intent: Optional[str] = None,
    dados: Optional[dict[str, Any]] = None,
) -> DiagramChoice:
    """Pick Mermaid diagram type deterministically.

    Precedence:
      1) explicit `intent` (must be in INTENTS)
      2) data-shape `signals` from `dados`
      3) keyword match on `texto`
      4) default flowchart
    """
    rules = sorted(_RULES, key=lambda r: -int(r["priority"]))
    texto_fold = fold_texto(texto or "")
    signals = detectar_sinais(dados)

    intent_n = fold_texto(intent or "")
    if intent_n:
        # map aliases
        aliases = {
            "fluxo": "fluxo",
            "flowchart": "fluxo",
            "arquitetura": "fluxo",
            "pipeline": "fluxo",
            "sequencia": "sequencia",
            "sequence": "sequencia",
            "cronograma": "cronograma",
            "gantt": "cronograma",
            "roadmap": "cronograma",
            "classes": "classes",
            "class": "classes",
            "git": "git",
            "entidades": "entidades",
            "er": "entidades",
            "schema": "entidades",
            "jornada": "jornada",
            "journey": "jornada",
            "priorizacao": "priorizacao",
            "quadrant": "priorizacao",
            "serie_temporal": "serie_temporal",
            "serie": "serie_temporal",
            "xychart": "serie_temporal",
            "proporcao": "proporcao",
            "pie": "proporcao",
            "estados": "estados",
            "state": "estados",
            "mapa_mental": "mapa_mental",
            "mindmap": "mapa_mental",
        }
        mapped = aliases.get(intent_n, intent_n)
        for r in rules:
            if r["intent"] == mapped:
                return DiagramChoice(
                    tipo=r["tipo"],
                    intent=r["intent"],
                    fonte="intent_explicito",
                    confianca="alta",
                    quando=r["quando"],
                    regras_aplicadas=(f"intent:{mapped}",),
                )
        # unknown intent → fall through (do not crash)

    # Signals first (structural evidence beats prose keywords)
    for r in rules:
        need = set(r.get("signals") or ())
        if need and need.issubset(signals):
            return DiagramChoice(
                tipo=r["tipo"],
                intent=r["intent"],
                fonte="signal",
                confianca="alta",
                quando=r["quando"],
                regras_aplicadas=tuple(sorted(need)),
            )

    if texto_fold:
        for r in rules:
            hit = _kw_hit(texto_fold, tuple(r["keywords"]))
            if hit:
                return DiagramChoice(
                    tipo=r["tipo"],
                    intent=r["intent"],
                    fonte="keyword",
                    confianca="media",
                    quando=r["quando"],
                    regras_aplicadas=(f"kw:{hit}",),
                )

    default = next(r for r in rules if r["tipo"] == "flowchart")
    return DiagramChoice(
        tipo=default["tipo"],
        intent=default["intent"],
        fonte="default",
        confianca="baixa",
        quando=default["quando"],
        regras_aplicadas=("fallback:flowchart",),
    )


def listar_regras() -> list[dict[str, Any]]:
    return [
        {
            "tipo": r["tipo"],
            "intent": r["intent"],
            "priority": r["priority"],
            "quando": r["quando"],
            "signals": list(r.get("signals") or ()),
            "keywords": list(r["keywords"]),
        }
        for r in sorted(_RULES, key=lambda x: -x["priority"])
    ]
