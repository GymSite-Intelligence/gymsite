"""PDF demografia: rótulos honestos (raio/setores), sem 'fonte real do bairro'."""


def test_pdf_demografia_header_not_fonte_real_do_bairro():
    from pdf.html_builder import _TEMPLATE

    assert "fonte real do bairro" not in _TEMPLATE
    assert "População (bairro)" not in _TEMPLATE
    assert "raio" in _TEMPLATE.lower() or "setores" in _TEMPLATE.lower()


def test_pdf_pop_poligono_ibge_sem_raio_centrode():
    from pdf.html_builder import _contexto
    from pdf.models import RelatorioPdfModel

    model = RelatorioPdfModel(
        relatorio_id="t",
        data_execucao="2026-08-06",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        tipo_negocio="academia",
        area_m2_min=800,
        area_m2_max=1500,
        publico_alvo=None,
        veredito=None,
        score_bairro=None,
        score_top1=None,
        metadata={
            "demografia_bairro": {
                "populacao": 60165,
                "renda_media": 4812,
                "domicilios": 22847,
                "censo_n_setores": 105,
                "censo_base": "poligono_ibge_bairro",
                "censo_raio_m": None,
                "censo_cd_bairro": "2304400015",
                "perfil_idade_sexo_bairro": {
                    "n_setores": 105,
                    "segmentos": {
                        "25-39": {"total": 18420, "homens": 8657, "mulheres": 9763,
                                  "pct_homens": 47.0, "pct_mulheres": 53.0},
                    },
                },
            }
        },
    )
    ctx = _contexto(model)
    demo = ctx.get("demografia") or {}
    pop = demo.get("populacao") or ""
    assert "polígono IBGE" in pop
    assert "raio do centróide" not in pop
    assert demo.get("censo_base") == "poligono_ibge_bairro"


def test_pdf_conciliacao_pop_vs_faixas_15mais():
    """Pop total ≠ soma 15+ (faltam 0–14); com Spec C n_setores pop = pirâmide."""
    from pdf.html_builder import _contexto, gerar_html
    from pdf.models import RelatorioPdfModel

    model = RelatorioPdfModel(
        relatorio_id="t-conc",
        data_execucao="2026-08-07",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        tipo_negocio="academia",
        area_m2_min=800,
        area_m2_max=1500,
        publico_alvo=None,
        veredito=None,
        score_bairro=None,
        score_top1=None,
        metadata={
            "demografia_bairro": {
                "populacao": 60165,
                "renda_media": 4812,
                "domicilios": 22847,
                "censo_n_setores": 105,
                "censo_base": "poligono_ibge_bairro",
                "censo_raio_m": None,
                "perfil_idade_sexo_bairro": {
                    "n_setores": 105,
                    "segmentos": {
                        "15-24": {"total": 7850, "homens": 3846, "mulheres": 4004,
                                  "pct_homens": 49.0, "pct_mulheres": 51.0},
                        "25-39": {"total": 18420, "homens": 8657, "mulheres": 9763,
                                  "pct_homens": 47.0, "pct_mulheres": 53.0},
                        "40-59": {"total": 12100, "homens": 5808, "mulheres": 6292,
                                  "pct_homens": 48.0, "pct_mulheres": 52.0},
                        "60+": {"total": 8200, "homens": 3690, "mulheres": 4510,
                                "pct_homens": 45.0, "pct_mulheres": 55.0},
                    },
                },
            }
        },
    )
    demo = _contexto(model)["demografia"]
    assert demo["setores_alinhados"] is True
    assert demo["n_setores_pop"] == 105
    assert demo["n_setores_piramide"] == 105
    assert demo["soma_faixas_15mais"] == "46.570"
    assert demo["residual_0_14"] == "13.595"
    html = gerar_html(model)
    assert "46.570" in html
    assert "13.595" in html
    assert "não inclui crianças" in html
