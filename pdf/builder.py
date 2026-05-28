"""
Montagem do PDF com ReportLab (layout classic / executive / data_room).
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from pdf.charts import chart_capex_stacked, chart_lucro_cenarios, chart_scores_bar
from pdf.models import LayoutId, RelatorioPdfModel
from pdf.theme import (
    BORDER,
    CONTENT_W,
    MARGIN_B,
    MARGIN_L,
    MARGIN_R,
    MARGIN_T,
    NAVY,
    PAGE_SIZE,
    ROW_ALT,
    TEAL,
    TEAL_LIGHT,
    build_styles,
    veredito_color,
)


def _brl(v: float | None) -> str:
    if v is None:
        return "—"
    return f"R$ {v:,.0f}".replace(",", ".")


def _pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}%"


def _score(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}"


def _para(text: str, style: str, styles: dict) -> Paragraph:
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
    return Paragraph(safe, styles[style])


def _section_title(title: str, styles: dict) -> list:
    return [Paragraph(title, styles["h1"]), Spacer(1, 4)]


def _table(data: list[list], col_widths: list[float] | None = None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ],
        ),
    )
    return t


def _header_footer(canvas, doc, model: RelatorioPdfModel) -> None:
    canvas.saveState()
    w, h = PAGE_SIZE
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 1.2 * cm, w, 1.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN_L, h - 0.85 * cm, "GymSite Intelligence")
    canvas.setFont("Helvetica", 8)
    loc = f"{model.bairro} · {model.cidade}"
    if model.uf:
        loc += f" / {model.uf}"
    canvas.drawRightString(w - MARGIN_R, h - 0.85 * cm, loc[:60])
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN_L, 1.4 * cm, w - MARGIN_R, 1.4 * cm)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        MARGIN_L,
        0.9 * cm,
        f"Relatório {model.relatorio_id[:8]}… · gerado {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )
    canvas.drawRightString(w - MARGIN_R, 0.9 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _cover_block(model: RelatorioPdfModel, styles: dict) -> list:
    ver = model.veredito or "—"
    vc = veredito_color(model.veredito)
    meta = (
        f"Área {model.area_m2_min}–{model.area_m2_max} m² · "
        f"{model.tipo_negocio.replace('_', ' ')} · "
        f"público {model.publico_alvo or '—'}"
    )
    cover_inner = [
        [Paragraph("GymSite Intelligence", styles["cover_sub"])],
        [
            Paragraph(
                f"<b>{model.bairro}</b> · {model.cidade}",
                styles["cover_title"],
            ),
        ],
        [
            Paragraph(
                f"Veredito: <font color='{vc.hexval()}'><b>{ver}</b></font>",
                styles["cover_sub"],
            ),
        ],
        [Paragraph(meta, styles["cover_sub"])],
        [
            Paragraph(
                f"Data da análise: {model.data_execucao or '—'} · "
                f"Score bairro {_score(model.score_bairro)} · "
                f"Top 1 {_score(model.score_top1)}",
                styles["cover_sub"],
            ),
        ],
    ]
    cover_tbl = Table(cover_inner, colWidths=[CONTENT_W])
    cover_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ],
        ),
    )
    return [cover_tbl, Spacer(1, 16)]


def _scores_section(model: RelatorioPdfModel, styles: dict) -> list:
    flow = _section_title("1. Scores e veredito", styles)
    kpi = [
        ["Score bairro", "Score Top 1", "Saturação", "Concorrentes analisados"],
        [
            _score(model.score_bairro),
            _score(model.score_top1),
            model.nivel_saturacao or "—",
            str(model.total_concorrentes or "—"),
        ],
    ]
    flow.append(_table(kpi, [CONTENT_W / 4] * 4))
    flow.append(Spacer(1, 8))
    png = chart_scores_bar(model.scores)
    if png:
        flow.append(Image(io.BytesIO(png), width=CONTENT_W * 0.85, height=4.2 * cm))
    return flow


def _resumo_section(model: RelatorioPdfModel, styles: dict) -> list:
    if not model.resumo_executivo:
        return []
    flow = _section_title("2. Resumo executivo", styles)
    flow.append(_para(model.resumo_executivo[:4000], "body", styles))
    return flow


def _market_section(model: RelatorioPdfModel, styles: dict) -> list:
    if not model.market:
        return []
    m = model.market
    flow = _section_title("3. Contexto de mercado", styles)
    rows = [
        ["Indicador", "Valor"],
        ["Ticket mercado", m.ticket_mercado or "—"],
        ["Aluguel médio/m²", m.aluguel_m2 or "—"],
        ["Renda bairro", m.renda or "—"],
        ["Tendência", m.tendencia or "—"],
    ]
    if m.parque_ativo is not None:
        rows.append(["Parque ativo (CNPJ)", str(m.parque_ativo)])
    if m.novos_cnpj_90d is not None:
        rows.append(["Novos CNPJ fitness (90d)", str(m.novos_cnpj_90d)])
    flow.append(_table(rows, [CONTENT_W * 0.45, CONTENT_W * 0.55]))
    if m.redes:
        flow.append(Spacer(1, 6))
        flow.append(_para("Redes mapeadas: " + ", ".join(m.redes[:8]), "small", styles))
    for ins in m.insights[:3]:
        flow.append(_para(f"• {ins}", "body", styles))
    return flow


def _candidatos_section(model: RelatorioPdfModel, styles: dict) -> list:
    if not model.candidatos:
        return []
    flow = _section_title("4. Top candidatos (imóveis)", styles)
    data = [["#", "Nome", "Área m²", "GeoScout", "Ancoragem", "Endereço"]]
    for c in model.candidatos:
        data.append(
            [
                str(c.posicao),
                c.nome[:40],
                str(int(c.area_m2)) if c.area_m2 else "—",
                _score(c.score_geoscout),
                _score(c.score_ancoragem),
                c.endereco[:55],
            ],
        )
    flow.append(
        _table(
            data,
            [
                0.8 * cm,
                4.2 * cm,
                1.5 * cm,
                1.5 * cm,
                1.5 * cm,
                CONTENT_W - 9.5 * cm,
            ],
        ),
    )
    for c in model.candidatos:
        if c.motivo:
            flow.append(
                _para(f"<b>Cand. {c.posicao}:</b> {c.motivo[:400]}", "small", styles),
            )
    return flow


def _finance_section(model: RelatorioPdfModel, styles: dict, *, charts: bool) -> list:
    if not model.cenarios:
        return []
    flow = _section_title("5. Viabilidade financeira (3 cenários)", styles)
    if model.modelo_recomendado:
        flow.append(
            _para(f"Modelo recomendado: <b>{model.modelo_recomendado}</b>", "body", styles),
        )
    if model.aluguel_mensal is not None:
        extra = ""
        if model.aluguel_mediana_m2 is not None:
            extra = f" · mediana {_brl(model.aluguel_mediana_m2)}/m²"
        flow.append(_para(f"Aluguel estimado: <b>{_brl(model.aluguel_mensal)}</b>{extra}", "body", styles))

    data = [
        [
            "Modelo",
            "Ticket",
            "Receita/mês",
            "Lucro/mês",
            "Margem",
            "Payback",
            "Investimento",
            "Viabilidade",
        ],
    ]
    for c in model.cenarios:
        pb = str(c.payback_meses) if c.payback_meses and c.payback_meses < 900 else "—"
        data.append(
            [
                c.label,
                _brl(c.ticket_medio),
                _brl(c.receita_mensal),
                _brl(c.lucro_mensal),
                _pct(c.margem_pct),
                f"{pb} m",
                _brl(c.investimento_total or c.capex_total),
                c.viabilidade or "—",
            ],
        )
    cw = CONTENT_W / 8
    flow.append(_table(data, [cw] * 8))

    if charts:
        flow.append(Spacer(1, 8))
        png1 = chart_capex_stacked(model.cenarios)
        if png1:
            flow.append(Image(io.BytesIO(png1), width=CONTENT_W, height=5.5 * cm))
        flow.append(Spacer(1, 6))
        png2 = chart_lucro_cenarios(model.cenarios)
        if png2:
            flow.append(Image(io.BytesIO(png2), width=CONTENT_W * 0.9, height=5 * cm))
    return flow


def _competition_section(model: RelatorioPdfModel, styles: dict) -> list:
    if not model.competidores:
        return []
    flow = _section_title("6. Inteligência competitiva", styles)
    if model.total_raio is not None:
        flow.append(
            _para(
                f"Academias no raio (agregado): <b>{model.total_raio}</b> · "
                f"amostra analisada: <b>{model.total_concorrentes or len(model.competidores)}</b>",
                "body",
                styles,
            ),
        )
    data = [["Concorrente", "Rating", "Avaliações", "Bairro", "24h"]]
    for c in model.competidores:
        data.append(
            [
                c.nome[:42],
                _score(c.rating),
                str(c.num_avaliacoes or "—"),
                (c.bairro or "—")[:20],
                "Sim" if c.tem_24h else ("Não" if c.tem_24h is False else "—"),
            ],
        )
    flow.append(
        _table(
            data,
            [5.5 * cm, 1.5 * cm, 2 * cm, 3 * cm, 1.2 * cm],
        ),
    )
    return flow


def _extras_section(model: RelatorioPdfModel, styles: dict) -> list:
    flow: list = []
    if model.posicionamento:
        flow.extend(_section_title("7. Posicionamento recomendado", styles))
        flow.append(_para(model.posicionamento[:3500], "body", styles))

    if model.bairros_alternativos:
        flow.extend(_section_title("8. Bairros alternativos", styles))
        data = [["Bairro", "Prioridade", "Concorrentes", "Motivo"]]
        for b in model.bairros_alternativos[:6]:
            data.append(
                [
                    b.bairro[:25],
                    b.prioridade or "—",
                    str(b.concorrentes) if b.concorrentes is not None else "—",
                    b.motivo[:80],
                ],
            )
        flow.append(_table(data, [3 * cm, 2 * cm, 2 * cm, CONTENT_W - 7 * cm]))

    if model.alertas:
        flow.extend(_section_title("9. Alertas e ressalvas", styles))
        box = Table(
            [[_para("<br/>".join(f"• {a}" for a in model.alertas[:12]), "body", styles)]],
            colWidths=[CONTENT_W],
        )
        box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FECACA")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ],
            ),
        )
        flow.append(box)

    if model.entrantes_cnpj_total is not None:
        flow.append(Spacer(1, 8))
        flow.append(
            _para(
                f"Novos entrantes CNPJ (90 dias) na cidade: <b>{model.entrantes_cnpj_total}</b>",
                "body",
                styles,
            ),
        )
    return flow


def _build_classic(model: RelatorioPdfModel, styles: dict) -> list:
    story: list = []
    story.extend(_cover_block(model, styles))
    story.extend(_scores_section(model, styles))
    story.extend(_resumo_section(model, styles))
    story.extend(_market_section(model, styles))
    story.append(PageBreak())
    story.extend(_candidatos_section(model, styles))
    story.extend(_finance_section(model, styles, charts=True))
    story.append(PageBreak())
    story.extend(_competition_section(model, styles))
    story.extend(_extras_section(model, styles))
    story.append(Spacer(1, 12))
    story.append(
        _para(
            "Documento gerado automaticamente pelo pipeline GymSite Intelligence (A0–A6). "
            "Valores são estimativas — validar com visita técnica e due diligence.",
            "small",
            styles,
        ),
    )
    return story


def _build_executive(model: RelatorioPdfModel, styles: dict) -> list:
    story: list = []
    story.extend(_cover_block(model, styles))
    story.extend(_scores_section(model, styles))
    story.extend(_resumo_section(model, styles))
    mid = next((c for c in model.cenarios if c.modelo == "mid"), None)
    if mid:
        story.extend(_section_title("Financeiro — cenário padrão (mid)", styles))
        story.append(
            _para(
                f"Lucro mensal {_brl(mid.lucro_mensal)} · Payback "
                f"{mid.payback_meses or '—'} meses · Investimento "
                f"{_brl(mid.investimento_total)} · {mid.viabilidade or ''}",
                "body",
                styles,
            ),
        )
        png = chart_lucro_cenarios(model.cenarios)
        if png:
            story.append(Image(io.BytesIO(png), width=CONTENT_W * 0.85, height=4.5 * cm))
    story.extend(_candidatos_section(model, styles))
    if model.alertas:
        story.extend(_extras_section(model, styles))
    return story


def _build_data_room(model: RelatorioPdfModel, styles: dict) -> list:
    story: list = []
    story.extend(_cover_block(model, styles))
    story.extend(_finance_section(model, styles, charts=True))
    story.extend(_competition_section(model, styles))
    story.extend(_candidatos_section(model, styles))
    story.extend(_market_section(model, styles))
    return story


def generate_relatorio_pdf(
    model: RelatorioPdfModel,
    *,
    layout: LayoutId | str = LayoutId.CLASSIC,
) -> bytes:
    """Gera bytes do PDF para o relatório."""
    layout_id = LayoutId(layout) if isinstance(layout, str) else layout
    styles = build_styles()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T + 0.6 * cm,
        bottomMargin=MARGIN_B + 0.4 * cm,
        title=f"GymSite — {model.bairro} {model.cidade}",
        author="GymSite Intelligence",
    )

    if layout_id == LayoutId.EXECUTIVE:
        story = _build_executive(model, styles)
    elif layout_id == LayoutId.DATA_ROOM:
        story = _build_data_room(model, styles)
    else:
        story = _build_classic(model, styles)

    doc.build(
        story,
        onFirstPage=lambda c, d: _header_footer(c, d, model),
        onLaterPages=lambda c, d: _header_footer(c, d, model),
    )
    return buf.getvalue()
