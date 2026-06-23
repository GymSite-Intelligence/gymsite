"""
Smoke visual dos SELOS DE CONFIANÇA do relatório A9 PDF (ConfidenceBadge).
Gera um PDF de amostra (dados fake) pra INSPEÇÃO VISUAL. Não vai pro pipeline.
Usa `chart_scores_bar` (chart já existente na main) só pra contextualizar o render.

Uso:
    python -m tools.smoke_pdf_visuais [caminho_saida.pdf]
    # default: ./build/smoke_pdf_visuais.pdf
"""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from pdf import charts, theme
from pdf.badges import ConfidenceBadge
from pdf.models import ScoreDim
from tools.confianca_dado import NivelConfianca

_SCORES = [ScoreDim("Demográfico", 7.2), ScoreDim("Competitivo", 5.8), ScoreDim("Viabilidade", 6.5)]


def _img(png: bytes | None, w_cm: float):
    if not png:
        return Paragraph("(sem dado — gráfico omitido)", theme.build_styles()["small"])
    im = Image(BytesIO(png))
    ratio = im.imageHeight / im.imageWidth
    im.drawWidth = w_cm * cm
    im.drawHeight = w_cm * cm * ratio
    return im


def build(out: Path) -> Path:
    st = theme.build_styles()
    story = [Paragraph("Smoke — Selos de confiança + Charts Fase A/B (dados fake)", st["h1"])]

    # 1) selos (3 variantes) + legenda
    story += [Paragraph("Selos de confiança", st["h2"])]
    selos = Table(
        [[ConfidenceBadge(NivelConfianca.MEDIDO),
          ConfidenceBadge(NivelConfianca.ESTIMATIVA),
          ConfidenceBadge(NivelConfianca.PROJECAO)]],
        colWidths=[3.2 * cm] * 3,
    )
    selos.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "LEFT"),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [selos, Spacer(1, 10)]

    # 2) chart real da main (contexto de render)
    story += [Paragraph("Scores por dimensão (chart_scores_bar)", st["h2"]),
              _img(charts.chart_scores_bar(_SCORES), 12.0)]

    out.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(out), pagesize=theme.PAGE_SIZE,
                      leftMargin=theme.MARGIN_L, rightMargin=theme.MARGIN_R,
                      topMargin=theme.MARGIN_T, bottomMargin=theme.MARGIN_B).build(story)
    return out


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/smoke_pdf_visuais.pdf")
    p = build(out)
    print(f"OK: {p.resolve()} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
