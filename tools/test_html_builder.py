"""Fundação PDF WeasyPrint (HTML/CSS): gerar_html binda o dado DETERMINÍSTICO do model
(ERRC/gaps/ticket/veredito/demanda) no template — sem o LLM escrever o documento.
A conversão HTML→PDF (WeasyPrint) precisa de libs de sistema (container), testada lá."""
from pdf.html_builder import gerar_html
from pdf.models import CenarioPdf, CompetidorPdf, RelatorioPdfModel


def _model() -> RelatorioPdfModel:
    return RelatorioPdfModel(
        relatorio_id="abc12345", data_execucao="2026-06-18", cidade="Fortaleza", bairro="Coco",
        uf="CE", tipo_negocio="academia", area_m2_min=1000, area_m2_max=1500, publico_alvo="25-40",
        veredito="OCEANO_AZUL", score_bairro=8.1, score_top1=7.4,
        posicionamento_estrategico={
            "veredito_posicionamento": "OCEANO_AZUL",
            "justificativa_recomendacao": "Coco top-1% de renda; premium fecha no teto.",
            "framework_errc": {"eliminar": ["preco low-cost"], "reduzir": ["friccao"],
                               "aumentar": ["qualidade"], "criar": ["Nutricao integrada"]},
            "gaps_identificados": ["Nutricao integrada — ninguem oferece"],
            "ticket": {"ticket_recomendado": 249, "banda_min": 199, "banda_max": 299},
        },
        metadata={"demanda_futura": {"status": "ok", "provavel_residencial_n": 6,
                                     "captura_total_est": 43, "receita_total_mensal_est": 6048,
                                     "moradores_total_est": 2879}},
    )


def test_binda_secoes_do_dado_real():
    h = gerar_html(_model())
    # ERRC 2x2
    for eixo in ("Eliminar", "Reduzir", "Aumentar", "Criar"):
        assert eixo in h
    assert "Nutricao integrada" in h          # gap real (não genérico hardcoded)
    assert "R$ 249" in h and "199 a R$ 299" in h  # ticket determinístico
    assert "OCEANO_AZUL" in h                  # veredito
    assert "2.879" in h and "~43 alunos" in h  # demanda futura datada


def test_degrada_sem_a9():
    m = _model()
    m.posicionamento_estrategico = None
    m.metadata = {}
    h = gerar_html(m)               # não quebra; só header/meta
    assert "GymSite" in h and "Eliminar" not in h


def _cenario(modelo: str, label: str, ticket: float, viab: str) -> CenarioPdf:
    return CenarioPdf(
        modelo=modelo, label=label, ticket_medio=ticket,
        receita_mensal=100_000, lucro_mensal=10_000, margem_pct=10,
        payback_meses=24, investimento_total=500_000, capex_total=400_000,
        capex_obra=200_000, capex_equipamentos=150_000, capex_contingencia=50_000,
        viabilidade=viab, matriculas_realista=200,
    )


def test_indeterminado_nao_herda_ticket_cenario():
    """INDETERMINADO não pode mostrar o ticket do cenário A4 como se fosse recomendação."""
    m = _model()
    m.modelo_recomendado = "nenhum"
    m.posicionamento = 'Gap de oferta: 24h; atacar a dor "atendimento ruim".'
    m.posicionamento_estrategico = {
        "veredito_posicionamento": "INDETERMINADO",
        "recomendacao_ticket": {"ticket_recomendado": None, "confianca": "indisponivel"},
        "framework_errc": {
            "eliminar": ["Guerra de preço"], "reduzir": ["CAC alto"],
            "aumentar": ["Retenção"], "criar": ["Aulas/espaço kids"],
        },
        "gaps_identificados": ["Aulas/espaço kids"],
        "matriz_demo_saturacao": {
            "quadrante": "Oceano Azul",
            "modelo_sugerido": "premium_ou_mid_high",
        },
        "markdown": (
            "Posicionamento indeterminado: A4 sem modelo viável. "
            "Sem modelo viável identificado pelo A4, não é possível recomendar ticket."
        ),
    }
    m.cenarios = [
        _cenario("low", "Econômico", 90, "INVIAVEL"),
        _cenario("mid", "Padrão", 150, "INVIAVEL"),
        _cenario("premium", "Premium", 250, "INVIAVEL"),
    ]
    h = gerar_html(m)
    idx = h.find("Posicionamento Tarifário")
    assert idx >= 0
    card = h[idx:idx + 900]
    assert "INDETERMINADO" in card
    assert "R$ 150" not in card
    assert "Gap de oferta: 24h" not in h
    assert "sem modelo viável" in h.lower()
    assert "todos os cenários financeiros são inviáveis" in h.lower()


def test_leitura_competitiva_todos_analisados():
    m = _model()
    m.competidores = [
        CompetidorPdf(f"A{i}", 4.5, 100, "Meireles", False, profundidade="analisado")
        for i in range(14)
    ]
    h = gerar_html(m)
    assert "14 concorrentes no bairro, todos com reviews e planos analisados" in h
    assert "apenas contados" not in h


def test_leitura_competitiva_mapeados_vs_analisados():
    m = _model()
    m.competidores = [
        CompetidorPdf("A", 4.5, 100, "Meireles", False, profundidade="analisado"),
        CompetidorPdf("B", 4.0, 50, "Meireles", False, profundidade="analisado"),
        CompetidorPdf("C", 4.2, 80, "Meireles", False, profundidade="analisado"),
    ] + [
        CompetidorPdf(f"M{i}", None, None, "Meireles", None, profundidade="mapeado")
        for i in range(11)
    ]
    h = gerar_html(m)
    assert "3 com reviews e planos" in h
    assert "11 ainda sem análise completa" in h
    assert "14 concorrentes com reviews analisados" not in h


def test_capex_sem_equipamentos_no_pdf():
    """Paridade web: PDF não exibe linha Equipamentos nem frete no breakdown."""
    m = _model()
    m.cenarios = [
        _cenario("mid", "Padrão", 150, "VIAVEL"),
    ]
    h = gerar_html(m)
    assert "Equipamentos" not in h
    assert "150.000" not in h  # capex_equipamentos do _cenario não no KPI
    assert "250.000" in h  # capex_total 400k − equip 150k


def test_payback_sem_equipamentos_no_pdf():
    """Payback no PDF usa investimento sem kit (capex_sem + capital_giro)."""
    m = _model()
    m.cenarios = [
        _cenario("mid", "Padrão", 150, "VIAVEL"),
    ]
    h = gerar_html(m)
    # investimento_sem = (400k-150k) + (500k-400k) = 350k; lucro 10k → ceil = 35m
    assert "35m" in h
    assert "24m" not in h  # payback bruto A4 (com kit) não deve aparecer


def test_ticket_segmento_usa_oferta_modalidades():
    m = _model()
    m.competidores = [
        CompetidorPdf(
            "Smart Fit", 4.5, 1000, "Meireles", False,
            planos_precos=[
                {"plano": "Black", "preco_mensal": 140},
                {"plano": "Smart", "preco_mensal": 160},
                {"plano": "Fit", "preco_mensal": 180},
            ],
            oferta_modalidades=["musculacao", "spinning", "danca"],
            profundidade="analisado",
        ),
        CompetidorPdf(
            "Bodytech", 4.8, 800, "Meireles", False,
            planos_precos=[{"plano": "Black", "preco_mensal": 280}],
            oferta_modalidades=["yoga", "piscina"],
            profundidade="analisado",
        ),
    ]
    h = gerar_html(m)
    idx = h.find("Ticket por segmento")
    assert idx >= 0
    chunk = h[idx:idx + 1600]
    assert "Musculação" in chunk
