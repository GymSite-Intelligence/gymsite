"""Testes — seção pré-computada de referência de aluguel no A6."""
from agents.a6_report_consolidator import _renderizar_secao_referencia_aluguel


def test_render_referencia_aluguel_tier2_portais_vazios() -> None:
    inner_fin = {
        "fonte_aluguel": "Search Grounding (mediana de 2 queries)",
        "aviso_metodologia_aluguel": "⚠️ Portais sem amostra. Fonte ativa: Search Grounding.",
        "aluguel_pesquisa_detalhes": {
            "tier": 2,
            "tier1_vazio": True,
            "tier1_suficiente": False,
            "n_validos_tier1": 0,
            "motivo_tier1": "Portais municipais: nenhum anúncio válido.",
            "mediana_r_m2": 42.0,
            "queries_com_dados": 2,
            "tier1_tentativa": {"urls_por_portal": {"zap": 1, "olx": 2}},
        },
        "referencia_macro_bcb": {
            "ok": True,
            "norte": "Panorama macro BCB — crédito imobiliário.",
        },
    }
    md = _renderizar_secao_referencia_aluguel(inner_fin)
    assert "REFERÊNCIA DE ALUGUEL" in md
    assert "N=0" in md
    assert "Search Grounding" in md
    assert "não é aluguel local" in md.lower() or "não** é aluguel local" in md


def test_render_vazio_sem_tier() -> None:
    assert _renderizar_secao_referencia_aluguel({}) == ""
