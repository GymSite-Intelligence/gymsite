"""Absorção / margem fresca — pool etário × parque (proxy área×tier) vs teto."""
from __future__ import annotations

from typing import Any, Literal

from tools.matriz_demo_saturacao import contar_mix
from tools.parametros_metodologia import param

Modelo = Literal["low", "mid", "premium"]
Rotulo = Literal["fresco", "misto", "roubo"]

FAIXAS_IBGE_15MAIS = ("15-24", "25-39", "40-59", "60+")
FAIXA_BOUNDS = {
    "15-24": (15, 24),
    "25-39": (25, 39),
    "40-59": (40, 59),
    "60+": (60, 120),
}


def faixas_primario_from_idade(idade_min: int, idade_max: int) -> list[str]:
    lo, hi = int(idade_min), int(idade_max)
    if hi < lo:
        lo, hi = hi, lo
    out: list[str] = []
    for f in FAIXAS_IBGE_15MAIS:
        a, b = FAIXA_BOUNDS[f]
        if lo <= b and hi >= a:
            out.append(f)
    return out


def faixas_secundario_from_primario(primario: list[str]) -> list[str]:
    s = set(primario)
    return [f for f in FAIXAS_IBGE_15MAIS if f not in s]


def _perfil_ab(renda_pc: float | None, perfil_ab: bool | None) -> bool:
    if perfil_ab is not None:
        return bool(perfil_ab)
    if renda_pc is None:
        return False
    return float(renda_pc) >= float(param("perfil_ab_renda_pc_min"))


def _penetracao_efetiva(renda_pc: float | None, perfil_ab: bool | None) -> tuple[float, str]:
    ab = _perfil_ab(renda_pc, perfil_ab)
    key = "penetracao_bairro_ab" if ab else "penetracao_geral"
    return float(param(key)), key


def _carimbo(valor: Any, base: str, fonte: str, janela: str = "n/a") -> str:
    return f"{valor} · {base} · {fonte} · {janela}"


def _estoque_faixas(segmentos: dict[str, Any], faixas: list[str]) -> int:
    total = 0
    for f in faixas:
        cell = segmentos.get(f) or {}
        if isinstance(cell, dict):
            total += int(cell.get("total") or 0)
        elif isinstance(cell, (int, float)):
            total += int(cell)
    return total


def absorcao_margem_fresca(
    *,
    concorrentes: list[dict[str, Any]] | None,
    pop_poligono: int | float | None,
    area_candidato_m2: float,
    modelo_cenario: str,
    renda_pc: float | None = None,
    perfil_ab: bool | None = None,
    fonte_espacial: str = "raio_fallback",
    censo_base: str | None = None,
    segmentos: dict[str, Any] | None = None,
    idade_min: int | None = None,
    idade_max: int | None = None,
) -> dict[str, Any]:
    modelo: Modelo = (
        modelo_cenario if modelo_cenario in ("low", "mid", "premium") else "mid"
    )  # type: ignore[assignment]
    mix = contar_mix(concorrentes)

    a_low = float(param("area_proxy_low_m2"))
    a_mid = float(param("area_proxy_mid_m2"))
    a_prem = float(param("area_proxy_premium_m2"))
    a_nd = float(param("area_proxy_nicho_desconhecido_m2"))

    m_low = float(param("matr_m2_low_realista"))
    m_mid = float(param("matr_m2_mid_realista"))
    m_prem = float(param("matr_m2_premium_realista"))

    cap = (
        mix.get("low", 0) * a_low * m_low
        + mix.get("mid", 0) * a_mid * m_mid
        + mix.get("premium", 0) * a_prem * m_prem
        + (mix.get("nicho", 0) + mix.get("desconhecido", 0)) * a_nd * m_mid
    )
    cap_i = int(round(cap))

    interesse = float(param("penetracao_potencial_fitness"))
    pen, pen_key = _penetracao_efetiva(renda_pc, perfil_ab)
    imin = int(idade_min if idade_min is not None else param("publico_fitness_idade_min"))
    imax = int(idade_max if idade_max is not None else param("publico_fitness_idade_max"))
    prim = faixas_primario_from_idade(imin, imax)
    sec = faixas_secundario_from_primario(prim)

    if isinstance(segmentos, dict) and segmentos:
        est_p = _estoque_faixas(segmentos, prim)
        est_s = _estoque_faixas(segmentos, sec)
        pool_p = int(round(est_p * interesse * pen))
        pool_s = int(round(est_s * interesse * pen))
        pool_t = int(round((est_p + est_s) * interesse * pen))
        pool_stamp = f"estoque_form×interesse×{pen_key}"
    else:
        est_p = int(pop_poligono or 0)
        est_s = 0
        pool_p = int(round(est_p * interesse * pen))
        pool_s = 0
        pool_t = pool_p
        pool_stamp = "fallback_pop_total"
        sec = []

    matr_modelo = float(param(f"matr_m2_{modelo}_realista"))
    teto = int(round(float(area_candidato_m2) * matr_modelo))

    margem = pool_p - cap_i
    if margem >= teto:
        rotulo: Rotulo = "fresco"
    elif margem > 0:
        rotulo = "misto"
    else:
        rotulo = "roubo"

    base_esp = (
        "poligono_ibge"
        if fonte_espacial in ("poligono_ibge", "poligono_ibge_bairro")
        else "raio_fallback"
    )

    nota = (
        "Faixas fora do formulário (ex. Jovem/Silver) têm pool secundário — "
        "informam modelo, não o rótulo fresco/roubo."
    )

    return {
        "teto_unidade": teto,
        "modelo_teto": modelo,
        "area_candidato_m2": float(area_candidato_m2),
        "capacidade_parque_estimada": cap_i,
        "mix": mix,
        "pool_demografico": pool_p,
        "pool_primario": pool_p,
        "pool_secundario": pool_s,
        "pool_total_15mais": pool_t,
        "estoque_primario": est_p,
        "estoque_secundario": est_s,
        "faixas_primario": prim,
        "faixas_secundario": sec,
        "interesse_fitness": interesse,
        "penetracao_efetiva": pen,
        "margem_fresca": margem,
        "rotulo": rotulo,
        "nota_modelo_secundario": nota,
        "carimbos": {
            "teto_unidade": _carimbo(
                teto,
                f"{area_candidato_m2}m²×{matr_modelo}",
                f"matr_m2_{modelo}_realista",
                "ACAD/param",
            ),
            "capacidade_parque_estimada": _carimbo(
                cap_i, "N×tier×área_proxy×matr/m²", "proxy franquia", "não medido"
            ),
            "pool_demografico": _carimbo(
                pool_p, pool_stamp, "IBGE+param", censo_base or "n/d"
            ),
            "margem_fresca": _carimbo(
                margem, "pool_primario−cap_parque", "derivada", "n/a"
            ),
        },
        "area_proxy_usada": {
            "low": int(a_low),
            "mid": int(a_mid),
            "premium": int(a_prem),
            "nicho_desconhecido": int(a_nd),
        },
        "base_espacial": base_esp,
    }


def _segmentos_from_demo(demo: dict[str, Any]) -> dict[str, Any] | None:
    pir = demo.get("perfil_idade_sexo_bairro")
    if isinstance(pir, dict):
        segs = pir.get("segmentos")
        if isinstance(segs, dict) and segs:
            return segs
    segs2 = demo.get("segmentos")
    if isinstance(segs2, dict) and segs2:
        return segs2
    return None


def _idades_from_state(state: dict[str, Any]) -> tuple[int | None, int | None]:
    ip = state.get("input_params")
    if isinstance(ip, dict):
        for a, b in (
            ("idade_min", "idade_max"),
            ("publico_fitness_idade_min", "publico_fitness_idade_max"),
        ):
            if ip.get(a) is not None and ip.get(b) is not None:
                try:
                    return int(ip[a]), int(ip[b])
                except (TypeError, ValueError):
                    pass
    return None, None


def aplicar_veto_oceano_por_roubo(parsed: dict[str, Any]) -> bool:
    """Se rótulo absorção = roubo, OCEANO_AZUL vira TRANSICAO (não piora VERMELHO)."""
    abs_ = parsed.get("absorcao_margem_fresca")
    if not isinstance(abs_, dict) or abs_.get("rotulo") != "roubo":
        return False
    vere = str(parsed.get("veredito_posicionamento") or "").upper()
    if vere != "OCEANO_AZUL":
        return False
    parsed["veredito_antes_veto_absorcao"] = parsed.get("veredito_posicionamento")
    parsed["veredito_posicionamento"] = "TRANSICAO"
    parsed["veto_absorcao_roubo"] = True
    prev = parsed.get("fonte_veredito") or ""
    parsed["fonte_veredito"] = (
        f"{prev} | veto_absorcao_roubo→TRANSICAO".strip(" |")
        if prev
        else "veto_absorcao_roubo→TRANSICAO"
    )
    return True


def attach_absorcao_margem_fresca(
    state: dict[str, Any], parsed: dict[str, Any]
) -> dict[str, Any] | None:
    """A9 hook: compute absorção into parsed (irmão da Matriz)."""
    from tools.matriz_demo_saturacao import concorrentes_espaciais_from_state

    demo = state.get("demografia_bairro") if isinstance(state.get("demografia_bairro"), dict) else {}
    hr = parsed.get("headroom_renda") if isinstance(parsed.get("headroom_renda"), dict) else {}
    pop = demo.get("populacao") if demo.get("populacao") is not None else hr.get("populacao")
    renda_pc = hr.get("renda_pc") or demo.get("renda_media_per_capita") or demo.get("renda_pc")

    area = state.get("area_m2") or state.get("area_candidato_m2")
    if area is None:
        area = 1500.0

    modelo = (
        parsed.get("modelo_sugerido")
        or (parsed.get("matriz_demo_saturacao") or {}).get("modelo_sugerido")
        or state.get("modelo_recomendado")
        or "mid"
    )
    modelo_s = str(modelo).lower()
    if "premium" in modelo_s:
        modelo_c = "premium"
    elif "low" in modelo_s:
        modelo_c = "low"
    else:
        modelo_c = "mid"

    imin, imax = _idades_from_state(state)
    cs, fonte = concorrentes_espaciais_from_state(state)
    result = absorcao_margem_fresca(
        concorrentes=cs,
        pop_poligono=pop,
        area_candidato_m2=float(area),
        modelo_cenario=modelo_c,
        renda_pc=float(renda_pc) if renda_pc is not None else None,
        fonte_espacial=fonte,
        censo_base=str(demo.get("censo_base") or fonte),
        segmentos=_segmentos_from_demo(demo),
        idade_min=imin,
        idade_max=imax,
    )
    parsed["absorcao_margem_fresca"] = result
    aplicar_veto_oceano_por_roubo(parsed)
    return result
