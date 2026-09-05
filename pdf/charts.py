"""Gráficos Matplotlib → PNG em memória para embutir no PDF."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdf.models import CenarioPdf, ScoreDim

# Backend não-interativo (servidor / Docker)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _fig_to_png(fig: plt.Figure, dpi: int = 140) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def chart_scores_bar(scores: list[ScoreDim], width_in: float = 6.0) -> bytes | None:
    labels = [s.label for s in scores if s.value is not None]
    values = [s.value for s in scores if s.value is not None]
    if not values:
        return None

    fig, ax = plt.subplots(figsize=(width_in, 2.4))
    colors = ["#0D9488", "#1B2A4A", "#E8751A"][: len(values)]
    bars = ax.barh(labels, values, color=colors, height=0.55)
    ax.set_xlim(0, 10)
    ax.set_xlabel("Score (0–10)")
    ax.set_title("Scores regionais", fontsize=11, fontweight="bold", color="#1B2A4A")
    ax.axvline(6, color="#94A3B8", linestyle="--", linewidth=0.8, alpha=0.7)
    for bar, val in zip(bars, values, strict=True):
        ax.text(
            min(val + 0.15, 9.5),
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}",
            va="center",
            fontsize=9,
            color="#1E293B",
        )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_png(fig)


def chart_capex_stacked(cenarios: list[CenarioPdf], width_in: float = 6.5) -> bytes | None:
    labels: list[str] = []
    obra: list[float] = []
    cont: list[float] = []

    for c in cenarios:
        o = c.capex_obra or 0
        t = c.capex_contingencia or 0
        if o + t <= 0:
            continue
        labels.append(c.label)
        obra.append(o)
        cont.append(t)

    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(width_in, 2.8))
    x = range(len(labels))
    ax.bar(x, obra, label="Obra / adaptação", color="#1B2A4A")
    ax.bar(x, cont, bottom=obra, label="Contingência", color="#E8751A")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_title("Composição do CAPEX por modelo", fontsize=11, fontweight="bold", color="#1B2A4A")
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"R$ {v/1e6:.1f}M" if v >= 1e6 else f"R$ {v/1e3:.0f}k"),
    )
    ax.legend(fontsize=7, loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_png(fig)


def chart_gauge_veredito(
    score: float | None, veredito: str | None, width_in: float = 3.2
) -> bytes | None:
    """Medidor radial 0–10 do score da praça, com a faixa colorida pelo veredito.

    Fase A do contrato de dados — usa score_bairro (existe no model). Cor do arco
    de preenchimento = VEREDITO_COLORS; fundo cinza claro.
    """
    import numpy as np

    if score is None:
        return None
    s = max(0.0, min(10.0, float(score)))
    cor = {
        "APROVADO": "#16A34A",
        "APROVADO COM RESSALVAS": "#CA8A04",
        "INVESTIGAR MAIS": "#EA580C",
        "REPROVADO": "#DC2626",
    }.get((veredito or "").upper().strip(), "#0D9488")

    fig, ax = plt.subplots(figsize=(width_in, width_in * 0.62), subplot_kw={"aspect": "equal"})
    # semicírculo 180° (esq=0, dir=10)
    theta_full = np.linspace(np.pi, 0, 100)
    theta_val = np.linspace(np.pi, np.pi - (s / 10.0) * np.pi, 100)
    for th, c, lw in ((theta_full, "#E2E8F0", 14), (theta_val, cor, 14)):
        ax.plot(np.cos(th), np.sin(th), color=c, linewidth=lw, solid_capstyle="round")
    ax.text(0, -0.02, f"{s:.1f}", ha="center", va="center", fontsize=22,
            fontweight="bold", color="#1B2A4A")
    ax.text(0, -0.30, "/ 10", ha="center", va="center", fontsize=9, color="#64748B")
    if veredito:
        ax.text(0, 0.42, veredito.upper(), ha="center", va="center", fontsize=8.5,
                fontweight="bold", color=cor)
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-0.4, 0.75)
    ax.axis("off")
    fig.tight_layout()
    return _fig_to_png(fig)


def chart_radar_perfil(scores: list[ScoreDim], width_in: float = 3.6) -> bytes | None:
    """Radar do perfil da praça (eixos = dimensões de score 0–10).

    Fase B do contrato — usa scores[ScoreDim] (já no model; 3 eixos hoje:
    demográfico/competitivo/viabilidade). Eixos None são pulados.
    """
    import numpy as np

    dims = [(s.label, s.value) for s in scores if s.value is not None]
    if len(dims) < 3:
        return None  # radar precisa de ≥3 eixos
    labels = [d[0] for d in dims]
    vals = [float(d[1]) for d in dims]
    ang = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    vals_c = vals + vals[:1]
    ang_c = ang + ang[:1]

    fig, ax = plt.subplots(figsize=(width_in, width_in), subplot_kw={"polar": True})
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 10)
    ax.set_xticks(ang)
    ax.set_xticklabels(labels, fontsize=8, color="#1E293B")
    ax.set_yticks([2, 4, 6, 8])
    ax.set_yticklabels(["2", "4", "6", "8"], fontsize=6, color="#94A3B8")
    ax.plot(ang_c, vals_c, color="#115E59", linewidth=1.4)
    ax.fill(ang_c, vals_c, color="#0D9488", alpha=0.25)
    ax.set_title("Perfil da praça", fontsize=10, fontweight="bold", color="#1B2A4A", pad=14)
    fig.tight_layout()
    return _fig_to_png(fig)


def chart_receita_resultado_cenarios(
    cenarios: list[CenarioPdf], width_in: float = 6.0
) -> bytes | None:
    """Colunas agrupadas receita × resultado (lucro) por cenário.

    Fase A — usa receita_mensal/lucro_mensal (já no model). Cenários sem receita
    são pulados.
    """
    import numpy as np

    labels: list[str] = []
    receitas: list[float] = []
    lucros: list[float] = []
    for c in cenarios:
        if c.receita_mensal is None and c.lucro_mensal is None:
            continue
        labels.append(c.label)
        receitas.append(c.receita_mensal or 0.0)
        lucros.append(c.lucro_mensal or 0.0)
    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(width_in, 2.8))
    x = np.arange(len(labels))
    w = 0.38
    ax.bar(x - w / 2, receitas, w, label="Receita mensal", color="#0D9488")
    ax.bar(x + w / 2, lucros, w, label="Resultado mensal",
           color=["#16A34A" if v >= 0 else "#DC2626" for v in lucros])
    ax.axhline(0, color="#64748B", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_title("Receita × resultado por cenário", fontsize=11, fontweight="bold", color="#1B2A4A")
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"R$ {v/1e3:.0f}k" if abs(v) >= 1e3 else f"R$ {v:.0f}")
    )
    ax.legend(fontsize=7, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_png(fig)


def chart_lucro_cenarios(cenarios: list[CenarioPdf], width_in: float = 6.0) -> bytes | None:
    labels: list[str] = []
    lucros: list[float] = []
    for c in cenarios:
        if c.lucro_mensal is None:
            continue
        labels.append(c.label)
        lucros.append(c.lucro_mensal)

    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(width_in, 2.6))
    bar_colors = ["#16A34A" if v >= 0 else "#DC2626" for v in lucros]
    ax.bar(labels, lucros, color=bar_colors, width=0.55)
    ax.axhline(0, color="#64748B", linewidth=0.8)
    ax.set_title("Lucro mensal estimado", fontsize=11, fontweight="bold", color="#1B2A4A")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"R$ {v:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_png(fig)
