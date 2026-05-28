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
    equip: list[float] = []
    cont: list[float] = []

    for c in cenarios:
        o = c.capex_obra or 0
        e = c.capex_equipamentos or 0
        t = c.capex_contingencia or 0
        if o + e + t <= 0:
            continue
        labels.append(c.label)
        obra.append(o)
        equip.append(e)
        cont.append(t)

    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(width_in, 2.8))
    x = range(len(labels))
    ax.bar(x, obra, label="Obra / adaptação", color="#1B2A4A")
    ax.bar(x, equip, bottom=obra, label="Equipamentos", color="#0D9488")
    bottom2 = [o + e for o, e in zip(obra, equip, strict=True)]
    ax.bar(x, cont, bottom=bottom2, label="Contingência", color="#E8751A")
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
