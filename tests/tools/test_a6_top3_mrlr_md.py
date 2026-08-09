from agents.a6_report_consolidator import _renderizar_md_top3_candidatos


def test_top3_mrlr_renderiza_composto_payback_e_carimbo():
    markdown = _renderizar_md_top3_candidatos(
        [
            {
                "nome": "Galpão Centro",
                "endereco": "Centro, Pirapora - MG",
                "area_m2": 800,
                "score_geoscout": 7,
                "score_geo_norm": 0.7,
                "score_payback_norm": 0.8,
                "score_composto": 0.765,
                "aluguel_mrlr_mensal": 10_000,
                "carimbo_aluguel": (
                    "R$ 10.000,00 · 800 m² do listing · MRLR · R$ 12,50/m²"
                ),
                "payback_est_meses": 18.2,
                "qualidade_sinal": "direto-listing-bairro",
            }
        ]
    )

    assert "Score composto" in markdown
    assert "35% geo / 65% payback" in markdown
    assert "Payback estimado" in markdown
    assert "18.2 meses" in markdown
    assert "MRLR" in markdown
    assert "R$ 10.000,00" in markdown
    assert "preço do anúncio" not in markdown.lower()


def test_top3_sem_viabilidade_mostra_aviso():
    markdown = _renderizar_md_top3_candidatos(
        [
            {
                "nome": "Loja",
                "endereco": "Centro, Pirapora - MG",
                "score_geoscout": 6,
                "aviso_viabilidade": (
                    "Viabilidade indisponível — ordenação apenas por localização."
                ),
            }
        ]
    )

    assert "Viabilidade indisponível" in markdown
