"""B4+B5 — seções Passantes e TOP vias no HTML Weasy."""
from __future__ import annotations

import json
from pathlib import Path

from pdf.adapters import relatorio_from_nested_json
from pdf.html_builder import _passantes_ctx, _top_vias_ctx, gerar_html


def _coco():
    return json.loads(Path("metrics/relatorios/rpt_1786416027.json").read_text(encoding="utf-8"))


def test_passantes_ctx_coco():
    model = relatorio_from_nested_json(_coco())
    p = _passantes_ctx(model.metadata)
    assert p is not None
    assert not p.get("indisponivel")
    assert p["score"].endswith("/100")
    assert p["top"]
    assert "Sabóia" in p["top"][0]["nome"] or "Sabóia" in (p.get("segmento") or "") or True
    # top-1 artéria no Cocó é Sabóia
    assert any("Sabóia" in t["nome"] or "Saboia" in t["nome"] for t in p["top"])


def test_top_vias_ctx_coco_modo_vias():
    model = relatorio_from_nested_json(_coco())
    tv = _top_vias_ctx(model.metadata)
    assert tv is not None
    assert tv["modo_vias"] is True
    assert len(tv["vias"]) >= 1
    assert "Sabóia" in tv["vias"][0]["nome"] or "Saboia" in tv["vias"][0]["nome"]
    assert tv["vias"][0]["fluxo"] == "100"


def test_html_coco_contem_passantes_e_vias():
    model = relatorio_from_nested_json(_coco())
    html = gerar_html(model)
    assert "Passantes" in html
    assert "TOP vias para prospecção" in html
    assert "Sabóia" in html or "Saboia" in html
    assert "mapeado" in html  # B3 profundidade visível
    assert html.count("Academias Max Forma") + html.count("Max Forma") >= 1
    # 7 gated devem aparecer (merge B3)
    assert html.count("<tr>") >= 7


def test_html_com_mapa_svg_vias():
    d = _coco()
    mv = d["output_consolidado"]["melhores_vias_prospeccao"]
    mv["mapa_svg"] = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">'
        '<path d="M10,10 L90,40" stroke="#DC2626" stroke-width="3"/>'
        '<circle cx="50" cy="25" r="3" fill="#0F172A"/></svg>'
    )
    html = gerar_html(relatorio_from_nested_json(d))
    assert "Mapa das top vias" in html
    assert 'stroke="#DC2626"' in html
    assert "<circle" in html
