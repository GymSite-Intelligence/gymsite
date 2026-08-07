"""PDF: Absorção — leitura executiva (vernáculo)."""


def test_html_has_absorcao_section():
    from pdf.html_builder import _TEMPLATE, _contexto, gerar_html
    from pdf.models import RelatorioPdfModel

    assert "Absorção de alunos — leitura executiva" in _TEMPLATE
    assert "Alunos (estimativa)" in _TEMPLATE
    assert "form ×" not in _TEMPLATE
    assert "Pool primário (form" not in _TEMPLATE

    model = RelatorioPdfModel(
        relatorio_id="t-absorcao",
        data_execucao="2026-08-07",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        tipo_negocio="academia",
        area_m2_min=800,
        area_m2_max=1500,
        publico_alvo=None,
        veredito="TRANSICAO",
        score_bairro=None,
        score_top1=None,
        posicionamento_estrategico={
            "veredito_posicionamento": "TRANSICAO",
            "absorcao_margem_fresca": {
                "teto_unidade": 2100,
                "capacidade_parque_estimada": 14200,
                "pool_demografico": 1221,
                "pool_primario": 1221,
                "pool_secundario": 642,
                "pool_total_15mais": 1863,
                "estoque_primario": 30520,
                "estoque_secundario": 16050,
                "faixas_primario": ["25-39", "40-59"],
                "faixas_secundario": ["15-24", "60+"],
                "margem_fresca": -12979,
                "rotulo": "roubo",
                "carimbos": {
                    "teto_unidade": "2100 · área×densidade · ACAD",
                    "capacidade_parque_estimada": "14200 · proxy porte · franquia",
                    "pool_demografico": "1221 · estoque×interesse×pen · IBGE",
                    "margem_fresca": "-12979 · potencial−oferta · derivada",
                },
            },
        },
    )
    ctx = _contexto(model)
    assert ctx.get("absorcao")
    assert ctx["absorcao"]["blocos"]
    assert any("formulário" in b["titulo"].lower() or "público" in b["titulo"].lower() for b in ctx["absorcao"]["blocos"])
    html = gerar_html(model)
    assert "alunos estimados" in html.lower()
    assert "25-39 · Core" in html or "Core" in html
    assert "Conclusão" in html
    assert "form ×" not in html
    assert "absorver" in html.lower() or "outra academia" in html.lower()
