"""Testes — seção pré-computada MRLR no A6."""
from agents.a6_report_consolidator import _renderizar_secao_referencia_aluguel


def test_render_referencia_aluguel_mrlr() -> None:
    inner_fin = {
        "fonte_aluguel": "MRLR IBAPE-GO (determinístico)",
        "aluguel_mensal": 10_000.0,
        "aluguel_mediana_m2": 12.5,
        "area_m2": 800,
        "aluguel_mrlr_inputs": {
            "municipio": "Pirapora",
            "bairro": "Centro",
            "fonte_porte": "municipio_pib",
            "fonte_renda": "renda_bairro",
        },
        "aviso_metodologia_aluguel": "Aluguel determinístico por MRLR.",
    }
    md = _renderizar_secao_referencia_aluguel(inner_fin)
    assert "ALUGUEL MRLR" in md
    assert "R$ 10.000,00" in md
    assert "R$ 12,50/m²" in md
    assert "municipio_pib" in md and "renda_bairro" in md
    assert "Search Grounding" not in md
    assert "Portais" not in md


def test_render_mrlr_indisponivel_sem_fallback_portal() -> None:
    md = _renderizar_secao_referencia_aluguel(
        {
            "fonte_aluguel": "Benchmark ACAD / FipeZap",
            "aviso_metodologia_aluguel": "MRLR indisponível.",
        }
    )
    assert "MRLR indisponível" in md
    assert "validar cotação local" in md
    assert "Search Grounding" not in md
    assert "Portais" not in md
