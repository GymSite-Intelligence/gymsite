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


def classificar_perfil_bairro(
    renda_media_pc: float | None = None,
    idh_renda: float | None = None,
) -> dict[str, Any]:
    """Deriva perfil 'ab' | 'geral' da renda REAL do bairro (regra de ouro).

    'ab' (penetração fitness segmentada, ~10%) quando o bairro é alta renda; senão
    'geral' (~4,5%). Ordem de confiança: IDH-Renda (CKAN/Atlas) > renda per capita >
    sem dado (fallback 'geral' rotulado). Cortes via param() — recalibráveis.

    Retorna {perfil, base, confianca, fonte} — exposto no relatório (auditável).
    """
    from tools.parametros_metodologia import param

    idh_min = param("perfil_ab_idh_renda_min")
    renda_min = param("perfil_ab_renda_pc_min")

    if idh_renda is not None and float(idh_renda) >= idh_min:
        return {"perfil": "ab", "base": "idh_renda", "confianca": "alta",
                "fonte": f"CKAN IDH-Renda {float(idh_renda):.3f} ≥ {idh_min:.3f} (alta renda A/B)"}
    if renda_media_pc is not None and float(renda_media_pc) >= renda_min:
        return {"perfil": "ab", "base": "renda_per_capita", "confianca": "media",
                "fonte": f"renda per capita R$ {float(renda_media_pc):.0f} ≥ R$ {renda_min:.0f} (A/B)"}
    if idh_renda is None and renda_media_pc is None:
        return {"perfil": "geral", "base": "sem_dado_renda", "confianca": "baixa",
                "fonte": "renda do bairro indisponível — penetração geral (fallback rotulado)"}
    return {"perfil": "geral", "base": "renda_abaixo_ab", "confianca": "media",
            "fonte": "renda/IDH do bairro abaixo do corte A/B — penetração geral"}


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

    from tools.bairro_normalize import resolver_bairro_canonico, sanity_renda_geocode

    bairro_in = (bairro or "").strip()
    bairro_geo = resolver_bairro_canonico(bairro_in, uf=uf or "", cidade=cidade or "")
    if bairro_geo and bairro_geo != bairro_in:
        out["bairro"] = bairro_geo
        out["bairro_alias_de"] = bairro_in

    # Renda — tabela nacional usa nomes curtos (ex.: "Lagoa"); geocode usa o canônico longo.
    try:
        from tools.bairro_renda_loader import enrich_demografia_bairro

        b = (enrich_demografia_bairro({}, cidade, bairro_in or bairro_geo, uf).get("bairro") or {})
        if not b.get("renda_media") and bairro_geo != bairro_in:
            b = (enrich_demografia_bairro({}, cidade, bairro_geo, uf).get("bairro") or {})
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

        geo = geocode_endereco(f"{bairro_geo}, {cidade}, {uf or ''}, Brasil".replace(" ,", ","))
        lat, lng = geo.get("lat"), geo.get("lng")
        # id_municipio às vezes não chega do A6 (market_context sem codigo_ibge) — sem ele o
        # perfil idade×sexo por setor vinha None. Resolve via IBGE (cidade, uf).
        if not id_municipio:
            try:
                from tools.ibge_tools import buscar_municipio

                _mun = buscar_municipio(cidade, uf or "")
                id_municipio = (_mun or {}).get("codigo") or id_municipio
            except Exception:
                pass
        if lat is not None and lng is not None:
            from tools.bairro_poligono import resolver_bairro_poligono
            from tools.censo_setor_tools import demografia_setor_censo, demografia_setor_poligono
            from tools.perfil_sexo_idade_tools import (
                perfil_sexo_idade_bairro,
                perfil_sexo_idade_poligono,
            )

            poly = resolver_bairro_poligono(
                id_municipio=id_municipio, bairro=bairro_geo, cidade=cidade, uf=uf,
            )
            ring = poly.get("ring") if poly else None
            if ring:
                censo = demografia_setor_poligono(id_municipio, ring)
                if censo:
                    out["populacao"] = censo.get("populacao")
                    out["domicilios"] = censo.get("domicilios")
                    out["media_moradores"] = censo.get("media_moradores")
                    out["populacao_fonte"] = censo.get("fonte")
                    out["censo_n_setores"] = censo.get("n_setores")
                    out["censo_base"] = "poligono_ibge_bairro"
                    out["censo_cd_bairro"] = poly.get("cd_bairro") if poly else None
                    out["censo_raio_m"] = None
                try:
                    perfil_bairro = perfil_sexo_idade_poligono(id_municipio, ring)
                    if perfil_bairro:
                        out["perfil_idade_sexo_bairro"] = perfil_bairro
                except Exception as exc:
                    logger.warning(
                        "demografia_bairro perfil polígono falhou: %s: %s",
                        type(exc).__name__, exc,
                    )
            else:
                censo = demografia_setor_censo(lat, lng, id_municipio=id_municipio)
                if censo:
                    out["populacao"] = censo.get("populacao")
                    out["domicilios"] = censo.get("domicilios")
                    out["media_moradores"] = censo.get("media_moradores")
                    out["populacao_fonte"] = censo.get("fonte")
                    out["censo_n_setores"] = censo.get("n_setores")
                    out["censo_raio_m"] = censo.get("raio_m")
                    out["censo_base"] = "raio_fallback"
                try:
                    _pop = out.get("populacao") or (censo or {}).get("populacao")
                    perfil_bairro = perfil_sexo_idade_bairro(id_municipio, lat, lng, _pop)
                    if perfil_bairro:
                        out["perfil_idade_sexo_bairro"] = perfil_bairro
                except Exception as exc:
                    logger.warning(
                        "demografia_bairro perfil idade×sexo falhou: %s: %s",
                        type(exc).__name__, exc,
                    )

    except Exception as exc:
        logger.warning("demografia_bairro Censo falhou: %s: %s", type(exc).__name__, exc)

    alerta = sanity_renda_geocode(out.get("renda_media"), bairro_geo, uf=uf or "")
    if alerta:
        logger.warning("demografia_bairro sanity: %s", alerta)
        out["sanity_alert"] = alerta

    return out
