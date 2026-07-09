"""Run b7199c7c: (a) coluna Inclui cortada no meio da palavra ('...e a outras opções
de'); (b) tier Wellhub listado como mensalidade de balcão na tabela de planos.
Valida truncamento por palavra e a marcação [agregador]."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf.html_builder import gerar_html
from pdf.models import CompetidorPdf
from pdf.test_render_campos_v3 import _modelo_com_v3


def _modelo_com_planos():
    model = _modelo_com_v3()
    model.competidores = [
        CompetidorPdf(
            nome="Academia VS Club - cocó", rating=4.3, num_avaliacoes=94,
            bairro="Cocó", tem_24h=None,
            planos_precos=[{"plano": "Plano Trimestral Musculação", "preco_mensal": "R$ 75,00",
                            "fidelidade": "3 meses",
                            "inclui": ["Musculação", "Aulas Coletivas"]}],
        ),
        CompetidorPdf(
            nome="Parque Esportes", rating=4.7, num_avaliacoes=82,
            bairro="Cocó", tem_24h=None,
            planos_precos=[{"plano": "Gold (Wellhub)", "preco_mensal": "R$ 319,99",
                            # >80 chars pra exercer o corte por palavra (o caso real do run b7199c7c)
                            "inclui": ["Acesso à Parque Esportes e a outras opções de bem-estar na rede credenciada Wellhub em todo o Brasil"]}],
        ),
    ]
    return model


def test_agregador_marcado_e_balcao_limpo():
    html = gerar_html(_modelo_com_planos())
    assert "[agregador]" in html                      # tier Wellhub rotulado
    assert "não mensalidade de balcão" in html        # nota explica
    assert "Plano Trimestral Musculação" in html      # balcão sem marcação


def test_inclui_corta_na_palavra():
    html = gerar_html(_modelo_com_planos())
    assert "opções de," not in html
    assert "e a outras opções de<" not in html        # corte cego antigo (46 chars)
    assert "…" in html                                # reticências do corte por palavra


def test_texto_curto_nao_ganha_reticencias():
    model = _modelo_com_v3()
    model.competidores = [CompetidorPdf(
        nome="X", rating=4.0, num_avaliacoes=5, bairro="Cocó", tem_24h=None,
        planos_precos=[{"plano": "Basic", "preco_mensal": "R$ 99", "inclui": ["Musculação"]}])]
    html = gerar_html(model)
    assert "Musculação…" not in html
