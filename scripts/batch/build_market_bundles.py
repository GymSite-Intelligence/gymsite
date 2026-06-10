#!/usr/bin/env python3
"""
Compõe market_bundle.json por cidade/bairro/uf.

Combina: enrichment cache (OSM, portais, BCB), IBGE (A2), CKAN catalog, sector_listed.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _build_demografia(cidade: str, bairro: str, uf: str) -> dict:
    from tools.ibge_tools import analise_demografica_completa
    from tools.bairro_renda_loader import enrich_demografia_bairro

    demo = analise_demografica_completa(cidade, uf)
    municipio = {
        "populacao_total": demo.get("populacao_total"),
        "populacao_faixa_18_45": demo.get("populacao_faixa_18_45"),
        "renda_media_domiciliar": demo.get("renda_media_domiciliar"),
        "renda_granularidade": demo.get("renda_granularidade", "municipal"),
        "codigo_ibge": demo.get("codigo_ibge"),
        "fonte": demo.get("fonte_renda", "ibge_tools"),
        "score_demografico": demo.get("score_demografico"),
    }
    if demo.get("erro"):
        municipio["aviso"] = demo.get("erro")
    base = {
        "municipio": municipio,
        "bairro": {
            "renda_media": None,
            "populacao": None,
            "granularidade": "bairro",
            "fonte": None,
            "dataset_id": None,
        },
    }
    return enrich_demografia_bairro(base, cidade, bairro, uf)


def _load_or_build_enrichment(
    cidade: str,
    bairro: str,
    uf: str,
    area_min: int,
    area_max: int,
    *,
    refresh: bool,
) -> dict:
    from tools.enrichment_cache import load_cache_file, cache_is_fresh

    cache = load_cache_file(cidade, bairro, uf)
    if cache and cache_is_fresh(cache) and not refresh:
        return cache

    from scripts.enrichment.cache_enrichment import build_cache

    return build_cache(cidade, bairro, uf, area_min, area_max)


def _capex_indices_block(uf: str) -> dict:
    try:
        from tools.sinapi_indices import capex_indices_for_uf

        return capex_indices_for_uf(uf)
    except Exception:
        return {"uf": uf.upper(), "fonte_obra": "benchmark_fixo_fase_a"}


def _ckan_catalog(cidade: str, uf: str, *, skip_network: bool) -> dict:
    if skip_network:
        return {"portais_consultados": [], "datasets_matched": [], "skipped": True}
    try:
        from tools.ckan_client import search_datasets_for_city

        datasets = search_datasets_for_city(cidade, uf)
        return {
            "portais_consultados": ["https://dados.gov.br"],
            "datasets_matched": datasets,
        }
    except Exception as exc:
        return {
            "portais_consultados": ["https://dados.gov.br"],
            "datasets_matched": [],
            "erro": str(exc),
        }


def build_bundle(
    cidade: str,
    bairro: str,
    uf: str,
    *,
    area_min: int = 800,
    area_max: int = 1500,
    refresh_enrichment: bool = False,
    skip_ckan: bool = False,
) -> dict:
    from tools.cvm_listed_metrics import obter_sector_listed
    from tools.ibge_tools import buscar_municipio

    mun = buscar_municipio(cidade, uf) or {}
    enrichment = _load_or_build_enrichment(
        cidade, bairro, uf, area_min, area_max, refresh=refresh_enrichment
    )
    demografia = _build_demografia(cidade, bairro, uf)

    missing: list[str] = []
    if demografia.get("bairro", {}).get("renda_media") is None and (bairro or "").strip():
        missing.append("renda_media_bairro")

    aluguel = enrichment.get("aluguel_portais") or {}
    if not aluguel.get("n_validos"):
        missing.append("aluguel_medio_m2")

    comp = enrichment.get("competicao_local") or {}
    if comp.get("status") != "ok":
        missing.append("competicao_osm")

    from tools.franchise_curated import bloco_para_bundle
    from tools.legal_fees_loader import bloco_para_bundle as legal_bloco
    from tools.market_bundle import compute_bundle_stale

    valido = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {
        "version": "1.0",
        "local": {
            "cidade": cidade,
            "bairro": bairro or None,
            "uf": uf.upper(),
            "codigo_ibge_municipio": mun.get("codigo"),
        },
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "valido_ate": valido.isoformat(timespec="seconds"),
        "ckan_catalog": _ckan_catalog(cidade, uf, skip_network=skip_ckan),
        "demografia": demografia,
        "sector_benchmarks": obter_sector_listed(),
        "competicao_local": enrichment.get("competicao_local"),
        "aluguel_portais": enrichment.get("aluguel_portais"),
        "bcb_imobiliario": enrichment.get("bcb_imobiliario"),
        "capex_indices": _capex_indices_block(uf),
        "franquias_referencia": bloco_para_bundle(),
        "legal_fees": legal_bloco(cidade, uf),
        "missing_fields": missing,
    }
    stale, stale_reasons = compute_bundle_stale(payload)
    payload["stale"] = stale
    payload["stale_reasons"] = stale_reasons
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cidade", required=True)
    p.add_argument("--bairro", default="")
    p.add_argument("--uf", default="CE")
    p.add_argument("--area-min", type=int, default=800)
    p.add_argument("--area-max", type=int, default=1500)
    p.add_argument("--refresh-enrichment", action="store_true")
    p.add_argument("--skip-ckan", action="store_true")
    args = p.parse_args()

    bundle = build_bundle(
        args.cidade,
        args.bairro,
        args.uf,
        area_min=args.area_min,
        area_max=args.area_max,
        refresh_enrichment=args.refresh_enrichment,
        skip_ckan=args.skip_ckan,
    )
    from tools.market_bundle import save_market_bundle

    path = save_market_bundle(args.cidade, args.bairro, args.uf, bundle)
    print("written:", path)
    print("missing_fields:", bundle.get("missing_fields"))
    print("codigo_ibge:", (bundle.get("local") or {}).get("codigo_ibge_municipio"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
