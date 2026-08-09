#!/usr/bin/env python3
"""Download IBGE Censo 2022 bairros GeoPackage for one UF into data/ibge_bairros/{UF}.gpkg.

No runtime use — batch/ops only. Relatório lê o arquivo local via resolver_bairro_poligono.

Usage:
  .venv/Scripts/python.exe scripts/batch/ingest_ibge_bairros_uf.py --uf CE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

_BASE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/bairros/gpkg/UF"
)
_ROOT = Path(__file__).resolve().parents[2]
_OUT_DIR = _ROOT / "data" / "ibge_bairros"


def _candidate_urls(uf: str) -> list[str]:
    u = uf.upper()
    # IBGE naming varies slightly by release; try common patterns.
    return [
        f"{_BASE}/{u}/{u}_bairros_CD2022.gpkg",
        f"{_BASE}/{u}/BR_bairros_CD2022_{u}.gpkg",
        f"{_BASE}/{u}/bairros_{u}_CD2022.gpkg",
    ]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--uf", required=True, help="UF code, e.g. CE")
    p.add_argument("--url", default="", help="Override download URL")
    args = p.parse_args()
    uf = args.uf.strip().upper()
    if len(uf) != 2:
        print("UF must be 2 letters", file=sys.stderr)
        return 2
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = _OUT_DIR / f"{uf}.gpkg"
    urls = [args.url] if args.url.strip() else _candidate_urls(uf)
    last_err = None
    for url in urls:
        if not url:
            continue
        try:
            print(f"GET {url}")
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                r = client.get(url)
                if r.status_code != 200:
                    last_err = f"HTTP {r.status_code}"
                    continue
                if len(r.content) < 1000:
                    last_err = "body too small"
                    continue
                dest.write_bytes(r.content)
            # sanity: open with geopandas
            import geopandas as gpd

            gdf = gpd.read_file(dest)
            n = len(gdf)
            if n <= 0:
                dest.unlink(missing_ok=True)
                last_err = "empty gpkg"
                continue
            print(f"OK {dest} features={n}")
            return 0
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            continue
    print(f"FAIL uf={uf} last={last_err}", file=sys.stderr)
    print("Hint: open IBGE FTP index and pass --url <direct gpkg>", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
