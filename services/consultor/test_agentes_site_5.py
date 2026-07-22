"""modo_site com 5 agentes: Arquiteto e Engenheiro de Obra além de Mercado/Técnico/
Regulatório. Rota B da Fase 3a (levar os 5 à landing via consultor_engine, que já roda
em prod), sem depender da migração ADK."""
from __future__ import annotations


def test_registry_tem_5_agentes():
    from services.consultor.consultor_engine import _AGENTES_SITE

    assert set(_AGENTES_SITE) == {
        "degustacao", "responsavel_tecnico", "regulatorio", "arquiteto", "engenheiro_obra",
    }


def test_arquiteto_tools_e_persona():
    from services.consultor.consultor_engine import _agente_cfg

    cfg = _agente_cfg("arquiteto")
    assert cfg["tools"] == frozenset({"consultar_engenharia_obra", "calcular_sanitarios_por_lotacao"})
    assert "Arquiteto" in cfg["persona"]


def test_engenheiro_tools_e_persona():
    from services.consultor.consultor_engine import _agente_cfg

    cfg = _agente_cfg("engenheiro_obra")
    assert cfg["tools"] == frozenset({"consultar_engenharia_obra"})
    assert "Engenheiro de Obra" in cfg["persona"]


def test_regulatorio_tools_lookups_p0():
    from services.consultor.consultor_engine import _agente_cfg

    cfg = _agente_cfg("regulatorio")
    assert "resolver_cref_por_uf" in cfg["tools"]
    assert "consultar_anuidade_pj_cref" in cfg["tools"]
    assert "consultar_base_conhecimento" in cfg["tools"]


def test_tools_novas_declaradas_no_contrato():
    """As 2 tools novas têm FunctionDeclaration (senão o LLM não as chama)."""
    from services.consultor import consultor_engine as ce

    # A lista de declarations é montada em _tool_decls_agente / _TOOLS; procura os nomes.
    import inspect
    src = inspect.getsource(ce)
    assert 'name="consultar_engenharia_obra"' in src
    assert 'name="calcular_sanitarios_por_lotacao"' in src
    assert 'name="resolver_cref_por_uf"' in src
    assert 'name="consultar_anuidade_pj_cref"' in src
    # E o dispatch conhece as duas (elif por nome).
    assert 'nome == "consultar_engenharia_obra"' in src
    assert 'nome == "calcular_sanitarios_por_lotacao"' in src
    assert 'nome == "resolver_cref_por_uf"' in src
    assert 'nome == "consultar_anuidade_pj_cref"' in src
