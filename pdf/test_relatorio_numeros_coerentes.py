from pdf.adapters import _map_cenario_row, _nested_cenarios_to_rows


def test_map_cenario_row_keeps_frete_giro_inad():
    row = {
        "modelo": "mid",
        "ticket_medio": 150,
        "receita_mensal": 201466.0,
        "lucro_mensal_estimado": 41606.0,
        "margem_percentual": 21,
        "payback_meses": 40,
        "investimento_total": 1_664_240.0,
        "capex_total": 1_226_244.0,
        "capex_equipamentos": 600_030.0,
        "capex_obra_adaptacao": 400_000.0,
        "capex_projeto_arquitetonico": 50_000.0,
        "capex_alvara_e_taxas": 25_874.0,
        "capex_contingencia_valor": 111_477.0,
        "capex_frete_equipamentos": 38_863.0,
        "capital_giro": 437_996.0,
        "taxa_inadimplencia": 0.0407,
        "ticket_realizado_estimado": 143.90,
        "viabilidade": "INVIAVEL",
        "alunos_projetados": 1400,
    }
    c = _map_cenario_row(row)
    assert c.capex_frete == 38863.0
    assert c.capital_giro == 437996.0
    assert c.taxa_inadimplencia == 0.0407
    assert c.ticket_realizado == 143.90


def test_nested_cenarios_copy_frete_giro_inad():
    nested = {
        "mid": {
            "ticket_medio": 150,
            "receita_mensal": 201466.0,
            "lucro_mensal_estimado": 41606.0,
            "margem_percentual": 21,
            "payback_meses": 40,
            "investimento_total": 1_664_240.0,
            "capex_total": 1_226_244.0,
            "capital_giro": 437_996.0,
            "taxa_inadimplencia": 0.0407,
            "ticket_realizado_estimado": 143.90,
            "viabilidade": "INVIAVEL",
            "alunos_projetados": 1400,
            "capex_detalhado": {
                "equipamentos": 600_030.0,
                "obra_adaptacao": 400_000.0,
                "projeto_arquitetonico": 50_000.0,
                "alvara_e_taxas": 25_874.0,
                "frete_equipamentos": 38_863.0,
                "contingencia_valor": 111_477.0,
                "total": 1_226_244.0,
            },
        }
    }
    rows = _nested_cenarios_to_rows(nested)
    assert len(rows) == 1
    assert rows[0]["capex_frete_equipamentos"] == 38863.0
    assert rows[0]["capital_giro"] == 437996.0
    mapped = _map_cenario_row(rows[0])
    assert mapped.capex_frete == 38863.0


from pdf.html_builder import gerar_html
from pdf.models import CenarioPdf, CompetidorPdf, RelatorioPdfModel
from tools.test_html_builder import _model


def _mid_capex() -> CenarioPdf:
    return CenarioPdf(
        modelo="mid",
        label="Padrão",
        ticket_medio=150,
        receita_mensal=201_466,
        lucro_mensal=41_606,
        margem_pct=21,
        payback_meses=40,
        investimento_total=1_664_240,
        capex_total=1_226_244,
        capex_obra=475_874,
        capex_equipamentos=600_030,
        capex_contingencia=111_477,
        capex_frete=38_863,
        capital_giro=437_996,
        viabilidade="INVIAVEL",
        matriculas_realista=1400,
    )


def test_capex_bars_include_frete_and_pct_of_total():
    m = _model()
    m.cenarios = [_mid_capex()]
    m.modelo_recomendado = "nenhum"
    h = gerar_html(m)
    assert "Frete equipamentos" in h
    assert "38.863" in h
    # 38863/1226244 ≈ 3% — must NOT be 0% of a 3-line-only subtotal
    assert "Composição do investimento" in h
    assert "soma das linhas = CAPEX" in h.lower() or "Soma das linhas" in h


def test_payback_note_uses_investimento_not_capex_alone():
    m = _model()
    m.cenarios = [_mid_capex()]
    h = gerar_html(m)
    assert "capital de giro" in h.lower()
    assert "1.664.240" in h or "investimento" in h.lower()
    assert "Payback (mid)" in h


def test_receita_note_mentions_inadimplencia():
    m = _model()
    c = _mid_capex()
    c.taxa_inadimplencia = 0.04
    c.ticket_realizado = 144.0
    m.cenarios = [c]
    h = gerar_html(m)
    assert "inadimplência" in h.lower()
    assert "ticket realizado" in h.lower() or "ticket efetivo" in h.lower()


def test_cno_total_equals_sum_of_displayed_rows():
    m = _model()
    m.metadata = {
        "demanda_futura": {
            "status": "ok",
            "provavel_residencial_n": 2,
            "captura_total_est": 26,
            "receita_total_mensal_est": 4828,
            "moradores_total_est": 2879.4,
            "obras": [
                {
                    "empreendimento": "A",
                    "provavel_residencial": True,
                    "unidades_est": 353,
                    "moradores_est": 938.6,
                    "captura_est": 14.2,
                    "receita_mensal_est": 2648,
                },
                {
                    "empreendimento": "B",
                    "provavel_residencial": True,
                    "unidades_est": 290,
                    "moradores_est": 772.4,
                    "captura_est": 11.8,
                    "receita_mensal_est": 2180,
                },
            ],
        }
    }
    h = gerar_html(m)
    assert h.count("939") + h.count("772") >= 1
    # footer must equal 939+772 = 1711 if both rounded with _brl
    assert "1.711" in h
    assert "2.879" not in h  # must not keep engine total when rows are shown


def test_rating_medio_states_sample_size():
    m = _model()
    m.competidores = [
        CompetidorPdf("A", 4.1, 429, "Aldeota", True, profundidade="analisado"),
        CompetidorPdf("B", 4.3, 160, "Papicu", False, profundidade="analisado"),
        CompetidorPdf("C", 5.0, 6, None, None, profundidade="mapeado"),
    ]
    m.metadata = {
        **(m.metadata or {}),
        "panorama": {"saturacao": "ALTO", "rating_medio": 4.2, "total": 7, "raio": 6},
    }
    h = gerar_html(m)
    assert "4.2" in h
    assert "2 analisados" in h.lower() or "n=2" in h.lower() or "2 concorrentes analisados" in h.lower()


def test_html_has_title_and_thead_on_finance_table():
    m = _model()
    m.cenarios = [_mid_capex()]
    h = gerar_html(m)
    assert "<title>" in h
    assert "Viabilidade" in h[h.find("<title>"):h.find("</title>") + 8]
    assert "Coco" in h or "Cocó" in h or "Fortaleza" in h
    fin = h[h.find("Viabilidade Financeira"):]
    assert "<thead>" in fin[:2500]


def test_matriz_explains_n_poligono_vs_sete():
    m = _model()
    m.total_concorrentes = 7
    m.posicionamento_estrategico = {
        **(m.posicionamento_estrategico or {}),
        "matriz_demo_saturacao": {
            "quadrante": "Oceano Azul",
            "modelo_sugerido": "premium_ou_mid_high",
            "n_poligono": 2,
            "n_per_10k": 0.87,
            "mix": {"low": 0, "mid": 0, "premium": 0},
            "acao_estrategica": "Espaço para Premium/Mid-High.",
            "carimbo": "Oceano Azul · N=2",
        },
    }
    h = gerar_html(m)
    assert "não é a contagem de 7" in h.lower() or "régua da matriz" in h.lower()
