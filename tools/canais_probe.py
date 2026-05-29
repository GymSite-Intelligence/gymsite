"""
Probes síncronos por canal de dados — usados pelos botões Run now e diagnóstico.
"""
from __future__ import annotations

from typing import Any


def probe_places(
    bairro: str,
    cidade: str,
    uf: str = "",
    *,
    raio_metros: int = 3000,
) -> dict[str, Any]:
    from tools.competitor_tools import buscar_academias

    out = buscar_academias(bairro, cidade, raio_metros=raio_metros, uf=uf)
    concorrentes = out.get("concorrentes") or []
    return {
        "canal": "google_places",
        "ok": not out.get("erro") and len(concorrentes) > 0,
        "erro": out.get("erro"),
        "fonte_busca_competidores": out.get("fonte_busca_competidores"),
        "fonte_geocode": out.get("fonte_geocode"),
        "total": len(concorrentes),
        "amostra": concorrentes[:8],
        "raw": out,
    }


def probe_osm(
    bairro: str,
    cidade: str,
    uf: str = "",
    *,
    raio_metros: int = 3000,
) -> dict[str, Any]:
    from tools.maps_tools import geocode_endereco
    from tools.competitor_tools import _buscar_academias_overpass

    endereco = f"{bairro}, {cidade}, Brasil" if bairro else f"{cidade}, Brasil"
    geo = geocode_endereco(endereco)
    if geo.get("error"):
        return {
            "canal": "overpass_osm",
            "ok": False,
            "erro": geo["error"],
            "fonte_geocode": geo.get("fonte_geocode"),
            "total": 0,
            "amostra": [],
        }

    lat, lng = geo["lat"], geo["lng"]
    concorrentes, meta = _buscar_academias_overpass(lat, lng, raio_metros, limit=25)
    return {
        "canal": "overpass_osm",
        "ok": len(concorrentes) > 0,
        "erro": meta.get("erro") if not concorrentes else None,
        "fonte_geocode": geo.get("fonte_geocode"),
        "total": len(concorrentes),
        "amostra": concorrentes[:8],
        "meta": meta,
    }


def probe_cnpj(
    bairro: str,
    cidade: str,
    uf: str = "",
    *,
    limit: int = 25,
) -> dict[str, Any]:
    from tools.cnpj_fitness_tools import listar_unidades_cnpj_no_bairro

    out = listar_unidades_cnpj_no_bairro(cidade, bairro, uf, limit=limit)
    unidades = out.get("unidades") or []
    return {
        "canal": "cnpj_rfb",
        "ok": out.get("status") == "ok" and len(unidades) > 0,
        "erro": out.get("motivo") if out.get("status") != "ok" else None,
        "total": len(unidades),
        "amostra": unidades[:8],
        "raw": out,
    }


def probe_kimi(
    cidade: str,
    bairro: str,
    *,
    tipo_negocio: str = "academia",
    publico_alvo: str = "premium",
    force_refresh: bool = True,
) -> dict[str, Any]:
    from tools.kimi_research import (
        executar_kimi_research_kimi,
        get_last_kimi_tier,
        _openclaw_configured,
    )

    if force_refresh:
        out = executar_kimi_research_kimi(
            cidade, bairro, tipo_negocio=tipo_negocio, publico_alvo=publico_alvo
        )
    else:
        from tools.kimi_research import rodar_kimi_research

        md = rodar_kimi_research(
            cidade,
            bairro,
            tipo_negocio=tipo_negocio,
            publico_alvo=publico_alvo,
        )
        out = {
            "status": "ok",
            "tier": get_last_kimi_tier(),
            "insights_deep_research": md,
            "openclaw_configured": _openclaw_configured(),
        }

    md = out.get("insights_deep_research") or ""
    preview = md[:1200] + ("…" if len(md) > 1200 else "")
    return {
        "canal": "kimi_research",
        "ok": out.get("status") == "ok" and len(md) > 200,
        "tier": out.get("tier"),
        "openclaw_configured": out.get("openclaw_configured"),
        "fontes_count": len(out.get("fontes_verificadas") or []),
        "preview_markdown": preview,
        "confidence_score": out.get("confidence_score"),
        "raw": out,
    }
