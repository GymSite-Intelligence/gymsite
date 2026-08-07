"""Matriz demografia × saturação → modelo adequado (compute puro).

Tier + mix (Task 1). Quadrante em Task 2.
"""
from __future__ import annotations

from typing import Any, Literal

from tools.bairro_normalize import fold_texto
from tools.parametros_metodologia import param

Tier = Literal["low", "mid", "premium", "nicho", "desconhecido"]

REDES_TIER: dict[str, Tier] = {
    "smart fit": "low",
    "smartfit": "low",
    "selfit": "low",
    "bluefit": "low",
    "blue fit": "low",
    "skyfit": "low",
    "sky fit": "low",
    "bodytech": "premium",
    "body tech": "premium",
    "bio ritmo": "premium",
    "bioritmo": "premium",
    "cia athletica": "premium",
    "competition": "premium",
}

_MIX_KEYS = ("low", "mid", "premium", "nicho", "desconhecido")


def _ticket_from(c: dict[str, Any]) -> float | None:
    raw = c.get("ticket_medio")
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    planos = c.get("planos_precos")
    if isinstance(planos, list) and planos:
        vals: list[float] = []
        for p in planos:
            if isinstance(p, dict):
                for k in ("preco", "price", "valor", "mensalidade"):
                    if p.get(k) is not None:
                        try:
                            vals.append(float(p[k]))
                        except (TypeError, ValueError):
                            pass
            elif isinstance(p, (int, float)):
                vals.append(float(p))
        if vals:
            return sum(vals) / len(vals)
    return None


def _tier_rede(nome_fold: str) -> Tier | None:
    if not nome_fold:
        return None
    # Longer keys first so "blue fit" wins over accidental short matches
    for chave in sorted(REDES_TIER.keys(), key=len, reverse=True):
        if chave in nome_fold:
            return REDES_TIER[chave]
    return None


def classificar_tier_concorrente(c: dict[str, Any]) -> Tier:
    nome = c.get("nome") or c.get("title") or ""
    nome_fold = fold_texto(str(nome))
    rede = _tier_rede(nome_fold)
    if rede is not None:
        return rede

    ticket = _ticket_from(c)
    if ticket is None:
        return "desconhecido"
    low_max = float(param("matriz_ticket_low_max"))
    prem_min = float(param("matriz_ticket_premium_min"))
    if ticket <= low_max:
        return "low"
    if ticket >= prem_min:
        return "premium"
    return "mid"


def contar_mix(concorrentes: list[dict[str, Any]] | None) -> dict[str, int]:
    out = {k: 0 for k in _MIX_KEYS}
    for c in concorrentes or []:
        if not isinstance(c, dict):
            continue
        tier = classificar_tier_concorrente(c)
        out[tier] = out.get(tier, 0) + 1
    return out


def _rating_medio(concorrentes: list[dict[str, Any]]) -> float | None:
    vals: list[float] = []
    for c in concorrentes:
        raw = c.get("rating")
        if raw is None:
            continue
        try:
            vals.append(float(raw))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return sum(vals) / len(vals)


def _alta_renda(
    renda_percentil: float | None,
    renda_pc: float | None,
) -> bool:
    lim_pct = float(param("matriz_renda_alta_percentil"))
    lim_pc = float(param("matriz_renda_pc_alta_min"))
    if renda_percentil is not None and float(renda_percentil) >= lim_pct:
        return True
    if renda_pc is not None and float(renda_pc) >= lim_pc:
        return True
    return False


_ACAO = {
    "Oceano Azul": "Espaço para Premium/Mid-High: renda alta com pouca pressão premium.",
    "Armadilha de Renda": "Não abrir Premium genérico: ≥2 Premium no polígono — nicho ou Mid-High.",
    "Guerra de Preço": "Praça low saturada: Low ultra-eficiente ou nicho; evitar Mid genérico.",
    "Deserto Viável": "Oferta baixa — validar por que vazio antes de investir pesado.",
}


def matriz_demo_saturacao(
    *,
    populacao: int | None,
    renda_pc: float | None = None,
    renda_percentil: float | None = None,
    concorrentes: list[dict] | None = None,
    censo_base: str | None = None,
    fonte_espacial: str | None = None,
    baixas_24m: int | None = None,
    rede_ancora: bool | None = None,
) -> dict[str, Any]:
    cs = [c for c in (concorrentes or []) if isinstance(c, dict)]
    n = len(cs)
    mix = contar_mix(cs)
    rating_medio = _rating_medio(cs)

    pop = int(populacao) if populacao is not None else 0
    n_per_10k: float | None
    if pop > 0:
        n_per_10k = n / (pop / 10000.0)
    else:
        n_per_10k = None

    alta = _alta_renda(renda_percentil, renda_pc)
    baixo = float(param("matriz_n_per_10k_baixo"))
    alto = float(param("matriz_n_per_10k_alto"))
    prem_min = int(param("matriz_premium_min_armadilha"))
    fraco = float(param("matriz_rating_fraco_max"))

    # W3: âncora nacional + ≥1 Premium → bump pressão até limiar Armadilha
    premium_eff = mix.get("premium", 0)
    if rede_ancora and alta and premium_eff >= 1:
        premium_eff = max(premium_eff, prem_min)

    if alta and premium_eff >= prem_min:
        quadrante = "Armadilha de Renda"
        modelo = "nicho_ou_mid_high"
    elif alta and (
        n_per_10k is None
        or n_per_10k < baixo
        or (mix.get("premium", 0) == 0 and rating_medio is not None and rating_medio < fraco)
    ):
        quadrante = "Oceano Azul"
        modelo = "premium_ou_mid_high"
    elif (
        (not alta)
        and n_per_10k is not None
        and n_per_10k >= alto
        and mix.get("low", 0) >= max(2, n // 2)
    ):
        quadrante = "Guerra de Preço"
        modelo = "low_ou_nicho"
    else:
        quadrante = "Deserto Viável"
        modelo = "teste_leve"

    red_flag_rotatividade = False
    # W3: baixas altas + N baixo → força Deserto (não sobrescreve Armadilha)
    if (
        baixas_24m is not None
        and int(baixas_24m) >= 3
        and (n_per_10k is None or n_per_10k < baixo)
        and quadrante != "Armadilha de Renda"
    ):
        quadrante = "Deserto Viável"
        modelo = "teste_leve"
        red_flag_rotatividade = True

    fonte = fonte_espacial or "raio_fallback"
    n10_txt = f"{n_per_10k:.2f}" if n_per_10k is not None else "n/d"
    carimbo = (
        f"{quadrante} · N={n} ({n10_txt}/10k) · "
        f"{fonte} · {censo_base or 'censo_n/d'}"
    )
    acao = _ACAO[quadrante]
    if red_flag_rotatividade:
        acao = (
            f"{acao} Red flag CNPJ: ≥{baixas_24m} baixas em 24m com oferta baixa."
        )

    out: dict[str, Any] = {
        "quadrante": quadrante,
        "modelo_sugerido": modelo,
        "n_poligono": n,
        "n_per_10k": n_per_10k,
        "mix": mix,
        "rating_medio": rating_medio,
        "censo_base": censo_base,
        "fonte_espacial": fonte,
        "acao_estrategica": acao,
        "carimbo": carimbo,
    }
    if baixas_24m is not None:
        out["baixas_24m"] = int(baixas_24m)
        out["red_flag_rotatividade"] = red_flag_rotatividade
    if rede_ancora is not None:
        out["rede_ancora"] = bool(rede_ancora)
    return out


def _concorrentes_from_state(state: dict[str, Any]) -> tuple[list[dict], str]:
    """Prefer PIP-gated list; else all + raio_fallback."""
    brutos = state.get("concorrentes_brutos")
    if isinstance(brutos, str):
        try:
            import json

            brutos = json.loads(brutos)
        except Exception:
            brutos = None
    pool: list[dict] = []
    if isinstance(brutos, list):
        pool = [c for c in brutos if isinstance(c, dict)]
    if not pool:
        ic = state.get("inteligencia_competitiva")
        if isinstance(ic, str):
            try:
                import json

                ic = json.loads(ic)
            except Exception:
                ic = None
        if isinstance(ic, dict):
            inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
            if isinstance(inner, dict):
                for key in ("concorrentes_detalhados", "concorrentes"):
                    raw = inner.get(key)
                    if isinstance(raw, list):
                        pool = [c for c in raw if isinstance(c, dict)]
                        if pool:
                            break

    pip = [c for c in pool if c.get("gate_espacial") == "poligono_ibge_bairro"]
    if pip:
        return pip, "poligono_ibge_bairro"
    return pool, "raio_fallback"


def concorrentes_espaciais_from_state(state: dict[str, Any]) -> tuple[list[dict], str]:
    """Public alias for PIP-preferring competitor list (Absorção / Matriz)."""
    return _concorrentes_from_state(state)


def attach_matriz_demo_saturacao(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any] | None:
    """A9 hook: compute matriz into parsed. Armadilha + OCEANO → matriz_override."""
    demo = state.get("demografia_bairro") if isinstance(state.get("demografia_bairro"), dict) else {}
    hr = parsed.get("headroom_renda") if isinstance(parsed.get("headroom_renda"), dict) else {}

    pop = demo.get("populacao")
    if pop is None and hr.get("populacao") is not None:
        pop = hr.get("populacao")

    renda_pc = hr.get("renda_pc")
    if renda_pc is None:
        renda_pc = demo.get("renda_media_per_capita") or demo.get("renda_media") or demo.get("renda_pc")
    renda_percentil = hr.get("renda_percentil")

    cs, fonte = _concorrentes_from_state(state)
    censo_base = demo.get("censo_base") or fonte

    baixas_24m, rede_ancora = _cnpj_modifiers_from_state(state)

    result = matriz_demo_saturacao(
        populacao=int(pop) if pop is not None else None,
        renda_pc=float(renda_pc) if renda_pc is not None else None,
        renda_percentil=float(renda_percentil) if renda_percentil is not None else None,
        concorrentes=cs,
        censo_base=str(censo_base) if censo_base else None,
        fonte_espacial=fonte,
        baixas_24m=baixas_24m,
        rede_ancora=rede_ancora,
    )
    parsed["matriz_demo_saturacao"] = result

    veredito = str(parsed.get("veredito_posicionamento") or "").upper()
    if result.get("quadrante") == "Armadilha de Renda" and "OCEANO" in veredito:
        parsed["matriz_override"] = True
    return result


def _cnpj_modifiers_from_state(state: dict[str, Any]) -> tuple[int | None, bool | None]:
    """Pull baixas_24m / rede_ancora from market_context / arvore if present."""
    baixas: int | None = None
    ancora: bool | None = None
    mc = state.get("market_context")
    if isinstance(mc, str):
        try:
            import json

            mc = json.loads(mc)
        except Exception:
            mc = None
    if isinstance(mc, dict):
        inner = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
        if isinstance(inner, dict):
            arv = inner.get("arvore_2x2") or inner.get("arvore_2x2_parque") or {}
            if isinstance(arv, dict):
                for k in ("baixas_24m", "baixas_bairro_24m", "baixas_q"):
                    if arv.get(k) is not None:
                        try:
                            baixas = int(arv[k])
                            break
                        except (TypeError, ValueError):
                            pass
            for k in ("baixas_cnpj_24m", "baixas_24m"):
                if inner.get(k) is not None and baixas is None:
                    try:
                        baixas = int(inner[k])
                    except (TypeError, ValueError):
                        pass
            if "rede_ancora" in inner:
                ancora = bool(inner.get("rede_ancora"))
            elif "rede_ancora_presente" in inner:
                ancora = bool(inner.get("rede_ancora_presente"))
    # Heurística: qualquer Bodytech/Bio/Smart no mix = âncora possível
    if ancora is None:
        cs, _ = _concorrentes_from_state(state)
        nomes = " ".join(fold_texto(str(c.get("nome") or "")) for c in cs)
        ancora = any(
            k in nomes
            for k in ("smart fit", "smartfit", "bodytech", "bio ritmo", "bioritmo")
        ) if cs else None
    return baixas, ancora
