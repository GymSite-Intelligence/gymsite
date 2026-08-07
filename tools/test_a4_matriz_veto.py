"""A4: Armadilha de Renda veta Premium genérico."""

from tools.financial_tools import _escolher_cenario_recomendado, _faixa_key_de_modelo


def _cenario(modelo: str, lucro: float, payback: int, viab: str = "ALTO") -> dict:
    return {
        "modelo": modelo,
        "lucro_mensal_estimado": lucro,
        "payback_meses": payback,
        "viabilidade": viab,
        "justificativa": f"base {modelo}",
    }


def test_armadilha_veta_premium():
    cenarios = {
        "low": _cenario("Low Cost", 8000, 36),
        "mid": _cenario("Mid Market", 12000, 30),
        "premium": _cenario("Premium", 20000, 24),  # best by lucro/tier
    }
    # Renda alta enough that preferido = premium (typically)
    escolhido = _escolher_cenario_recomendado(
        cenarios,
        renda_media_bairro=8000.0,
        renda_percentil=0.9,
        matriz_demo_saturacao={"quadrante": "Armadilha de Renda"},
    )
    assert _faixa_key_de_modelo(escolhido.get("modelo", "")) != "premium"
    assert "Armadilha" in (escolhido.get("justificativa_matriz") or "")


def test_sem_matriz_pode_premium():
    cenarios = {
        "low": _cenario("Low Cost", 8000, 36),
        "mid": _cenario("Mid Market", 12000, 30),
        "premium": _cenario("Premium", 20000, 24),
    }
    escolhido = _escolher_cenario_recomendado(
        cenarios,
        renda_media_bairro=8000.0,
        renda_percentil=0.9,
        matriz_demo_saturacao=None,
    )
    # Without matriz, premium may win on rich neighborhood — assert no matriz veto
    assert escolhido.get("justificativa_matriz") is None
