#!/usr/bin/env python3
"""
Re-scrape horários de pico para um place_id (ignora cache sem_popular_times).

Uso:
  python scripts/refresh_popular_times_cache.py ChIJmXdNVzu_uZQRzWnQroPidNI \\
    --nome "Academia Smart Fit - Neo" --cidade "Ribeirão Preto" \\
    --lat -21.1805 --lng -47.8102
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.popular_times_tool import _cache_path, pesquisar_horarios_pico


async def main() -> None:
    p = argparse.ArgumentParser(description="Refresh competitor_cache peak JSON")
    p.add_argument("place_id", help="Google place_id (ChIJ...)")
    p.add_argument("--nome", default="", help="Nome do lugar")
    p.add_argument("--cidade", default="", help="Cidade para busca Maps")
    p.add_argument("--lat", type=float, default=None)
    p.add_argument("--lng", type=float, default=None)
    p.add_argument("--maps-url", default="", help="googleMapsUri opcional")
    args = p.parse_args()

    cp = _cache_path(args.place_id)
    if cp.exists():
        cp.unlink()
        print(f"Cache removido: {cp}")

    maps_url = args.maps_url or ""
    r = await pesquisar_horarios_pico(
        maps_url,
        args.place_id,
        nome=args.nome,
        cidade=args.cidade,
        lat=args.lat,
        lng=args.lng,
        force_refresh=True,
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print(f"\nstatus={r.get('status')} pontos={r.get('total_pontos_extraidos', 0)}")
    print(f"cache_file={cp}")


if __name__ == "__main__":
    asyncio.run(main())
