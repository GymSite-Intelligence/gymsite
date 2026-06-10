"""Pesos do heatmap oceano — espelha frontend/src/lib/heatmap-weight.ts."""

from __future__ import annotations


def oceano_heatmap_weight(veredito: str | None) -> float:
    if veredito == "OCEANO_AZUL":
        return 0.5
    if veredito == "TRANSICAO":
        return 2.0
    if veredito in ("VERMELHO", "OCEANO_VERMELHO"):
        return 4.0
    return 1.0


def pin_heatmap_weight(
    *,
    score_concorrencia: float | None,
    veredito_oceano: str | None,
) -> float:
    if score_concorrencia is not None:
        return max(0.1, 11.0 - float(score_concorrencia))
    return oceano_heatmap_weight(veredito_oceano)


def test_score_concorrencia_inverts_favorability() -> None:
    assert pin_heatmap_weight(score_concorrencia=10.0, veredito_oceano="VERMELHO") == 1.0
    assert pin_heatmap_weight(score_concorrencia=1.0, veredito_oceano="OCEANO_AZUL") == 10.0


def test_oceano_fallback() -> None:
    assert oceano_heatmap_weight("OCEANO_AZUL") < oceano_heatmap_weight("VERMELHO")
    assert pin_heatmap_weight(score_concorrencia=None, veredito_oceano="TRANSICAO") == 2.0
