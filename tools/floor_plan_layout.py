"""Deterministic gym zone floor plans via archit-app (SVG).

Anteprojeto only — not signed RRT. Used by agents_site `gerar_planta_layout_zonas`.

Área de cálculo = mediana da faixa de porte (mesma regra A4 `_derivar_area`),
não a área bruta informada e não um template fixo de 300 m².
Ex.: 1400 m² → faixa M 800–1500 → mediana 1150 → envelope 4:3 sobre 1150.
"""
from __future__ import annotations

import base64
import json
import math
from typing import Any

PRESET_MUSCULACAO_ENTRADA_FUNDO = "musculacao_entrada_fundo"

# Faixas canônicas = consultor / conversational_engine.TAMANHO_PRESET_AREAS
# Mediana (min+max)/2 = área de cálculo (A4 `_derivar_area`).
PORTE_FAIXAS_M2: dict[str, tuple[float, float]] = {
    "pp": (200.0, 500.0),
    "p": (500.0, 800.0),
    "m": (800.0, 1500.0),
    "g": (1500.0, 2500.0),
    "gg": (2500.0, 5000.0),
}

# L:C do salão quando o usuário não informa eixos (entrada→fundo × lateral).
_ASPECT_RATIO_LC = 4.0 / 3.0

# (label, x0_frac, y0_frac, x1_frac, y1_frac) — tiles full floor; y=0 entrance front
_MUSCULACAO_TILES: tuple[tuple[str, float, float, float, float], ...] = (
    ("Mobilidade · core · aquecimento", 0.0, 0.0, 0.35, 0.20),
    ("Máquinas guiadas · membros superiores", 0.35, 0.0, 1.0, 0.20),
    ("Máquinas guiadas · pernas · glúteos", 0.0, 0.20, 0.50, 0.40),
    ("Polias · crossover", 0.50, 0.20, 1.0, 0.40),
    ("Halteres · bancos · espelhos", 0.0, 0.40, 1.0, 0.80),
    ("Racks · agachamento · peso pesado", 0.0, 0.80, 1.0, 1.0),
)


def resolver_area_calculo(area_informada_m2: float) -> dict[str, Any]:
    """Encaixa a área na faixa de porte e devolve a mediana de cálculo.

    Fonte: faixas PP/P/M/G/GG do consultor; mediana = (min+max)/2 como A4.
    Intervalos semi-abertos [min, max) — fronteira inferior pertence à faixa
    (800 → M, 1500 → G). Última faixa (GG) fecha no teto.
    """
    area = max(1.0, float(area_informada_m2))
    ordered = list(PORTE_FAIXAS_M2.items())
    preset, lo, hi = ordered[0][0], ordered[0][1][0], ordered[0][1][1]
    for i, (codigo, (a_min, a_max)) in enumerate(ordered):
        last = i == len(ordered) - 1
        if area < a_min:
            break
        if last or area < a_max:
            preset, lo, hi = codigo, a_min, a_max
            if not last:
                break
    mediana = round((lo + hi) / 2.0, 1)
    return {
        "area_informada_m2": round(area, 1),
        "area_calculo_m2": mediana,
        "tamanho_preset": preset,
        "area_m2_min": int(lo),
        "area_m2_max": int(hi),
        "metodo": "mediana_faixa_porte",
        "fonte": "A4 _derivar_area · TAMANHO_PRESET_AREAS",
    }


def _dimensoes(area_m2: float, comprimento_m: float, largura_m: float) -> tuple[float, float]:
    """Envelope do salão. Sem L×C → retângulo proporção 4:3 sobre `area_m2` de cálculo."""
    area = max(1.0, float(area_m2))
    if comprimento_m > 0 and largura_m > 0:
        return float(comprimento_m), float(largura_m)
    if comprimento_m > 0:
        return float(comprimento_m), round(area / comprimento_m, 2)
    if largura_m > 0:
        return round(area / largura_m, 2), float(largura_m)
    w = math.sqrt(area * _ASPECT_RATIO_LC)
    h = area / w
    return round(w, 2), round(h, 2)


def _bbox_m(w: float, h: float, x0f: float, y0f: float, x1f: float, y1f: float) -> dict[str, float]:
    return {
        "x0_m": round(x0f * w, 2),
        "y0_m": round(y0f * h, 2),
        "x1_m": round(x1f * w, 2),
        "y1_m": round(y1f * h, 2),
    }


def _area_zona_m2(bbox: dict[str, float]) -> float:
    return round((bbox["x1_m"] - bbox["x0_m"]) * (bbox["y1_m"] - bbox["y0_m"]), 1)


def build_level_from_tiles(
    width_m: float,
    depth_m: float,
    tiles: tuple[tuple[str, float, float, float, float], ...],
):
    from archit_app import Level, Polygon2D, Room, WORLD

    level = Level(index=0, elevation=0.0, floor_height=3.0, name="Sala musculação")
    for label, x0f, y0f, x1f, y1f in tiles:
        poly = Polygon2D.rectangle(
            x0f * width_m,
            y0f * depth_m,
            x1f * width_m,
            y1f * depth_m,
            crs=WORLD,
        )
        level = level.add_room(Room(boundary=poly, name=label))
    return level


def render_layout_svg(
    area_m2: float,
    *,
    comprimento_m: float = 0.0,
    largura_m: float = 0.0,
    preset: str = PRESET_MUSCULACAO_ENTRADA_FUNDO,
    pixels_per_meter: int = 35,
) -> dict[str, Any]:
    """Build zone layout and return SVG + metadata.

    Sem eixos explícitos, o envelope usa a mediana da faixa de porte da área
    informada (ex. 1400 → M → 1150 m²), não a área bruta.
    """
    try:
        from archit_app.io.svg import level_to_svg
    except ImportError as e:
        return {
            "erro": "archit-app não instalado (pip install 'archit-app[io]')",
            "detalhe": str(e),
        }

    if preset != PRESET_MUSCULACAO_ENTRADA_FUNDO:
        return {
            "erro": f"preset desconhecido: {preset!r}",
            "presets_validos": [PRESET_MUSCULACAO_ENTRADA_FUNDO],
        }

    gate = resolver_area_calculo(area_m2)
    eixos_explicito = comprimento_m > 0 or largura_m > 0
    area_envelope = float(area_m2) if eixos_explicito else gate["area_calculo_m2"]
    w, h = _dimensoes(area_envelope, comprimento_m, largura_m)
    level = build_level_from_tiles(w, h, _MUSCULACAO_TILES)
    svg = level_to_svg(level, pixels_per_meter=pixels_per_meter)

    zonas: list[dict[str, Any]] = []
    for label, x0f, y0f, x1f, y1f in _MUSCULACAO_TILES:
        bbox = _bbox_m(w, h, x0f, y0f, x1f, y1f)
        zonas.append({"nome": label, "bbox_m": bbox, "area_m2": _area_zona_m2(bbox)})

    return {
        "tipo": "anteprojeto_nao_oficial",
        "preset": preset,
        "dimensoes_m": {
            "comprimento": w,
            "largura": h,
            "area_informada_m2": gate["area_informada_m2"],
            "area_calculo_m2": gate["area_calculo_m2"],
            "area_desenhada_m2": round(w * h, 1),
            "tamanho_preset": gate["tamanho_preset"],
            "area_m2_min": gate["area_m2_min"],
            "area_m2_max": gate["area_m2_max"],
            "metodo_area": (
                "eixos_explicitos" if eixos_explicito else gate["metodo"]
            ),
        },
        "fluxo": "entrada (y=0) → mobilidade/máquinas → halteres → racks (fundo)",
        "zonas": zonas,
        "svg": svg,
        "svg_base64": base64.b64encode(svg.encode("utf-8")).decode("ascii"),
        "fonte": "archit-app · GymSite floor_plan_layout · mediana_faixa_porte",
        "aviso": (
            "Anteprojeto conceitual para discussão — não substitui planta assinada (RRT). "
            "Envelope calculado na mediana da faixa de porte "
            f"({gate['tamanho_preset'].upper()} {gate['area_m2_min']}–{gate['area_m2_max']} m² "
            f"→ {gate['area_calculo_m2']} m²), não na área bruta informada. "
            "Conferir NBR 9050, Corpo de Bombeiros, pilares/janelas/entrada real e COE local."
        ),
    }


def sanitize_planta_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    """Poll API: drop svg_base64 duplicate — front uses `svg` only."""
    if not isinstance(result, dict):
        return result
    out = dict(result)
    out.pop("svg_base64", None)
    return out


def sanitize_tool_calls_planta(tool_calls: list | None) -> None:
    """In-place: strip svg_base64 from gerar_planta_layout_zonas results in poll payload."""
    if not isinstance(tool_calls, list):
        return
    for tc in tool_calls:
        if not isinstance(tc, dict):
            continue
        if tc.get("ferramenta") != "gerar_planta_layout_zonas":
            continue
        r = tc.get("resultado")
        if isinstance(r, dict):
            tc["resultado"] = sanitize_planta_tool_result(r)


def parse_zonas_json(zonas_json: str) -> list[dict[str, Any]] | None:
    raw = (zonas_json or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return [z for z in data if isinstance(z, dict)]
