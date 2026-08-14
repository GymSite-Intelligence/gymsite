"""RN-A4-11: todos cenários INVIAVEL → modelo nenhum."""

from tools.financial_tools import _escolher_cenario_recomendado, _resumo_decisao_a4


def _cenario(modelo: str, viab: str = "INVIAVEL", lucro: float = -1000.0) -> dict:
    return {
        "modelo": modelo,
        "lucro_mensal_estimado": lucro,
        "payback_meses": 999,
        "viabilidade": viab,
        "justificativa": f"base {modelo}",
        "capacidade_maxima_alunos": 100,
        "alunos_break_even": 80,
        "margem_percentual": -5,
        "receita_mensal": 10000,
        "custos_detalhados": {"aluguel": 20000},
    }


def test_escolher_todos_inviaveis_retorna_nenhum():
    cenarios = {
        "low": _cenario("Low Cost"),
        "mid": _cenario("Mid Market"),
        "premium": _cenario("Premium"),
    }
    escolhido = _escolher_cenario_recomendado(cenarios, renda_media_bairro=2000.0)
    assert escolhido["modelo"] == "nenhum"
    assert escolhido["alerta_viabilidade"] == "todos_cenarios_inviaveis"
    assert set(escolhido["cenarios_inviaveis"]) == {"low", "mid", "premium"}


def test_escolher_um_viavel_nao_retorna_nenhum():
    cenarios = {
        "low": _cenario("Low Cost", viab="ALTO", lucro=5000),
        "mid": _cenario("Mid Market"),
        "premium": _cenario("Premium"),
    }
    escolhido = _escolher_cenario_recomendado(cenarios, renda_media_bairro=2000.0)
    assert escolhido["modelo"] != "nenhum"
    assert "Low" in escolhido["modelo"]


def test_resumo_decisao_todos_inviaveis():
    fin = {
        "recomendacao": "Low Cost",
        "cenarios": {
            "low": _cenario("Low Cost"),
            "mid": _cenario("Mid Market"),
            "premium": _cenario("Premium"),
        },
    }
    dec = _resumo_decisao_a4(fin)
    assert dec["recomendacao_modelo"] == "nenhum"
    assert dec["modelo_recomendado"] == "nenhum"
    assert dec["score_viabilidade"] == 0.0
    assert dec["alerta_viabilidade"] == "todos_cenarios_inviaveis"


def test_resumo_decisao_ja_nenhum():
    fin = {
        "recomendacao": "nenhum",
        "cenarios": {
            "low": _cenario("Low Cost"),
            "mid": _cenario("Mid Market"),
            "premium": _cenario("Premium"),
        },
    }
    dec = _resumo_decisao_a4(fin)
    assert dec["recomendacao_modelo"] == "nenhum"
