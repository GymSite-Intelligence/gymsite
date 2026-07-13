#!/usr/bin/env python3
"""Cache deterministico de fatos locais (sem LLM) para cidade/bairro."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE_DIR = Path(__file__).resolve().parent / "cache"


def _slug(cidade: str, bairro: str, uf: str) -> str:
    parts = [cidade.strip().lower(), (bairro or "").strip().lower(), uf.strip().lower()]
    return "_".join(p for p in parts if p)


def _cache_key(cidade: str, bairro: str, uf: str, area_min: int, area_max: int) -> str:
    payload = json.dumps(
        {
            "cidade": cidade.strip().lower(),
            "bairro": (bairro or "").strip().lower(),
            "uf": uf.strip().upper(),
            "area_min": area_min,
            "area_max": area_max,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _bcb_resumo(cidade: str, uf: str) -> dict:
    try:
        from tools.bcb_imobiliario_olinda import extrair_resumo_imobiliario
        return extrair_resumo_imobiliario(cidade_contexto=cidade) or {}
    except Exception as exc:
        return {"status": "erro", "motivo": str(exc)}


def build_cache(
    cidade: str,
    bairro: str,
    uf: str,
    area_min: int = 800,
    area_max: int = 1500,
) -> dict:
    from tools.local_market_facts import fatos_competicao_local

    key = _cache_key(cidade, bairro, uf, area_min, area_max)
    competicao = fatos_competicao_local(cidade=cidade, bairro=bairro, uf=uf)
    bcb = _bcb_resumo(cidade, uf)

    out: dict = {
        "cache_key": key,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "local": {"cidade": cidade, "bairro": bairro or None, "uf": uf},
        "parametros": {"area_min_m2": area_min, "area_max_m2": area_max},
        "competicao_local": competicao,
        "bcb_imobiliario": bcb,
    }
    if competicao.get("status") == "ok":
        out["competicao_osm_unidades"] = competicao.get("total_unidades_osm", 0)
        out["redes_detectadas_osm"] = list(competicao.get("redes_detectadas_osm") or [])
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Gera cache deterministico de enrichment local")
    p.add_argument("--cidade", default="Fortaleza")
    p.add_argument("--bairro", default="Meireles")
    p.add_argument("--uf", default="CE")
    p.add_argument("--area-min", type=int, default=800)
    p.add_argument("--area-max", type=int, default=1500)
    args = p.parse_args()

    data = build_cache(args.cidade, args.bairro, args.uf, args.area_min, args.area_max)
    slug = _slug(args.cidade, args.bairro, args.uf)
    out = CACHE_DIR / f"{slug}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("cache_key:", data["cache_key"])
    print("written:", out)
    comp = data.get("competicao_local") or {}
    if comp.get("status") == "ok":
        print("competicao_unidades:", comp.get("total_unidades_osm", 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

