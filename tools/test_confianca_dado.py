"""Mapa categoria→nível de confiança (selos do PDF) + smoke de render do badge."""
from io import BytesIO

from tools.confianca_dado import (
    NivelConfianca,
    agregar_nivel,
    nivel_por_categoria,
    nivel_por_tier_aluguel,
)


def test_categoria_para_nivel():
    assert nivel_por_categoria("benchmark") == NivelConfianca.ESTIMATIVA
    assert nivel_por_categoria("calibracao") == NivelConfianca.ESTIMATIVA
    assert nivel_por_categoria("aberto") == NivelConfianca.PROJECAO
    # sem param / desconhecida = dado observado direto = MEDIDO
    assert nivel_por_categoria(None) == NivelConfianca.MEDIDO
    assert nivel_por_categoria("") == NivelConfianca.MEDIDO
    assert nivel_por_categoria("qualquer") == NivelConfianca.MEDIDO
    # case-insensitive
    assert nivel_por_categoria("BENCHMARK") == NivelConfianca.ESTIMATIVA


def test_tier_aluguel():
    assert nivel_por_tier_aluguel("1") == NivelConfianca.MEDIDO
    assert nivel_por_tier_aluguel(1) == NivelConfianca.MEDIDO
    assert nivel_por_tier_aluguel("2") == NivelConfianca.ESTIMATIVA
    assert nivel_por_tier_aluguel("3") == NivelConfianca.ESTIMATIVA
    assert nivel_por_tier_aluguel(None) == NivelConfianca.PROJECAO


def test_agregacao_menor_confianca():
    # selo de métrica composta = MENOR confiança das entradas
    assert agregar_nivel(NivelConfianca.MEDIDO, NivelConfianca.ESTIMATIVA) == NivelConfianca.ESTIMATIVA
    assert agregar_nivel(
        NivelConfianca.MEDIDO, NivelConfianca.PROJECAO, NivelConfianca.ESTIMATIVA
    ) == NivelConfianca.PROJECAO
    assert agregar_nivel(NivelConfianca.MEDIDO, NivelConfianca.MEDIDO) == NivelConfianca.MEDIDO
    assert agregar_nivel() == NivelConfianca.MEDIDO
    assert agregar_nivel(None, NivelConfianca.ESTIMATIVA) == NivelConfianca.ESTIMATIVA


def test_badge_render_smoke():
    from reportlab.platypus import SimpleDocTemplate, Spacer

    from pdf.badges import ConfidenceBadge

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=(300, 200))
    story = []
    for lvl in (NivelConfianca.MEDIDO, NivelConfianca.ESTIMATIVA, NivelConfianca.PROJECAO):
        b = ConfidenceBadge(lvl)
        assert b.height == 16.0
        assert b.width >= 54.0  # mín. do spec
        story += [b, Spacer(1, 8)]
    doc.build(story)
    pdf = buf.getvalue()
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 800
