"""Deterministic Mermaid diagram router — no LLM, ordered rules."""
from __future__ import annotations

from tools.mermaid_diagram_router import (
    DiagramChoice,
    detectar_sinais,
    escolher_diagrama,
    listar_regras,
)


def test_intent_explicito_vence_keyword():
    # texto sugere gantt, mas intent diz sequence
    c = escolher_diagrama(
        "cronograma gantt roadmap",
        intent="sequencia",
    )
    assert c.tipo == "sequenceDiagram"
    assert c.fonte == "intent_explicito"
    assert c.confianca == "alta"


def test_signal_serie_temporal():
    c = escolher_diagrama("qualquer texto", dados={"series": [10, 20, 30, 40]})
    assert c.tipo == "xychart-beta"
    assert c.fonte == "signal"
    assert "numeric_series" in c.regras_aplicadas


def test_signal_entidades():
    c = escolher_diagrama(
        "",
        dados={"entities": ["customer", "order"], "relations": ["places"]},
    )
    assert c.tipo == "erDiagram"
    assert c.fonte == "signal"


def test_keyword_jornada():
    c = escolher_diagrama("quero mapear a jornada do usuario na degustacao")
    assert c.tipo == "journey"
    assert c.fonte == "keyword"


def test_keyword_pipeline_flowchart():
    c = escolher_diagrama("arquitetura do pipeline A0-A9 e orquestracao")
    assert c.tipo == "flowchart"
    assert c.intent == "fluxo"


def test_nao_pega_status_como_state_diagram():
    c = escolher_diagrama("status do relatorio ainda queued running done")
    assert c.tipo == "flowchart"
    assert c.fonte == "default"


def test_nao_pega_commit_como_git_graph():
    c = escolher_diagrama("preciso fazer commit do fix no branch e merge")
    assert c.tipo != "gitGraph"
    assert c.fonte in {"default", "keyword"}
    if c.fonte == "keyword":
        assert c.tipo == "flowchart"


def test_nao_pega_tabela_como_er():
    c = escolher_diagrama("tabela de concorrentes no supabase com fk")
    assert c.tipo != "erDiagram"


def test_default_flowchart_sem_pista():
    c = escolher_diagrama("olá")
    assert c.tipo == "flowchart"
    assert c.fonte == "default"
    assert c.confianca == "baixa"


def test_escolher_e_deterministico():
    a = escolher_diagrama("matriz 2x2 impacto vs esforco", intent=None)
    b = escolher_diagrama("matriz 2x2 impacto vs esforco", intent=None)
    assert a == b
    assert a.tipo == "quadrantChart"


def test_detectar_sinais_actors():
    s = detectar_sinais({"actors": ["Mercado", "SearchAPI"], "messages": []})
    assert "actors_messages" in s


def test_listar_regras_tem_todos_tipos_base():
    tipos = {r["tipo"] for r in listar_regras()}
    for t in (
        "flowchart",
        "sequenceDiagram",
        "gantt",
        "classDiagram",
        "gitGraph",
        "erDiagram",
        "journey",
        "quadrantChart",
        "xychart-beta",
    ):
        assert t in tipos


def test_diagram_choice_serializavel():
    c = escolher_diagrama(intent="git")
    assert isinstance(c, DiagramChoice)
    d = c.as_dict()
    assert d["tipo"] == "gitGraph"
    assert d["fonte"] == "intent_explicito"
