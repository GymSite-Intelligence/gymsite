"""Task #15: contrato Wellhub-only + seção 'Oferta mapeada por concorrente' no PDF
+ brutos do A3a na união do ERRC (run 3f4e0b82: Krav Maga/S3 invisíveis)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.a9_positioning_strategist import _concorrentes_para_oferta, _gaps_reais
from pdf.html_builder import gerar_html
from pdf.models import CompetidorPdf
from pdf.test_render_campos_v3 import _modelo_com_v3


def test_brutos_entram_na_uniao_do_errc():
    state = {
        "inteligencia_competitiva": {"concorrentes_detalhados": [
            {"nome": "Academia Smart Fit", "planos_precos": [{"plano": "Fit", "inclui": ["Musculação"]}]}]},
        "concorrentes_brutos": [
            {"nome": "Centro de Krav Maga FSAKM - Ceará"},
            {"displayName": {"text": "S3 - Treinamento Personalizado"}},
        ],
    }
    nomes = [c["nome"] for c in _concorrentes_para_oferta(state)]
    assert "Centro de Krav Maga FSAKM - Ceará" in nomes
    assert "S3 - Treinamento Personalizado" in nomes
    gaps = _gaps_reais(state)
    assert "Artes marciais" not in gaps
    assert "Personal (PT)" not in gaps


def test_secao_oferta_mapeada_renderiza():
    model = _modelo_com_v3()
    model.competidores = [CompetidorPdf(
        nome="Parque Esportes", rating=4.7, num_avaliacoes=82, bairro="Cocó", tem_24h=None,
        tier_agregador={"plano": "Gold", "preco_mensal_brl": 319.99, "fonte": "wellhub"},
        oferta_modalidades=["crossfit", "area_kids", "musculacao"],
        oferta_comodidades=["Ar condicionado", "Estacionamento"],
        oferta_fontes=["website", "wellhub"],
    )]
    html = gerar_html(model)
    assert "Oferta mapeada por concorrente" in html
    assert "Crossfit" in html and "Aulas/espaço kids" in html
    assert "Ar condicionado" in html
    assert "wellhub" in html
    assert "substrato determinístico dos GAPs" in html


def test_sem_oferta_sem_secao():
    model = _modelo_com_v3()
    model.competidores = [CompetidorPdf(
        nome="Academia X", rating=4.5, num_avaliacoes=10, bairro="Cocó", tem_24h=None)]
    html = gerar_html(model)
    assert "Oferta mapeada por concorrente" not in html
