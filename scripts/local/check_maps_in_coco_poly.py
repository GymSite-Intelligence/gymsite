"""Check which SearchAPI Maps pins fall inside IBGE Cocó polygon."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from tools.bairro_poligono import point_in_ring, resolver_bairro_poligono
from tools.voronoi_atratividade import concorrentes_from_searchapi_local_results


def main() -> None:
    poly = resolver_bairro_poligono(
        id_municipio="2304400",
        bairro="Cocó",
        cidade="Fortaleza",
        uf="CE",
    )
    if not poly or not poly.get("ring"):
        raise SystemExit("Cocó polygon missing — need data/ibge_bairros/CE.gpkg")
    ring = [(float(p[0]), float(p[1])) for p in poly["ring"]]
    fixture = json.loads(
        (ROOT / "tools/fixtures/searchapi_maps_coco_fortaleza.json").read_text(
            encoding="utf-8"
        )
    )
    rivals = concorrentes_from_searchapi_local_results(fixture)
    inside = []
    outside = []
    for r in rivals:
        ok = point_in_ring(float(r["lng"]), float(r["lat"]), ring)
        row = {
            "pos": r.get("position"),
            "nome": r.get("nome") or r.get("title"),
            "addr": r.get("address") or "",
            "lat": r["lat"],
            "lng": r["lng"],
            "inside": ok,
        }
        (inside if ok else outside).append(row)

    print(
        f"poligono={poly.get('nm_bairro')} cd={poly.get('cd_bairro')} "
        f"area_km2={poly.get('area_km2')}"
    )
    print(f"total={len(rivals)} inside={len(inside)} outside={len(outside)}")
    print("--- DENTRO ---")
    for x in inside:
        print(
            f"{x['pos']:>2} | {x['nome'][:45]:45} | "
            f"{x['lat']:.6f},{x['lng']:.6f} | {x['addr'][:70]}"
        )
    print("--- FORA ---")
    for x in outside:
        print(
            f"{x['pos']:>2} | {x['nome'][:45]:45} | "
            f"{x['lat']:.6f},{x['lng']:.6f} | {x['addr'][:70]}"
        )


if __name__ == "__main__":
    main()
