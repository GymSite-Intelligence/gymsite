"""Re-run Cocó→Tauape border capture with Tauape local Maps rivals."""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

from tools.absorcao_margem_fresca import (  # noqa: E402
    _estoque_faixas,
    _penetracao_efetiva,
    faixas_primario_from_idade,
)
from tools.bairro_normalize import normalizar_bairro  # noqa: E402
from tools.bairro_poligono import point_in_ring  # noqa: E402
from tools.censo_setor_tools import carregar_setores_idade_sexo  # noqa: E402
from tools.parametros_metodologia import param  # noqa: E402
from tools.voronoi_atratividade import (  # noqa: E402
    compute_voronoi_smoke,
    concorrentes_from_searchapi_local_results,
)


def _ring(geom):
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    return [(float(x), float(y)) for x, y in geom.exterior.coords]


def _pin(coco, neigh):
    strip = coco.intersection(neigh.buffer(0.0025))
    if strip.is_empty:
        strip = coco.intersection(neigh.buffer(0.005))
    pt = strip.representative_point()
    return float(pt.y), float(pt.x)


def main() -> None:
    gdf = gpd.read_file(ROOT / "data/ibge_bairros/CE.gpkg")
    gdf = gdf[gdf["CD_MUN"].astype(str) == "2304400"]
    by = {normalizar_bairro(str(r["NM_BAIRRO"])): r for _, r in gdf.iterrows()}
    coco = by[normalizar_bairro("Coco")].geometry
    tauape = by[normalizar_bairro("Sao Joao do Tauape")].geometry
    ring = _ring(tauape)
    lat, lng = _pin(coco, tauape)

    coco_maps = concorrentes_from_searchapi_local_results(
        json.loads(
            (ROOT / "tools/fixtures/searchapi_maps_coco_fortaleza.json").read_text(
                encoding="utf-8"
            )
        )
    )
    tau_maps = concorrentes_from_searchapi_local_results(
        json.loads(
            (ROOT / "tools/fixtures/searchapi_maps_tauape_fortaleza.json").read_text(
                encoding="utf-8"
            )
        )
    )
    # dedupe by rounded lat/lng
    seen = set()
    maps = []
    for m in coco_maps + tau_maps:
        key = (round(m["lat"], 5), round(m["lng"], 5))
        if key in seen:
            continue
        seen.add(key)
        maps.append(m)

    in_tau = [m for m in maps if point_in_ring(float(m["lng"]), float(m["lat"]), ring)]
    print("pin", lat, lng)
    print("rivals_total", len(maps), "inside_tauape_poly", len(in_tau))
    for m in in_tau:
        print(" -", m.get("nome") or m.get("title"), m["lat"], m["lng"])

    rows = carregar_setores_idade_sexo("2304400", ring=ring)
    setores = [
        s
        for s in rows
        if s.get("lat") is not None
        and point_in_ring(float(s["lng"]), float(s["lat"]), ring)
    ]
    segs = {}
    for label, hc, mc in (
        ("15-24", "h_15_24", "m_15_24"),
        ("25-39", "h_25_39", "m_25_39"),
        ("40-59", "h_40_59", "m_40_59"),
        ("60+", "h_60_mais", "m_60_mais"),
    ):
        segs[label] = {
            "total": sum(int(s.get(hc) or 0) + int(s.get(mc) or 0) for s in setores)
        }
    est = _estoque_faixas(segs, faixas_primario_from_idade(25, 40))
    pen, _ = _penetracao_efetiva(None, True)
    pool_ref = int(round(est * float(param("penetracao_potencial_fitness")) * pen))
    pop = sum(int(s.get("pessoas") or 0) for s in setores)

    sites = [{"lat": lat, "lng": lng, "peso": 1500.0, "is_candidato": True}]
    for m in maps:
        sites.append(
            {"lat": m["lat"], "lng": m["lng"], "peso": 1500.0, "is_candidato": False}
        )

    before = compute_voronoi_smoke(
        sites=[{"lat": lat, "lng": lng, "peso": 1500.0, "is_candidato": True}]
        + [
            {"lat": m["lat"], "lng": m["lng"], "peso": 1500.0, "is_candidato": False}
            for m in coco_maps
        ],
        ring=ring,
        setores=setores,
        pool_ref=max(pool_ref, 1),
        pop_bairro=max(pop, 1),
        perfil_ab=True,
        idade_min=25,
        idade_max=40,
        pin_fonte="borda_coco_capta_tauape",
    )
    after = compute_voronoi_smoke(
        sites=sites,
        ring=ring,
        setores=setores,
        pool_ref=max(pool_ref, 1),
        pop_bairro=max(pop, 1),
        perfil_ab=True,
        idade_min=25,
        idade_max=40,
        pin_fonte="borda_coco_capta_tauape",
    )

    out = {
        "cenario": "pin_borda_coco_demanda_tauape",
        "pin": {"lat": lat, "lng": lng},
        "pop_tauape": pop,
        "estoque_form_tauape": est,
        "pool_form_tauape": pool_ref,
        "rivals_coco_only": len(coco_maps),
        "rivals_tauape_added": len(tau_maps),
        "rivals_merged": len(maps),
        "rivals_inside_tauape_poly": len(in_tau),
        "smoke_so_coco_maps": {
            "pool_voronoi": before.get("pool_voronoi"),
            "estoque_celula": before.get("estoque_primario_celula"),
            "n_setores_celula": before.get("n_setores_celula"),
        },
        "smoke_coco_mais_tauape": {
            "pool_voronoi": after.get("pool_voronoi"),
            "estoque_celula": after.get("estoque_primario_celula"),
            "n_setores_celula": after.get("n_setores_celula"),
            "delta_pct": after.get("delta_pct"),
            "carimbo": after.get("carimbo"),
        },
    }
    path = ROOT / ".superpowers/sdd/voronoi-borda-tauape-com-parque.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("wrote", path)


if __name__ == "__main__":
    main()
