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
CHARCOAL = colors.HexColor("#0F172A")
TEAL = colors.HexColor("#0D9488")
TEAL_LIGHT = colors.HexColor("#CCFBF1")
TEAL_DARK = colors.HexColor("#115E59")
ORANGE = colors.HexColor("#E8751A")
ORANGE_LIGHT = colors.HexColor("#FDEBD8")  # bg do selo "ESTIMATIVA" (ConfidenceBadge)
SLATE = colors.HexColor("#64748B")
TEXT = colors.HexColor("#1E293B")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#E2E8F0")
ROW_ALT = colors.HexColor("#F8FAFC")
CARD_BG = colors.HexColor("#F1F5F9")
SUCCESS = colors.HexColor("#16A34A")
DANGER = colors.HexColor("#DC2626")
WARNING = colors.HexColor("#CA8A04")

# Cores de marca (verde-limao do logo + azul-petroleo), aproximacoes HEX do site
LIME = colors.HexColor("#A3E635")  # verde-limao primario da marca (acento/realce)
LIME_GLOW = colors.HexColor("#BEF264")  # variacao clara do verde-limao para realces
PETROLEUM = colors.HexColor("#0E5C66")  # azul-petroleo (alinhado a NAVY/TEAL)
PETROLEUM_DEEP = colors.HexColor("#08323A")  # azul-petroleo profundo (capa/dividers)

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
        # --- estilos layout BALA ---
        "bala_cover_title": ParagraphStyle(
            "BalaCoverTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=32,
            textColor=colors.white,
            leading=36,
            spaceAfter=4,
        ),
        "bala_cover_sub": ParagraphStyle(
            "BalaCoverSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=13,
            textColor=colors.HexColor("#CBD5E1"),
            leading=16,
            spaceAfter=2,
        ),
        "bala_kpi_label": ParagraphStyle(
            "BalaKpiLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=SLATE,
            leading=10,
            alignment=TA_CENTER,
        ),
        "bala_kpi_value": ParagraphStyle(
            "BalaKpiValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=TEAL_DARK,
            leading=20,
            alignment=TA_CENTER,
        ),
        "bala_section": ParagraphStyle(
            "BalaSection",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=CHARCOAL,
            spaceBefore=18,
            spaceAfter=6,
            borderWidth=0,
            borderColor=TEAL,
            borderPadding=5,
            leftIndent=0,
        ),
        "bala_body": ParagraphStyle(
            "BalaBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=TEXT,
            leading=13,
            spaceAfter=6,
        ),
        "bala_small": ParagraphStyle(
            "BalaSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            leading=10,
        ),
        "bala_badge": ParagraphStyle(
            "BalaBadge",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.white,
            alignment=TA_CENTER,
            leading=12,
        ),
    }


def veredito_color(veredito: str | None) -> colors.Color:
    if not veredito:
        return SLATE
    return VEREDITO_COLORS.get(veredito.upper().strip(), SLATE)
