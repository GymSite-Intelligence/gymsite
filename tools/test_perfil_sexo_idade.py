"""Gancho mkt sexo×idade: agrega populacao_idade_sexo por sexo, % e insight.
Best-effort — sem código/erro → None (A2 degrada)."""
from unittest.mock import patch

import tools.perfil_sexo_idade_tools as t


def test_none_safe():
    assert t.perfil_sexo_publico_fitness(None) is None
    assert t.perfil_sexo_publico_fitness("abc") is None
    assert t.insight_gancho_mkt(None) is None


def test_espelho_supabase_primeiro():
    # PRIMÁRIO: lê o espelho Supabase (funciona em prod sem BQ)
    fake = {"id_municipio": "2304400", "faixa_idade": "25-40", "homens": 305492,
            "mulheres": 341771, "total": 647263, "pct_homens": 47.2, "pct_mulheres": 52.8,
            "maioria": "feminino", "fonte": "x", "granularidade": "municipio"}
    with patch.object(t, "_perfil_do_espelho_supabase", return_value=fake):
        p = t.perfil_sexo_publico_fitness("2304400")
    assert p["pct_mulheres"] == 52.8 and p["maioria"] == "feminino"


def test_fallback_bq_quando_espelho_vazio():
    rows = [{"sexo": "Homens", "pop": 305492}, {"sexo": "Mulheres", "pop": 341771}]
    with patch.object(t, "_perfil_do_espelho_supabase", return_value=None), \
         patch("tools.basedosdados_loader.run_query", return_value=rows):
        p = t.perfil_sexo_publico_fitness("2304400")
    assert p["pct_homens"] == 47.2 and p["pct_mulheres"] == 52.8
    assert t.insight_gancho_mkt(p) and "Censo 2022" in t.insight_gancho_mkt(p)


def test_total_zero_retorna_none():
    with patch.object(t, "_perfil_do_espelho_supabase", return_value=None), \
         patch("tools.basedosdados_loader.run_query", return_value=[{"sexo": "Homens", "pop": 0}]):
        assert t.perfil_sexo_publico_fitness("2304400") is None


def test_bq_falha_degrada():
    def boom(_q):
        raise RuntimeError("BQ down")
    with patch.object(t, "_perfil_do_espelho_supabase", return_value=None), \
         patch("tools.basedosdados_loader.run_query", side_effect=boom):
        assert t.perfil_sexo_publico_fitness("2304400") is None
