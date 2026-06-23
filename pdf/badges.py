"""
Selos de confiança do PDF (render ReportLab) — geometria de docs/A9_CONFIDENCE_BADGES_SPEC.md.

`ConfidenceBadge(nivel)` é um Flowable pill: borda+ícone+texto na cor da variante,
fundo claro da mesma matiz. O marcador difere por FORMA (preenchido/meio/vazado)
para leitura em P&B, não só por cor (spec §7).
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable

from pdf import theme
from tools.confianca_dado import ROTULO, NivelConfianca

# Geometria fixa (pt) — badge spec §2.
_H = 16.0
_PAD_H = 8.0
_RADIUS = 8.0
_DOT = 6.0          # diâmetro do marcador
_GAP = 5.0          # marcador → texto
_BORDER = 0.75
_FONT = "Helvetica-Bold"
_FONT_SIZE = 6.5
_TRACKING = 0.4
_MIN_W = 54.0

# variante → (foreground, background, forma do marcador)
_VARIANTE = {
    NivelConfianca.MEDIDO: (theme.TEAL, theme.TEAL_LIGHT, "filled"),
    NivelConfianca.ESTIMATIVA: (theme.ORANGE, theme.ORANGE_LIGHT, "half"),
    NivelConfianca.PROJECAO: (theme.SLATE, theme.CARD_BG, "outline"),
}


def _texto_largura(txt: str) -> float:
    base = stringWidth(txt, _FONT, _FONT_SIZE)
    return base + _TRACKING * max(0, len(txt) - 1)


class ConfidenceBadge(Flowable):
    """Selo pill de nível de confiança. Largura = hug do conteúdo (mín. 54pt)."""

    def __init__(self, nivel: NivelConfianca, rotulo: str | None = None):
        super().__init__()
        self.nivel = nivel if isinstance(nivel, NivelConfianca) else NivelConfianca(nivel)
        self.rotulo = (rotulo or ROTULO[self.nivel]).upper()
        self._fg, self._bg, self._marker = _VARIANTE[self.nivel]
        self.height = _H
        self.width = max(_MIN_W, _PAD_H + _DOT + _GAP + _texto_largura(self.rotulo) + _PAD_H)

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def _desenhar_texto_tracking(self, c, x, y, txt):
        for ch in txt:
            c.drawString(x, y, ch)
            x += stringWidth(ch, _FONT, _FONT_SIZE) + _TRACKING

    def _desenhar_marcador(self, c, cx, cy):
        r = _DOT / 2.0
        c.setLineWidth(0.75)
        c.setStrokeColor(self._fg)
        if self._marker == "filled":
            c.setFillColor(self._fg)
            c.circle(cx, cy, r, stroke=0, fill=1)
        elif self._marker == "half":
            # contorno + metade esquerda preenchida (wedge 90°→270°)
            c.setFillColor(self._fg)
            c.wedge(cx - r, cy - r, cx + r, cy + r, 90, 180, stroke=0, fill=1)
            c.circle(cx, cy, r, stroke=1, fill=0)
        else:  # outline
            c.circle(cx, cy, r, stroke=1, fill=0)

    def draw(self):
        c = self.canv
        # pill: fundo + borda
        c.setFillColor(self._bg)
        c.setStrokeColor(self._fg)
        c.setLineWidth(_BORDER)
        c.roundRect(0, 0, self.width, self.height, _RADIUS, stroke=1, fill=1)
        # marcador
        self._desenhar_marcador(c, _PAD_H + _DOT / 2.0, self.height / 2.0)
        # texto (baseline centralizada vertical: ~ (H - fontSize)/2 + ajuste)
        c.setFillColor(self._fg)
        c.setFont(_FONT, _FONT_SIZE)
        tx = _PAD_H + _DOT + _GAP
        ty = (self.height - _FONT_SIZE) / 2.0 + 1.2
        self._desenhar_texto_tracking(c, tx, ty, self.rotulo)


def badge_para(nivel: NivelConfianca, rotulo: str | None = None) -> ConfidenceBadge:
    """Atalho de construção."""
    return ConfidenceBadge(nivel, rotulo)
