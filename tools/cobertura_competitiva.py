"""B1+B2 — cobertura competitiva da praça gated + validação de gaps universais.

B1: todo gated entra em `oferta_por_gated`; deep preserva oferta; mapeado mínimo.
Denominador do mapa = gated COM oferta (`n_com_oferta`), não `gated_n` cru.

B2: serviço universal com cobertura amostral < limiar → artefato (fora do ERRC);
nichos (natação/crossfit/kids) permanecem CRIAR reais.

Fail-soft: erro → None / lista vazia — nunca quebra o pipeline.
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# Espelha agents/a9_positioning_strategist._SERVICOS_CATALOGO (rótulos canônicos).
_SERVICOS_CATALOGO = {
    "musculacao": "Musculação",
    "funcional": "Treino funcional/HIIT",
    "danca": "Aulas de dança",
    "spinning": "Spinning",
    "lutas": "Artes marciais",
    "yoga": "Yoga/Pilates",
    "pilates": "Yoga/Pilates",
    "crossfit": "Crossfit",
    "piscina": "Natação/Hidro",
    "nutricao": "Nutrição integrada",
    "avaliacao": "Avaliação física",
    "personal": "Personal (PT)",
    "recovery": "Recovery/fisioterapia",
    "estetica": "Sauna/estética",
    "area_kids": "Aulas/espaço kids",
}


def _norm_pid(v: Any) -> str:
    return str(v or "").strip()


def _norm_nome(v: Any) -> str:
    return str(v or "").strip().lower()


def _unwrap_oferta(oferta_concorrentes: Any) -> dict:
    if isinstance(oferta_concorrentes, str):
        try:
            import json

            oferta_concorrentes = json.loads(oferta_concorrentes)
        except Exception:
            return {}
    if not isinstance(oferta_concorrentes, dict):
        return {}
    inner = oferta_concorrentes.get("oferta_concorrentes")
    if isinstance(inner, dict):
        return inner
    return oferta_concorrentes


def _rotulos_de_chaves(chaves: Any) -> set[str]:
    out: set[str] = set()
    if not isinstance(chaves, (list, tuple, set)):
        return out
    for k in chaves:
        kk = str(k or "").strip().lower()
        if kk in _SERVICOS_CATALOGO:
            out.add(_SERVICOS_CATALOGO[kk])
        elif k and str(k).strip() in set(_SERVICOS_CATALOGO.values()):
            out.add(str(k).strip())
    return out


def _servicos_de_oferta_blob(blob: dict | None) -> tuple[list[str], list[str]]:
    """Retorna (servicos_rotulos, fontes) a partir de oferta_mapeada / oferta_concorrentes."""
    if not isinstance(blob, dict):
        return [], []
    svcs = _rotulos_de_chaves(blob.get("modalidades") or blob.get("servicos") or [])
    fontes: list[str] = []
    raw_f = blob.get("fontes")
    if isinstance(raw_f, list):
        fontes = [str(x) for x in raw_f if x]
    elif isinstance(raw_f, str) and raw_f.strip():
        fontes = [raw_f.strip()]
    return sorted(svcs), fontes


def _servicos_do_deep(c: dict) -> tuple[list[str], list[str]]:
    """Une oferta_mapeada + chaves já no dict deep (servicos_oferecidos / ig)."""
    svcs: set[str] = set()
    fontes: list[str] = []
    om = c.get("oferta_mapeada") if isinstance(c.get("oferta_mapeada"), dict) else None
    if om:
        s, f = _servicos_de_oferta_blob(om)
        svcs |= set(s)
        fontes.extend(f)
    svcs |= _rotulos_de_chaves(c.get("servicos_oferecidos") or [])
    svcs |= _rotulos_de_chaves(c.get("servicos_ig") or [])
    if svcs and "deep" not in fontes:
        fontes.append("competitors_set")
    return sorted(svcs), fontes


def _index_deep(competitors_set: list[dict]) -> dict[str, dict]:
    by_pid: dict[str, dict] = {}
    for c in competitors_set or []:
        if not isinstance(c, dict):
            continue
        pid = _norm_pid(c.get("place_id") or c.get("id"))
        if pid:
            by_pid[pid] = c
    return by_pid


def _lookup_oferta(
    oferta_inner: dict, place_id: str, nome: str
) -> dict | None:
    if not oferta_inner:
        return None
    pid = _norm_pid(place_id)
    if pid and pid in oferta_inner and isinstance(oferta_inner[pid], dict):
        return oferta_inner[pid]
    nn = _norm_nome(nome)
    if nn:
        for k, v in oferta_inner.items():
            if not isinstance(v, dict):
                continue
            if _norm_nome(k) == nn or _norm_nome(v.get("nome")) == nn:
                return v
    return None


def montar_cobertura_competitiva(
    *,
    no_bairro: list[dict] | None,
    competitors_set: list[dict] | None = None,
    oferta_concorrentes: Any = None,
) -> dict | None:
    """B1: monta `cobertura_competitiva` a partir do gate + deep + oferta minerada.

    Fail-soft: qualquer erro → None.
    """
    try:
        gated = [g for g in (no_bairro or []) if isinstance(g, dict)]
        if not gated:
            return {
                "gated_n": 0,
                "n_com_oferta": 0,
                "cobertura_amostral": 0.0,
                "oferta_por_gated": {},
                "fonte": "cobertura_competitiva_b1",
            }

        deep_by_pid = _index_deep(list(competitors_set or []))
        oferta_inner = _unwrap_oferta(oferta_concorrentes)
        oferta_por_gated: dict[str, dict] = {}

        for g in gated:
            pid = _norm_pid(g.get("place_id") or g.get("id"))
            nome = str(g.get("nome") or g.get("name") or "").strip()
            key = pid or f"nome:{_norm_nome(nome)}"
            deep = deep_by_pid.get(pid) if pid else None
            # Flag `deep` no gate (cross_check) OU presença no competitors_set.
            is_analisado = bool(deep) or bool(g.get("deep"))

            servicos: list[str] = []
            fontes: list[str] = []
            if deep:
                servicos, fontes = _servicos_do_deep(deep)
            if not servicos:
                blob = _lookup_oferta(oferta_inner, pid, nome)
                s2, f2 = _servicos_de_oferta_blob(blob)
                if s2:
                    servicos = s2
                    fontes = list(dict.fromkeys([*(fontes or []), *f2, "oferta_concorrentes"]))

            oferta_por_gated[key] = {
                "nome": nome,
                "place_id": pid or None,
                "servicos": servicos,
                "fontes": fontes,
                "profundidade": "analisado" if is_analisado else "mapeado",
            }

        n_com = sum(1 for v in oferta_por_gated.values() if v.get("servicos"))
        gated_n = len(oferta_por_gated)
        return {
            "gated_n": gated_n,
            "n_com_oferta": n_com,
            "cobertura_amostral": round(n_com / gated_n, 4) if gated_n else 0.0,
            "oferta_por_gated": oferta_por_gated,
            "fonte": "cobertura_competitiva_b1",
        }
    except Exception:
        logger.warning("montar_cobertura_competitiva falhou", exc_info=True)
        return None


def montar_cobertura_from_state(state: dict) -> dict | None:
    """Conveniência: lê gate/deep/oferta do state ou do consolidado já montado."""
    try:
        aneis = state.get("aneis_competitivos")
        if not isinstance(aneis, dict):
            oc = state.get("output_consolidado")
            if isinstance(oc, dict):
                aneis = oc.get("aneis_competitivos")
        cc = (aneis or {}).get("cross_check") if isinstance(aneis, dict) else None
        no_bairro = (cc or {}).get("no_bairro") if isinstance(cc, dict) else None

        competitors_set = state.get("competitors_set")
        if not isinstance(competitors_set, list):
            oc = state.get("output_consolidado") if isinstance(state.get("output_consolidado"), dict) else {}
            competitors_set = oc.get("competitors_set") if isinstance(oc, dict) else None
            if not isinstance(competitors_set, list):
                # Fallback: detalhados da inteligência competitiva
                from tools.competitor_tools import _parse_market_context

                ic = _parse_market_context(state.get("inteligencia_competitiva"))
                inner = (
                    ic.get("inteligencia_competitiva")
                    if isinstance(ic.get("inteligencia_competitiva"), dict)
                    else ic
                )
                competitors_set = (
                    (inner.get("concorrentes_detalhados") or [])
                    if isinstance(inner, dict)
                    else []
                )

        return montar_cobertura_competitiva(
            no_bairro=list(no_bairro or []),
            competitors_set=list(competitors_set or []),
            oferta_concorrentes=state.get("oferta_concorrentes"),
        )
    except Exception:
        logger.warning("montar_cobertura_from_state falhou", exc_info=True)
        return None


def mapa_servicos_da_cobertura(cobertura: dict | None) -> tuple[dict, Counter]:
    """Penetração por rótulo do catálogo; `de` = n_com_oferta."""
    universo = sorted(set(_SERVICOS_CATALOGO.values()))
    if not isinstance(cobertura, dict):
        return {s: {"oferecem": 0, "de": 0, "penetracao_pct": 0} for s in universo}, Counter()

    por = cobertura.get("oferta_por_gated") or {}
    com_oferta = [v for v in por.values() if isinstance(v, dict) and v.get("servicos")]
    n = int(cobertura.get("n_com_oferta") or len(com_oferta) or 0)
    pen: Counter = Counter()
    for v in com_oferta:
        for s in v.get("servicos") or []:
            if s in set(_SERVICOS_CATALOGO.values()):
                pen[s] += 1
    mapa = {
        s: {
            "oferecem": pen.get(s, 0),
            "de": n,
            "penetracao_pct": round(100 * pen.get(s, 0) / n) if n else 0,
        }
        for s in universo
    }
    return mapa, pen


def filtrar_gaps_universais(
    gaps: list[str] | None,
    *,
    cobertura: dict | None,
    limiar: float | None = None,
    universais: list[str] | None = None,
    nichos: list[str] | None = None,
) -> list[dict]:
    """B2: classifica gaps em real vs artefato_cobertura.

    `cobertura_amostral` = n_com_oferta / gated_n (não penetração do serviço).
    """
    try:
        from tools.parametros_metodologia import param, param_list

        if limiar is None:
            limiar = float(param("limiar_cobertura_gap"))
        if universais is None:
            universais = param_list("servicos_universais")
        if nichos is None:
            nichos = param_list("servicos_nicho_gap")
    except Exception:
        limiar = 0.60 if limiar is None else limiar
        universais = universais or [
            "Musculação", "Spinning", "Treino funcional/HIIT", "Personal (PT)", "Yoga/Pilates",
        ]
        nichos = nichos or ["Natação/Hidro", "Crossfit", "Aulas/espaço kids"]

    univ = {str(x) for x in universais}
    nich = {str(x) for x in nichos}
    cov_ratio = float((cobertura or {}).get("cobertura_amostral") or 0.0)
    gated_n = int((cobertura or {}).get("gated_n") or 0)
    n_com = int((cobertura or {}).get("n_com_oferta") or 0)
    if gated_n > 0 and not cov_ratio and n_com:
        cov_ratio = n_com / gated_n

    out: list[dict] = []
    for g in gaps or []:
        servico = str(g).strip()
        if not servico:
            continue
        if servico in nich:
            out.append({
                "gap": f"{servico} — nenhum concorrente da praça anuncia (oportunidade de CRIAR)",
                "servico": servico,
                "tipo": "real",
                "confianca": "media",
                "incluir_no_errc": True,
                "cobertura_amostral": cov_ratio,
            })
            continue
        if servico in univ:
            if cov_ratio < float(limiar):
                out.append({
                    "gap": (
                        f"{servico} — artefato de cobertura "
                        f"(oferta mapeada em {n_com}/{gated_n} gated, "
                        f"amostra {cov_ratio:.0%} < limiar {float(limiar):.0%})"
                    ),
                    "servico": servico,
                    "tipo": "artefato_cobertura",
                    "confianca": "baixa",
                    "incluir_no_errc": False,
                    "cobertura_amostral": cov_ratio,
                })
            else:
                out.append({
                    "gap": f"{servico} — nenhum concorrente da praça anuncia (oportunidade de CRIAR)",
                    "servico": servico,
                    "tipo": "real",
                    "confianca": "alta",
                    "incluir_no_errc": True,
                    "cobertura_amostral": cov_ratio,
                })
            continue
        out.append({
            "gap": f"{servico} — nenhum concorrente da praça anuncia (oportunidade de CRIAR)",
            "servico": servico,
            "tipo": "real",
            "confianca": "media",
            "incluir_no_errc": True,
            "cobertura_amostral": cov_ratio,
        })
    return out


def aplicar_cobertura_no_posicionamento(state: dict, parsed: dict) -> None:
    """Ponto único: preenche mapa_servicos + gaps_* a partir de cobertura_competitiva."""
    try:
        cov = state.get("cobertura_competitiva")
        if not isinstance(cov, dict) or not cov.get("oferta_por_gated"):
            cov = montar_cobertura_from_state(state)
            if isinstance(cov, dict):
                state["cobertura_competitiva"] = cov
        if not isinstance(cov, dict) or not cov.get("oferta_por_gated"):
            return

        mapa, pen = mapa_servicos_da_cobertura(cov)
        n = int(cov.get("n_com_oferta") or 0)
        gaps_brutos = (
            sorted(s for s in set(_SERVICOS_CATALOGO.values()) if pen.get(s, 0) == 0)
            if n else []
        )
        validados = filtrar_gaps_universais(gaps_brutos, cobertura=cov)
        para_errc = [g for g in validados if g.get("incluir_no_errc")]
        suprimidos = [g for g in validados if not g.get("incluir_no_errc")]

        parsed["mapa_servicos"] = mapa
        parsed["gaps_validados"] = validados
        parsed["gaps_suprimidos"] = suprimidos
        parsed["gaps_identificados"] = (
            [g["gap"] for g in para_errc]
            if para_errc
            else (
                ["Mercado coberto nos serviços-núcleo — foco em AUMENTAR/REDUZIR (qualidade/preço), não em CRIAR"]
                if n
                else parsed.get("gaps_identificados") or []
            )
        )
        parsed["fonte_gaps"] = "deterministico_cobertura_competitiva_b1_b2"
        parsed["cobertura_competitiva_resumo"] = {
            "gated_n": cov.get("gated_n"),
            "n_com_oferta": cov.get("n_com_oferta"),
            "cobertura_amostral": cov.get("cobertura_amostral"),
        }
    except Exception:
        logger.warning("aplicar_cobertura_no_posicionamento falhou", exc_info=True)
