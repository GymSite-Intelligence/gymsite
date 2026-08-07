"""PDF: seção Modelo de Negócio Adequado (matriz demo × saturação)."""


def test_pdf_matriz_armadilha_section():
    from pdf.html_builder import _TEMPLATE, _contexto, gerar_html
    from pdf.models import RelatorioPdfModel

    assert "Modelo de Negócio Adequado" in _TEMPLATE

    model = RelatorioPdfModel(
        relatorio_id="t-matriz",
        data_execucao="2026-08-07",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        tipo_negocio="academia",
        area_m2_min=800,
        area_m2_max=1500,
        publico_alvo=None,
        veredito="OCEANO_AZUL",
        score_bairro=None,
        score_top1=None,
        posicionamento_estrategico={
            "veredito_posicionamento": "OCEANO_AZUL",
            "matriz_demo_saturacao": {
                "quadrante": "Armadilha de Renda",
                "modelo_sugerido": "nicho_ou_mid_high",
                "n_poligono": 3,
                "n_per_10k": 0.6,
                "mix": {"low": 1, "mid": 0, "premium": 2, "nicho": 0, "desconhecido": 0},
                "rating_medio": 4.2,
                "censo_base": "poligono_ibge_bairro",
                "fonte_espacial": "poligono_ibge_bairro",
                "acao_estrategica": "Não abrir Premium genérico: ≥2 Premium no polígono.",
                "carimbo": "Armadilha de Renda · N=3 (0.60/10k) · poligono_ibge_bairro · poligono_ibge_bairro",
            },
        },
    )
    ctx = _contexto(model)
    assert ctx.get("matriz")
    assert ctx["matriz"]["quadrante"] == "Armadilha de Renda"
    html = gerar_html(model)
    assert "Modelo de Negócio Adequado" in html
    assert "Armadilha" in html
