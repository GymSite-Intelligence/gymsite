"""
Bloco demografia do BAIRRO — composição determinística de fontes reais.

Renda: CKAN municipal (IDH-Renda → renda per capita Atlas) via bairro_renda_loader.
População/ocupação: IBGE Censo 2022 por setor (espelho Supabase / BQ) via censo_setor_tools.

Sem LLM, sem hardcode: cada campo carrega sua fonte. Usado pelo A6 pra persistir o
bloco no relatório (UI mini-cards). Censo 2022 NÃO tem renda por setor → renda só do CKAN.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def demografia_bairro(
    cidade: str,
    uf: str,
    bairro: str | None,
    *,
    id_municipio: str | None = None,
) -> dict[str, Any]:
    """{renda_media, idh_renda, ranking_idh, populacao, domicilios, media_moradores, fontes}.

    Best-effort: cada fonte que falha fica null (não quebra). Retorna sempre dict com
    granularidade e o que conseguiu — A6 persiste, UI rende o que existir.
    """
    out: dict[str, Any] = {
        "cidade": cidade, "uf": uf, "bairro": bairro, "granularidade": "bairro",
        "renda_media": None, "idh_renda": None, "ranking_idh": None,
        "populacao": None, "domicilios": None, "media_moradores": None,
        "renda_fonte": None, "populacao_fonte": None,
    }
    if not (bairro or "").strip():
        return out

    # Renda — CKAN municipal (IDH-Renda → renda per capita Atlas).
    try:
        from tools.bairro_renda_loader import enrich_demografia_bairro

        b = (enrich_demografia_bairro({}, cidade, bairro, uf).get("bairro") or {})
        out["renda_media"] = b.get("renda_media")
        out["idh_renda"] = b.get("idh_renda")
        out["ranking_idh"] = b.get("ranking_idh")
        out["renda_fonte"] = b.get("fonte")
        out["renda_data_referencia"] = b.get("data_referencia")
    except Exception as exc:
        logger.warning("demografia_bairro renda CKAN falhou: %s: %s", type(exc).__name__, exc)

    # População/ocupação — IBGE Censo 2022 por setor (espelho Supabase → BQ).
    try:
        from tools.censo_setor_tools import demografia_setor_censo
        from tools.maps_tools import geocode_endereco

        geo = geocode_endereco(f"{bairro}, {cidade}, Brasil")
        lat, lng = geo.get("lat"), geo.get("lng")
        if lat is not None and lng is not None:
            censo = demografia_setor_censo(lat, lng, id_municipio=id_municipio)
            if censo:
                out["populacao"] = censo.get("populacao")
                out["domicilios"] = censo.get("domicilios")
                out["media_moradores"] = censo.get("media_moradores")
                out["populacao_fonte"] = censo.get("fonte")
                out["censo_n_setores"] = censo.get("n_setores")
    except Exception as exc:
        logger.warning("demografia_bairro Censo falhou: %s: %s", type(exc).__name__, exc)

    return out
