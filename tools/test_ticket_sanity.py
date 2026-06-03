"""Tickets financeiros — sanitização Grounding + teto por renda bairro."""
from tools.benchmarks_tool import reset_cache, sanitizar_ticket_por_modelo
from tools.financial_tools import calcular_viabilidade_3_cenarios


def test_sanitizar_premium_1500_grounding():
    limpos, avisos = sanitizar_ticket_por_modelo(
        {"low": 120.0, "mid": 300.0, "premium": 1500.0}
    )
    assert limpos["premium"] == 299.90
    assert limpos["mid"] == 149.90
    assert any("premium" in a for a in avisos)


def test_premium_capado_por_renda_aldeota():
    reset_cache()
    from tools import benchmarks_tool

    benchmarks_tool._MEM_CACHE = {
        "ticket_por_modelo": {
            "low": 120.0,
            "mid": 300.0,
            "premium": 1500.0,
        },
        "fonte": "test",
    }
    r = calcular_viabilidade_3_cenarios(
        area_m2=1150,
        aluguel_mensal=40000,
        bairro="Aldeota",
        cidade="Fortaleza",
        uf="CE",
        renda_media_bairro=5200,
    )
    prem = r["cenarios"]["premium"]
    assert prem["ticket_medio"] <= 780  # 15% de R$ 5.200
    assert prem["ticket_medio"] < 750
    assert r["recomendacao"] != "Premium" or prem["ticket_medio"] < 750
