"""
Montagem do PDF com ReportLab (layout classic / executive / data_room).
"""
from __future__ import annotations

import io
import os
import hashlib
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

# pyrefly: ignore [untyped-import]
from reportlab.lib import colors
# pyrefly: ignore [untyped-import]
from reportlab.lib.units import cm
# pyrefly: ignore [untyped-import]
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
from tools.maps_street_view import build_street_view_google_url
from tools.telemetry import span
from pdf.theme import (
    BORDER,
    CARD_BG,
    CHARCOAL,
    CONTENT_W,
    LIME,
    MARGIN_B,
    MARGIN_L,
    MARGIN_R,
    MARGIN_T,
    NAVY,
    PAGE_SIZE,
    PETROLEUM,
    PETROLEUM_DEEP,
    ROW_ALT,
    SLATE,
    TEAL,
    TEAL_DARK,
    TEAL_LIGHT,
    build_styles,
    veredito_color,
)


_LOGO_DIMS = (760, 424)  # w,h do asset otimizado (logo-gymsite.png), p/ manter o aspecto


def _logo_flowable(width_cm: float = 6.0):
    """Logo GymSite Intelligence centralizado p/ capa (banda branca, aspecto preservado).
    Usa o resolver defensivo _logo_path(); None se asset ausente."""
    try:
        path = _logo_path()
        if not path:
            return None
        w = width_cm * cm
        h = w * (_LOGO_DIMS[1] / _LOGO_DIMS[0])
        img = Image(path, width=w, height=h)
        img.hAlign = "CENTER"
        return img
    except Exception:
        return None


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


import re as _re_para

# Tags que o ReportLab Paragraph entende e que QUEREMOS preservar (negrito/quebra/cor).
_TAGS_OK = _re_para.compile(r"</?(?:b|i|br|font)(?:\s[^>]*)?/?>", _re_para.IGNORECASE)
# Emoji/símbolos sem glifo na Helvetica → viravam "■■". Remove (mantém ★ · — ° º ª).
_EMOJI = _re_para.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF\U0000FE00-\U0000FE0F\U00002190-\U000021FF]"
)


def _strip_emoji(s: str) -> str:
    return _EMOJI.sub("", s).strip()


def _para(text: str, style: str, styles: dict) -> Paragraph:
    """Escapa o texto MAS preserva as tags de marcação intencionais (<b>/<br/>/<font>) —
    antes o escape global virava '<b>' literal no PDF. Converte **negrito** markdown."""
    text = _strip_emoji(text or "")

    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    partes: list[str] = []
    fim = 0
    for m in _TAGS_OK.finditer(text):
        partes.append(_esc(text[fim:m.start()]))
        partes.append(m.group(0))  # tag permitida, mantém crua
        fim = m.end()
    partes.append(_esc(text[fim:]))
    safe = "".join(partes).replace("\n", "<br/>")
    safe = _re_para.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)  # **x** → negrito
    return Paragraph(safe, styles[style])


def _section_title(title: str, styles: dict) -> list:
    return [Paragraph(title, styles["h1"]), Spacer(1, 4)]


def _section_title_bala(title: str, styles: dict) -> list:
    """Título de seção com linha de acento teal."""
    return [
        Paragraph(title, styles["bala_section"]),
        Table(
            [[""]],
            colWidths=[CONTENT_W],
            rowHeights=[2],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), TEAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]),
        ),
        Spacer(1, 8),
    ]


def _table_bala(data: list[list], col_widths: list[float] | None = None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, TEAL_DARK),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ],
        ),
    )
    return t


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
    # Faixa fina de acento verde-limao sob a barra de topo (marca).
    canvas.setFillColor(LIME)
    canvas.rect(0, h - 1.25 * cm, w, 0.05 * cm, fill=1, stroke=0)
    # Cabeçalho: só o wordmark em branco sobre o navy (o logo cheio fica na capa). O logo
    # tem fundo branco e ficava como caixinha branca distorcida no navy — removido.
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
        f"Relatório {model.relatorio_id} · gerado {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )
    canvas.drawRightString(w - MARGIN_R, 0.9 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _logo_path() -> str | None:
    """Resolve o caminho do logo da marca de forma defensiva.

    Procura, nesta ordem: variavel de ambiente GYMSITE_PDF_LOGO e alguns
    caminhos convencionais do repo. Retorna None se o arquivo nao existir,
    para que a geracao do PDF nunca quebre por falta do asset.
    """
    candidatos = [
        os.environ.get("GYMSITE_PDF_LOGO"),
        str(Path(__file__).resolve().parent / "assets" / "logo-gymsite.png"),
        str(
            Path(__file__).resolve().parent.parent
            / "frontend" / "src" / "assets" / "logo-gymsite.png"
        ),
    ]
    for caminho in candidatos:
        if caminho and os.path.isfile(caminho):
            return caminho
    return None


def _heatmap_path() -> str | None:
    """Resolve o caminho do heatmap do Brasil de forma defensiva.

    Procura GYMSITE_PDF_HEATMAP e caminhos convencionais do repo; retorna
    None se nao existir, para nao quebrar a geracao do PDF.
    """
    candidatos = [
        os.environ.get("GYMSITE_PDF_HEATMAP"),
        str(Path(__file__).resolve().parent / "assets" / "brazil-heatmap.jpg"),
        str(
            Path(__file__).resolve().parent.parent
            / "frontend" / "src" / "assets" / "brazil-heatmap.jpg"
        ),
    ]
    for caminho in candidatos:
        if caminho and os.path.isfile(caminho):
            return caminho
    return None



def _street_view_path(lat: float | None, lng: float | None) -> str | None:
    """Baixa (1x, com cache em disco) a foto Street View do ponto e retorna o caminho.

    Reaproveita o builder de URL do servidor (chave SERVER, nunca exposta ao cliente).
    Defensivo: retorna None em qualquer falha (sem cobertura, rede, billing), para
    que a geracao do PDF nunca quebre por causa da imagem (padrao _logo_path/_heatmap_path).
    """
    if lat is None or lng is None:
        return None
    try:
        cache_dir = Path(tempfile.gettempdir()) / "gymsite_streetview"
        cache_dir.mkdir(parents=True, exist_ok=True)
        chave = hashlib.md5(f"{lat:.6f},{lng:.6f}".encode("utf-8")).hexdigest()
        destino = cache_dir / f"sv_{chave}.jpg"
        if destino.is_file() and destino.stat().st_size > 0:
            return str(destino)
        url = build_street_view_google_url(float(lat), float(lng), width=640, height=400)
        if not url:
            return None
        req = urllib.request.Request(url, headers={"User-Agent": "gymsite-pdf"})
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310 (URL do Google)
            if getattr(resp, "status", 200) != 200:
                return None
            dados = resp.read()
        # Google devolve um placeholder cinza minusculo quando nao ha cobertura.
        if not dados or len(dados) < 3000:
            return None
        destino.write_bytes(dados)
        return str(destino)
    except Exception:
        return None

def _cover_block(model: RelatorioPdfModel, styles: dict) -> list:
    ver = model.veredito or "—"
    vc = veredito_color(model.veredito)
    meta = (
        f"Área {model.area_m2_min}–{model.area_m2_max} m² · "
        f"{model.tipo_negocio.replace('_', ' ')} · "
        f"público {model.publico_alvo or '—'}"
    )

    # Logo vai ACIMA do bloco navy (banda branca, aspecto correto) — ver _cover_block
    # return. Dentro do navy a marca viraria caixa branca / distorcida (logo é wide).
    cover_inner = [
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
                # Fundo escuro grafite/petroleo, espelhando o split do logo.
                ("BACKGROUND", (0, 0), (-1, -1), CHARCOAL),
                ("BACKGROUND", (0, 0), (-1, 0), PETROLEUM_DEEP),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Faixa de acento verde-limao logo abaixo do topo da marca.
                ("LINEBELOW", (0, 0), (-1, 0), 3, LIME),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, 0), 18),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 14),
                ("TOPPADDING", (0, 1), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ],
        ),
    )
    logo = _logo_flowable(6.2)
    out: list = []
    if logo is not None:
        out += [logo, Spacer(1, 10)]
    out += [cover_tbl, Spacer(1, 16)]
    return out


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
    # Imagem de contexto geografico (heatmap do Brasil), se o asset existir.
    heatmap = _heatmap_path()
    if heatmap:
        try:
            img = Image(heatmap, width=CONTENT_W * 0.5, height=3.0 * cm)
            img.hAlign = "CENTER"
            flow.append(img)
            cap = _para("Densidade do mercado fitness no Brasil (referência nacional)", "small", styles)
            cap.hAlign = "CENTER"
            flow.append(cap)
            flow.append(Spacer(1, 6))
        except Exception:
            pass
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
    data: list[list[str | Paragraph]] = [["#", "Nome", "Tipo", "m²", "Geo", "Ancor.", "Endereço"]]
    for c in model.candidatos:
        data.append(
            [
                str(c.posicao),
                _para(c.nome[:60], "small", styles),          # Paragraph → quebra dentro da coluna
                _para((c.tipo_imovel_label or "—")[:24], "small", styles),
                str(int(c.area_m2)) if c.area_m2 else "—",
                _score(c.score_geoscout),
                _score(c.score_ancoragem),
                _para(c.endereco[:90], "small", styles),       # quebra, não corta na borda
            ],
        )
    flow.append(
        _table(
            data,
            [0.7 * cm, 3.4 * cm, 1.9 * cm, 1.1 * cm, 1.0 * cm, 1.2 * cm, CONTENT_W - 9.3 * cm],
        ),
    )
    # R1 — Street View (evidencia visual): foto de rua dos top-N candidatos.
    # Limite de N para conter custo/latencia; cache em disco reutiliza chamadas.
    _SV_TOP_N = 3
    _sv_render = []
    for c in model.candidatos[:_SV_TOP_N]:
        _sv_img = _street_view_path(getattr(c, "lat", None), getattr(c, "lng", None))
        if _sv_img:
            _sv_render.append((c, _sv_img))
    if _sv_render:
        flow.extend(_section_title("Vista da rua (Street View)", styles))
        for c, _sv_img in _sv_render:
            try:
                flow.append(Image(_sv_img, width=8 * cm, height=5 * cm))
            except Exception:
                continue
            flow.append(
                _para(
                    f"<b>Cand. {c.posicao}:</b> {c.endereco[:120]}",
                    "small",
                    styles,
                ),
            )
            flow.append(Spacer(1, 0.3 * cm))
    for c in model.candidatos:
        if c.motivo:
            flow.append(
                _para(f"<b>Cand. {c.posicao}:</b> {c.motivo[:400]}", "small", styles),
            )
        if c.cartorio:
            cart = c.cartorio
            cns = cart.get("cns") or "—"
            nome = cart.get("nome") or "—"
            tel = cart.get("telefone") or "—"
            end = cart.get("endereco") or "—"
            flow.append(
                _para(
                    f"<b>Cartório Competente (Cand. {c.posicao}):</b> {nome} (CNS: {cns}) · Tel: {tel} · End: {end}",
                    "small",
                    styles,
                ),
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


def _posicionamento_veredito_color(veredito: str | None):
    if not veredito:
        return SLATE
    key = veredito.upper().strip()
    if key == "OCEANO_AZUL":
        return TEAL
    if key == "TRANSICAO":
        return colors.HexColor("#D97706")
    if key == "VERMELHO":
        return colors.HexColor("#DC2626")
    return SLATE


def _posicionamento_estrategico_flow(
    pos: dict | None,
    styles: dict,
    *,
    section_fn,
    table_fn,
    body_style: str,
) -> list:
    """Seção A9: veredito ERRC, GAPs e ticket recomendado."""
    if not pos or not isinstance(pos, dict):
        return []
    flow: list = []
    veredito = str(pos.get("veredito_posicionamento") or "—")
    justificativa = str(pos.get("justificativa_veredito") or "")
    flow.extend(section_fn("7b. Posicionamento estratégico (ERRC)", styles))
    badge = Table(
        [[Paragraph(f"<b>Veredito:</b> {veredito}", styles.get("h2", styles[body_style]))]],
        colWidths=[CONTENT_W],
    )
    badge.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _posicionamento_veredito_color(veredito)),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]),
    )
    flow.append(badge)
    flow.append(Spacer(1, 6))
    if justificativa:
        flow.append(_para(justificativa[:1200], body_style, styles))
        flow.append(Spacer(1, 6))

    errc = pos.get("framework_errc") or {}
    if isinstance(errc, dict) and any(errc.get(k) for k in ("eliminar", "reduzir", "aumentar", "criar")):
        data = [["Dimensão", "Recomendações"]]
        labels = [
            ("eliminar", "Eliminar"),
            ("reduzir", "Reduzir"),
            ("aumentar", "Aumentar"),
            ("criar", "Criar"),
        ]
        for key, label in labels:
            items = errc.get(key) or []
            if isinstance(items, list) and items:
                data.append([label, "<br/>".join(f"• {i}" for i in items[:5])])
        if len(data) > 1:
            flow.append(Paragraph("Framework ERRC", styles.get("h2", styles[body_style])))
            flow.append(Spacer(1, 4))
            rows = []
            for row in data:
                rows.append([  # type: ignore
                    Paragraph(str(row[0]), styles[body_style]),
                    Paragraph(str(row[1]), styles[body_style]),
                ])
            flow.append(table_fn(rows, [3.5 * cm, CONTENT_W - 3.5 * cm]))
            flow.append(Spacer(1, 8))

    gaps = pos.get("gaps_identificados") or []
    if isinstance(gaps, list) and gaps:
        flow.append(Paragraph("GAPs de mercado", styles.get("h2", styles[body_style])))
        flow.append(Spacer(1, 4))
        gdata = [["GAP", "Potencial ticket", "Dificuldade"]]
        for g in gaps[:5]:
            if not isinstance(g, dict):
                continue
            gdata.append([
                str(g.get("gap") or "—")[:40],
                str(g.get("potencial_ticket") or "—"),
                str(g.get("dificuldade_implementacao") or "—"),
            ])
        if len(gdata) > 1:
            flow.append(table_fn(gdata, [6 * cm, 4 * cm, CONTENT_W - 10 * cm]))
            flow.append(Spacer(1, 8))

    ticket = pos.get("recomendacao_ticket") or {}
    if isinstance(ticket, dict) and ticket.get("ticket_recomendado") is not None:
        rec = ticket.get("ticket_recomendado")
        tmin = ticket.get("ticket_minimo")
        tmax = ticket.get("ticket_maximo")
        flow.append(
            _para(
                f"<b>Ticket recomendado:</b> R$ {rec}/mês "
                f"(faixa R$ {tmin or '—'} – R$ {tmax or '—'}). "
                f"{ticket.get('justificativa') or ''}"[:800],
                body_style,
                styles,
            ),
        )
        comp = ticket.get("comparativo_mercado") or {}
        if isinstance(comp, dict) and comp:
            parts = [f"{k}: R$ {v}" for k, v in list(comp.items())[:6]]
            flow.append(_para("Comparativo: " + " | ".join(parts), body_style, styles))
    return flow


def _extras_section(model: RelatorioPdfModel, styles: dict) -> list:
    flow: list = []
    if model.posicionamento:
        flow.extend(_section_title("7. Posicionamento recomendado", styles))
        flow.append(_para(model.posicionamento[:3500], "body", styles))

    flow.extend(
        _posicionamento_estrategico_flow(
            model.posicionamento_estrategico,
            styles,
            section_fn=_section_title,
            table_fn=_table,
            body_style="body",
        ),
    )

    if model.bairros_alternativos:
        flow.extend(_section_title("8. Bairros alternativos", styles))
        data: list[list[str | Paragraph]] = [["Bairro", "Prior.", "Conc.", "Motivo"]]
        for b in model.bairros_alternativos[:6]:
            data.append(
                [
                    _para(b.bairro[:40], "small", styles),
                    b.prioridade or "—",
                    str(b.concorrentes) if b.concorrentes is not None else "—",
                    _para(b.motivo[:120], "small", styles),
                ],
            )
        flow.append(_table(data, [4 * cm, 1.6 * cm, 1.4 * cm, CONTENT_W - 7 * cm]))

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
        _txt_ent = f"Novos entrantes CNPJ (90 dias) na cidade: <b>{model.entrantes_cnpj_total}</b>"
        if model.entrantes_cnpj_bairro is not None and model.entrantes_cnpj_bairro_nome:
            _txt_ent += (
                f" — sendo <b>{model.entrantes_cnpj_bairro}</b> no bairro-alvo "
                f"({model.entrantes_cnpj_bairro_nome})"
            )
        flow.append(_para(_txt_ent, "body", styles))
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


def _header_footer_bala(canvas, doc, model: RelatorioPdfModel) -> None:
    canvas.saveState()
    w, h = PAGE_SIZE
    # faixa teal no topo
    canvas.setFillColor(TEAL)
    canvas.rect(0, h - 0.4 * cm, w, 0.4 * cm, fill=1, stroke=0)
    canvas.setFillColor(CHARCOAL)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN_L, h - 0.9 * cm, "GymSite Intelligence")
    canvas.setFont("Helvetica", 8)
    loc = f"{model.bairro} · {model.cidade}"
    if model.uf:
        loc += f" / {model.uf}"
    canvas.drawRightString(w - MARGIN_R, h - 0.9 * cm, loc[:60])
    # rodapé
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN_L, 1.2 * cm, w - MARGIN_R, 1.2 * cm)
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        MARGIN_L,
        0.8 * cm,
        f"Relatório {model.relatorio_id} · gerado {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )
    canvas.drawRightString(w - MARGIN_R, 0.8 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _cover_block_bala(model: RelatorioPdfModel, styles: dict) -> list:
    ver = model.veredito or "—"
    vc = veredito_color(model.veredito)
    meta = (
        f"Área {model.area_m2_min}–{model.area_m2_max} m² · "
        f"{model.tipo_negocio.replace('_', ' ')} · "
        f"público {model.publico_alvo or '—'}"
    )
    badge = Table(
        [[Paragraph(ver.upper(), styles["bala_badge"])]],
        colWidths=[6 * cm],
    )
    badge.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), vc),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    cover_inner = [
        [Paragraph(f"<b>{model.bairro}</b> · {model.cidade}", styles["bala_cover_title"])],
        [badge],
        [Paragraph(meta, styles["bala_cover_sub"])],
        [
            Paragraph(
                f"Data da análise: {model.data_execucao or '—'}",
                styles["bala_cover_sub"],
            ),
        ],
    ]
    cover_tbl = Table(cover_inner, colWidths=[CONTENT_W])
    cover_tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CHARCOAL),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 20),
            ("RIGHTPADDING", (0, 0), (-1, -1), 20),
            ("TOPPADDING", (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ]),
    )

    # KPI cards
    kpi_data = [
        [
            Paragraph("Score bairro", styles["bala_kpi_label"]),
            Paragraph("Score Top 1", styles["bala_kpi_label"]),
            Paragraph("Saturação", styles["bala_kpi_label"]),
            Paragraph("Concorrentes", styles["bala_kpi_label"]),
        ],
        [
            Paragraph(_score(model.score_bairro), styles["bala_kpi_value"]),
            Paragraph(_score(model.score_top1), styles["bala_kpi_value"]),
            Paragraph(model.nivel_saturacao or "—", styles["bala_kpi_value"]),
            Paragraph(str(model.total_concorrentes or "—"), styles["bala_kpi_value"]),
        ],
    ]
    kpi_tbl = Table(kpi_data, colWidths=[CONTENT_W / 4] * 4)
    kpi_tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])
    )

    logo = _logo_flowable(6.2)
    out: list = []
    if logo is not None:
        out += [logo, Spacer(1, 8)]
    out += [cover_tbl, kpi_tbl, Spacer(1, 20)]
    return out


def _scores_section_bala(model: RelatorioPdfModel, styles: dict) -> list:
    flow = _section_title_bala("1. Scores e veredito", styles)
    kpi = [
        ["Score bairro", "Score Top 1", "Saturação", "Concorrentes analisados"],
        [
            _score(model.score_bairro),
            _score(model.score_top1),
            model.nivel_saturacao or "—",
            str(model.total_concorrentes or "—"),
        ],
    ]
    flow.append(_table_bala(kpi, [CONTENT_W / 4] * 4))
    flow.append(Spacer(1, 10))
    png = chart_scores_bar(model.scores)
    if png:
        flow.append(Image(io.BytesIO(png), width=CONTENT_W * 0.85, height=4.2 * cm))
    return flow


def _resumo_section_bala(model: RelatorioPdfModel, styles: dict) -> list:
    if not model.resumo_executivo:
        return []
    flow = _section_title_bala("2. Resumo executivo", styles)
    flow.append(_para(model.resumo_executivo[:4000], "bala_body", styles))
    return flow


def _market_section_bala(model: RelatorioPdfModel, styles: dict) -> list:
    if not model.market:
        return []
    m = model.market
    flow = _section_title_bala("3. Contexto de mercado", styles)
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
    flow.append(_table_bala(rows, [CONTENT_W * 0.45, CONTENT_W * 0.55]))
    if m.redes:
        flow.append(Spacer(1, 6))
        flow.append(_para("Redes mapeadas: " + ", ".join(m.redes[:8]), "bala_small", styles))
    for ins in m.insights[:3]:
        flow.append(_para(f"• {ins}", "bala_body", styles))
    return flow


def _candidatos_section_bala(model: RelatorioPdfModel, styles: dict) -> list:
    if not model.candidatos:
        return []
    flow = _section_title_bala("4. Top candidatos (imóveis)", styles)
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
        _table_bala(
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
                _para(f"<b>Cand. {c.posicao}:</b> {c.motivo[:400]}", "bala_small", styles),
            )
    return flow


def _finance_section_bala(model: RelatorioPdfModel, styles: dict, *, charts: bool) -> list:
    if not model.cenarios:
        return []
    flow = _section_title_bala("5. Viabilidade financeira (3 cenários)", styles)
    if model.modelo_recomendado:
        flow.append(
            _para(f"Modelo recomendado: <b>{model.modelo_recomendado}</b>", "bala_body", styles),
        )
    if model.aluguel_mensal is not None:
        extra = ""
        if model.aluguel_mediana_m2 is not None:
            extra = f" · mediana {_brl(model.aluguel_mediana_m2)}/m²"
        flow.append(_para(f"Aluguel estimado: <b>{_brl(model.aluguel_mensal)}</b>{extra}", "bala_body", styles))

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
    flow.append(_table_bala(data, [cw] * 8))

    if charts:
        flow.append(Spacer(1, 10))
        png1 = chart_capex_stacked(model.cenarios)
        if png1:
            flow.append(Image(io.BytesIO(png1), width=CONTENT_W, height=5.5 * cm))
        flow.append(Spacer(1, 6))
        png2 = chart_lucro_cenarios(model.cenarios)
        if png2:
            flow.append(Image(io.BytesIO(png2), width=CONTENT_W * 0.9, height=5 * cm))
    return flow


def _competition_section_bala(model: RelatorioPdfModel, styles: dict) -> list:
    if not model.competidores:
        return []
    flow = _section_title_bala("6. Inteligência competitiva", styles)
    if model.total_raio is not None:
        flow.append(
            _para(
                f"Academias no raio (agregado): <b>{model.total_raio}</b> · "
                f"amostra analisada: <b>{model.total_concorrentes or len(model.competidores)}</b>",
                "bala_body",
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
        _table_bala(
            data,
            [5.5 * cm, 1.5 * cm, 2 * cm, 3 * cm, 1.2 * cm],
        ),
    )
    return flow


def _extras_section_bala(model: RelatorioPdfModel, styles: dict) -> list:
    flow: list = []
    if model.posicionamento:
        flow.extend(_section_title_bala("7. Posicionamento recomendado", styles))
        flow.append(_para(model.posicionamento[:3500], "bala_body", styles))

    flow.extend(
        _posicionamento_estrategico_flow(
            model.posicionamento_estrategico,
            styles,
            section_fn=_section_title_bala,
            table_fn=_table_bala,
            body_style="bala_body",
        ),
    )

    if model.bairros_alternativos:
        flow.extend(_section_title_bala("8. Bairros alternativos", styles))
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
        flow.append(_table_bala(data, [3 * cm, 2 * cm, 2 * cm, CONTENT_W - 7 * cm]))

    if model.alertas:
        flow.extend(_section_title_bala("9. Alertas e ressalvas", styles))
        box = Table(
            [[_para("<br/>".join(f"• {a}" for a in model.alertas[:12]), "bala_body", styles)]],
            colWidths=[CONTENT_W],
        )
        box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FECACA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]),
        )
        flow.append(box)

    if model.entrantes_cnpj_total is not None:
        flow.append(Spacer(1, 8))
        _txt_ent = f"Novos entrantes CNPJ (90 dias) na cidade: <b>{model.entrantes_cnpj_total}</b>"
        if model.entrantes_cnpj_bairro is not None and model.entrantes_cnpj_bairro_nome:
            _txt_ent += (
                f" — sendo <b>{model.entrantes_cnpj_bairro}</b> no bairro-alvo "
                f"({model.entrantes_cnpj_bairro_nome})"
            )
        flow.append(_para(_txt_ent, "bala_body", styles))
    return flow


def _build_bala(model: RelatorioPdfModel, styles: dict) -> list:
    story: list = []
    story.extend(_cover_block_bala(model, styles))
    story.extend(_scores_section_bala(model, styles))
    story.extend(_resumo_section_bala(model, styles))
    story.extend(_market_section_bala(model, styles))
    story.append(PageBreak())
    story.extend(_candidatos_section_bala(model, styles))
    story.extend(_finance_section_bala(model, styles, charts=True))
    story.append(PageBreak())
    story.extend(_competition_section_bala(model, styles))
    story.extend(_extras_section_bala(model, styles))
    story.append(Spacer(1, 14))
    story.append(
        _para(
            "Documento gerado automaticamente pelo pipeline GymSite Intelligence (A0–A6). "
            "Valores são estimativas — validar com visita técnica e due diligence.",
            "bala_small",
            styles,
        ),
    )
    return story


@span("pdf.generate")
def generate_relatorio_pdf(
    model: RelatorioPdfModel,
    *,
    layout: LayoutId | str = LayoutId.CLASSIC,
) -> bytes:
    """Gera bytes do PDF para o relatório."""
    layout_id = LayoutId(layout) if isinstance(layout, str) else layout
    styles = build_styles()

    buf = io.BytesIO()

    if layout_id == LayoutId.BALA:
        doc = SimpleDocTemplate(
            buf,
            pagesize=PAGE_SIZE,
            leftMargin=MARGIN_L,
            rightMargin=MARGIN_R,
            topMargin=MARGIN_T,
            bottomMargin=MARGIN_B,
            title=f"GymSite — {model.bairro} {model.cidade}",
            author="GymSite Intelligence",
        )
        story = _build_bala(model, styles)
        doc.build(
            story,
            onFirstPage=lambda c, d: _header_footer_bala(c, d, model),
            onLaterPages=lambda c, d: _header_footer_bala(c, d, model),
        )
    else:
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
