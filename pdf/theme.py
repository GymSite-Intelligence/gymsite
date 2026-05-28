"""Identidade visual GymSite / Vectra para PDFs ReportLab."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm

PAGE_SIZE = A4
MARGIN_L = 2.0 * cm
MARGIN_R = 2.0 * cm
MARGIN_T = 2.2 * cm
MARGIN_B = 2.0 * cm
CONTENT_W = PAGE_SIZE[0] - MARGIN_L - MARGIN_R

NAVY = colors.HexColor("#1B2A4A")
TEAL = colors.HexColor("#0D9488")
TEAL_LIGHT = colors.HexColor("#CCFBF1")
ORANGE = colors.HexColor("#E8751A")
SLATE = colors.HexColor("#64748B")
TEXT = colors.HexColor("#1E293B")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#E2E8F0")
ROW_ALT = colors.HexColor("#F8FAFC")

VEREDITO_COLORS = {
    "APROVADO": colors.HexColor("#16A34A"),
    "APROVADO COM RESSALVAS": colors.HexColor("#CA8A04"),
    "INVESTIGAR MAIS": colors.HexColor("#EA580C"),
    "REPROVADO": colors.HexColor("#DC2626"),
}

MODELO_LABEL = {"low": "Econômico", "mid": "Padrão ★", "premium": "Premium"}


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.white,
            leading=26,
            spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            textColor=colors.HexColor("#CBD5E1"),
            leading=14,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=TEAL,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT,
            leading=12,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            leading=10,
        ),
        "mono": ParagraphStyle(
            "Mono",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8,
            textColor=TEXT,
            leading=10,
        ),
        "table_header": ParagraphStyle(
            "TH",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "TD",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=TEXT,
            leading=10,
        ),
        "veredito": ParagraphStyle(
            "Veredito",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
    }


def veredito_color(veredito: str | None) -> colors.Color:
    if not veredito:
        return SLATE
    return VEREDITO_COLORS.get(veredito.upper().strip(), SLATE)
