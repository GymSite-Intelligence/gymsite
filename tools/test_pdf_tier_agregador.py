"""Task #13 (fase 2 agregadores): tier/rating do agregador chegam à tabela de
Inteligência Competitiva do PDF, com a nota 'não é mensalidade de balcão'."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf.html_builder import gerar_html
from pdf.models import CompetidorPdf
from pdf.test_render_campos_v3 import _modelo_com_v3


def _ct_greenlife():
    return CompetidorPdf(
        nome="CT Greenlife", rating=3.9, num_avaliacoes=64, bairro="Cocó", tem_24h=True,
        tier_agregador={"plano": "Gold", "preco_mensal_brl": 319.99, "fonte": "wellhub"},
        rating_agregador={"nota": 4.86, "avaliacoes": 1843, "fonte": "wellhub"},
    )


def test_tier_e_rating_agregador_renderizam():
    model = _modelo_com_v3()
    model.competidores = [_ct_greenlife()]
    html = gerar_html(model)
    assert "Tier agregador" in html
    assert "Gold" in html and "319,99" in html
    assert "4.86" in html and "wellhub" in html
    assert "não é mensalidade de balcão" in html


def test_sem_agregador_sem_coluna():
    model = _modelo_com_v3()
    model.competidores = [CompetidorPdf(
        nome="Academia X", rating=4.5, num_avaliacoes=10, bairro="Cocó", tem_24h=None)]
    html = gerar_html(model)
    assert "Tier agregador" not in html
    assert "não é mensalidade de balcão" not in html
