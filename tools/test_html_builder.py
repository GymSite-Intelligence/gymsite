"""Fundação PDF WeasyPrint (HTML/CSS): gerar_html binda o dado DETERMINÍSTICO do model
(ERRC/gaps/ticket/veredito/demanda) no template — sem o LLM escrever o documento.
A conversão HTML→PDF (WeasyPrint) precisa de libs de sistema (container), testada lá."""
from pdf.html_builder import gerar_html
from pdf.models import RelatorioPdfModel


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
    assert "GYM" in h and "Eliminar" not in h
