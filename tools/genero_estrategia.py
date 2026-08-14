"""Regra determinística de gênero-alvo (PONTO 52 / limiar configurável).

Academia: se a diferença mulheres−homens na faixa-alvo for < limiar → misto;
senão prevalece o lado majoritário. Não inventa % — só classifica.
"""
from __future__ import annotations

# publico_alvo do form → chave em perfil_idade_sexo_bairro.segmentos
_PUBLICO_PARA_FAIXA = {
    "15-24": "15-24",
    "18-24": "15-24",
    "25-40": "25-39",
    "25-39": "25-39",
    "25-45": "25-39",
    "40-59": "40-59",
    "40-60": "40-59",
    "60+": "60+",
    "60-": "60+",
}


def limiar_genero_pp() -> float:
    try:
        from tools.parametros_metodologia import param

        return float(param("genero_diff_limiar_pp"))
    except Exception:
        return 8.0


def classificar_genero(
    pct_mulheres: float | None,
    pct_homens: float | None,
    limiar: float | None = None,
) -> dict:
    """Classifica feminino | masculino | misto | indeterminado."""
    lim = float(limiar if limiar is not None else limiar_genero_pp())
    try:
        pm = float(pct_mulheres)  # type: ignore[arg-type]
        ph = float(pct_homens)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return {
            "genero": "misto",
            "diff_pp": None,
            "limiar_pp": lim,
            "pct_mulheres": None,
            "pct_homens": None,
            "nivel_base": "indeterminado",
        }

    diff = abs(pm - ph)
    if diff < lim:
        genero = "misto"
    elif pm > ph:
        genero = "feminino"
    else:
        genero = "masculino"

    return {
        "genero": genero,
        "diff_pp": round(diff, 1),
        "limiar_pp": lim,
        "pct_mulheres": pm,
        "pct_homens": ph,
        "nivel_base": "classificado",
    }


def resolver_faixa_alvo(state_or_params: dict | None, perfil: dict | None = None) -> str:
    """Faixa canônica para gênero e ERRC (PONTO 80): input > perfil > 25-39."""
    if isinstance(perfil, dict):
        fi = str(perfil.get("faixa_idade") or "").strip()
        if fi in ("15-24", "25-39", "40-59", "60+"):
            return fi

    src = state_or_params if isinstance(state_or_params, dict) else {}
    ip = src.get("input_params") if isinstance(src.get("input_params"), dict) else src
    publico = str(
        (ip or {}).get("publico_alvo")
        or src.get("publico_alvo")
        or ""
    ).strip().lower()
    for key, faixa in _PUBLICO_PARA_FAIXA.items():
        if key in publico or publico == key:
            return faixa
    return "25-39"


def _pcts_da_faixa(perfil: dict, faixa: str) -> tuple[float | None, float | None]:
    seg = perfil.get("segmentos") if isinstance(perfil.get("segmentos"), dict) else {}
    dados = seg.get(faixa) if isinstance(seg, dict) else None
    if isinstance(dados, dict) and dados.get("total"):
        return dados.get("pct_mulheres"), dados.get("pct_homens")
    if str(perfil.get("faixa_idade") or "") == faixa:
        return perfil.get("pct_mulheres"), perfil.get("pct_homens")
    return None, None


def extrair_genero_do_state(state: dict, limiar: float | None = None) -> dict:
    """
    Cascata de bases (mais específica → genérica):
      1. perfil_idade_sexo_bairro na faixa-alvo (bairro_faixa_alvo)
      2. sexo_total do bairro
      3. perfil_sexo_publico (município)
      4. misto / nenhum
    """
    lim = float(limiar if limiar is not None else limiar_genero_pp())
    demo = state.get("demografia_bairro") if isinstance(state.get("demografia_bairro"), dict) else {}
    if not demo:
        oc = state.get("output_consolidado") if isinstance(state.get("output_consolidado"), dict) else {}
        demo = oc.get("demografia_bairro") if isinstance(oc.get("demografia_bairro"), dict) else {}

    perfil = demo.get("perfil_idade_sexo_bairro") if isinstance(demo, dict) else None
    if isinstance(perfil, dict) and (perfil.get("total") or perfil.get("segmentos")):
        faixa = resolver_faixa_alvo(state, perfil)
        pm, ph = _pcts_da_faixa(perfil, faixa)
        if pm is not None and ph is not None:
            out = classificar_genero(pm, ph, lim)
            out["nivel_base"] = "bairro_faixa_alvo"
            out["faixa_idade"] = faixa
            out["fonte"] = "perfil_idade_sexo_bairro"
            return out

        st = perfil.get("sexo_total") if isinstance(perfil.get("sexo_total"), dict) else None
        if isinstance(st, dict) and st.get("pct_mulheres") is not None:
            out = classificar_genero(st.get("pct_mulheres"), st.get("pct_homens"), lim)
            out["nivel_base"] = "bairro_sexo_total"
            out["fonte"] = "perfil_idade_sexo_bairro.sexo_total"
            return out

    mun = demo.get("perfil_sexo_publico") if isinstance(demo, dict) else None
    if isinstance(mun, dict) and mun.get("pct_mulheres") is not None:
        out = classificar_genero(mun.get("pct_mulheres"), mun.get("pct_homens"), lim)
        out["nivel_base"] = "municipio"
        out["fonte"] = "perfil_sexo_publico"
        return out

    return {
        "genero": "misto",
        "diff_pp": None,
        "limiar_pp": lim,
        "pct_mulheres": None,
        "pct_homens": None,
        "nivel_base": "nenhum",
        "fonte": None,
    }


def aplicar_regra_genero(
    genero_input: str | None,
    state: dict,
    limiar: float | None = None,
) -> dict:
    """
    Sobrescreve só quando input é misto/vazio e a demografia fecha um lado.
    Retorna carimbo para insight (PONTO 55).
    """
    dec = extrair_genero_do_state(state, limiar=limiar)
    entrada = str(genero_input or "misto").strip().lower() or "misto"
    # Normaliza aliases do form conversacional
    if entrada in ("predom_fem", "predominantemente_feminino", "feminino"):
        entrada_norm = "feminino" if "fem" in entrada else entrada
    elif entrada in ("predom_masc", "predominantemente_masculino", "masculino"):
        entrada_norm = "masculino"
    else:
        entrada_norm = "misto" if entrada in ("misto", "", "none", "null") else entrada

    estrategia = dec.get("genero") or "misto"
    sobrescrito = False
    final = entrada_norm
    if entrada_norm == "misto" and estrategia in ("feminino", "masculino"):
        final = estrategia
        sobrescrito = True
    elif entrada_norm in ("feminino", "masculino", "exclusivamente_feminino", "exclusivamente_masculino"):
        final = entrada_norm
        sobrescrito = False

    insight = None
    if sobrescrito:
        insight = (
            f"Estratégia ajustada de '{genero_input or 'misto'}' para '{final}' "
            f"(diff {dec.get('diff_pp')}pp ≥ limiar {dec.get('limiar_pp')}pp). "
            f"Fonte: {dec.get('fonte') or dec.get('nivel_base')}."
        )

    return {
        **dec,
        "genero_input": genero_input or "misto",
        "genero_final": final,
        "sobrescrito": sobrescrito,
        "insight": insight,
    }


def sugestoes_genero_errc(estrategia: str, pct_publico: float | None = None) -> list[str]:
    """Pauta ERRC no público majoritário (PONTO 56) — textos, não inventa oferta."""
    g = str(estrategia or "misto").lower()
    pct = f"{pct_publico:.0f}%" if isinstance(pct_publico, (int, float)) else "maioria"
    if g == "feminino":
        return [
            f"Grade e acolhimento com viés feminino (público {pct} na faixa-alvo): "
            "yoga/pilates, dança, funcional feminino, nutrição mulher, pós-parto e "
            "menopausa fitness — sem abandonar musculação.",
        ]
    if g == "masculino":
        return [
            f"Grade e comunicação com viés masculino (público {pct} na faixa-alvo): "
            "musculação/performance, funcional/HIIT, lutas e recovery — sem excluir misto.",
        ]
    return []
