"""PDF header uses GymSite lime logo asset when present."""

import os

from pdf.html_builder import _ASSETS, _contexto
from pdf.models import RelatorioPdfModel


def test_pdf_logo_src_points_to_lime_asset():
    assert os.path.isfile(os.path.join(_ASSETS, "logo-gymsite-lockup.png"))
    model = RelatorioPdfModel(
        relatorio_id="t-logo",
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
    )
    ctx = _contexto(model)
    assert ctx.get("logo_src") == "logo-gymsite-lockup.png"


def test_pdf_html_header_has_logo_img():
    from pdf.html_builder import gerar_html
    from PIL import Image

    lockup = os.path.join(_ASSETS, "logo-gymsite-lockup.png")
    im = Image.open(lockup)
    assert im.mode == "RGBA"
    assert im.getpixel((0, 0))[3] == 0  # canto transparente (sem fundo preto)

    model = RelatorioPdfModel(
        relatorio_id="t-logo",
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
    )
    html = gerar_html(model)
    assert 'class="logo-img"' in html
    assert "logo-gymsite-lockup.png" in html
    assert 'alt="GymSite Intelligence"' in html
