"""Border-capture smoke: pin inside Cocó at frontier; demand = neighbor polygon."""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv
from shapely.geometry import Point

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

VIZINHOS = [
    "Aldeota",
    "Cidade 2000",
    "Dionísio Torres",
    "Edson Queiroz",
    "Manuel Dias Branco",
    "Papicu",
    "Salinas",
    "São João do Tauape",
    "Varjota",
]


def _ring_from_geom(geom) -> list[tuple[float, float]]:
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    coords = list(geom.exterior.coords)
    return [(float(x), float(y)) for x, y in coords]


def _pin_borda_coco(coco_geom, neigh_geom) -> tuple[float, float] | None:
    """Point inside Cocó near shared border with neighbor."""
    strip = coco_geom.intersection(neigh_geom.buffer(0.0025))
    if strip.is_empty:
        strip = coco_geom.intersection(neigh_geom.buffer(0.005))
    if strip.is_empty:
        return None
    pt = strip.representative_point()
    if not coco_geom.contains(pt) and not coco_geom.touches(pt):
        pt = coco_geom.representative_point()
    return float(pt.y), float(pt.x)  # lat, lng


def _pool_form(setores: list[dict], *, perfil_ab: bool) -> tuple[int, int]:
    segs: dict = {}
    for label, hc, mc in (
        ("15-24", "h_15_24", "m_15_24"),
        ("25-39", "h_25_39", "m_25_39"),
        ("40-59", "h_40_59", "m_40_59"),
        ("60+", "h_60_mais", "m_60_mais"),
    ):
        segs[label] = {
            "total": sum(int(r.get(hc) or 0) + int(r.get(mc) or 0) for r in setores)
        }
    prim = faixas_primario_from_idade(25, 40)
    est = _estoque_faixas(segs, prim)
    interesse = float(param("penetracao_potencial_fitness"))
    pen, _ = _penetracao_efetiva(None, perfil_ab)
    return est, int(round(est * interesse * pen))


def main() -> None:
    gdf = gpd.read_file(ROOT / "data/ibge_bairros/CE.gpkg")
    gdf = gdf[gdf["CD_MUN"].astype(str) == "2304400"].copy()
    by_name = {
        normalizar_bairro(str(r["NM_BAIRRO"])): r
        for _, r in gdf.iterrows()
    }
    coco = by_name.get(normalizar_bairro("Coco"))
    if coco is None:
        raise SystemExit("Cocó missing in CE.gpkg")
    coco_geom = coco.geometry

    fixture = json.loads(
        (ROOT / "tools/fixtures/searchapi_maps_coco_fortaleza.json").read_text(
            encoding="utf-8"
        )
    )
    maps = concorrentes_from_searchapi_local_results(fixture)

    rows_out: list[dict] = []
    for nome in VIZINHOS:
        row = by_name.get(normalizar_bairro(nome))
        if row is None:
            rows_out.append({"vizinho": nome, "status": "sem_poligono"})
            continue
        neigh_geom = row.geometry
        pin = _pin_borda_coco(coco_geom, neigh_geom)
        if pin is None:
            rows_out.append({"vizinho": nome, "status": "sem_pin"})
            continue
        lat, lng = pin
        ring = _ring_from_geom(neigh_geom)

        setores_bbox = carregar_setores_idade_sexo("2304400", ring=ring)
        in_ring = [
            s
            for s in setores_bbox
            if s.get("lat") is not None
            and point_in_ring(float(s["lng"]), float(s["lat"]), ring)
        ]
        est, pool_ref = _pool_form(in_ring, perfil_ab=True)
        pop_b = sum(int(s.get("pessoas") or 0) for s in in_ring)

        # Rivais: todos Maps + conta quantos caem no vizinho vs Cocó
        n_in_viz = sum(
            1 for m in maps if point_in_ring(float(m["lng"]), float(m["lat"]), ring)
        )
        coco_ring = _ring_from_geom(coco_geom)
        n_in_coco = sum(
            1
            for m in maps
            if point_in_ring(float(m["lng"]), float(m["lat"]), coco_ring)
        )

        sites = [{"lat": lat, "lng": lng, "peso": 1500.0, "is_candidato": True}]
        for m in maps:
            sites.append(
                {
                    "lat": m["lat"],
                    "lng": m["lng"],
                    "peso": 1500.0,
                    "is_candidato": False,
                }
            )

        smoke = compute_voronoi_smoke(
            sites=sites,
            ring=ring,
            setores=in_ring,
            pool_ref=max(pool_ref, 1),
            pop_bairro=max(pop_b, 1),
            perfil_ab=True,
            idade_min=25,
            idade_max=40,
            pin_fonte="borda_coco_capta_vizinho",
        )
        rows_out.append(
            {
                "vizinho": nome,
                "status": smoke.get("status"),
                "pin_lat": round(lat, 6),
                "pin_lng": round(lng, 6),
                "pop_vizinho": pop_b,
                "estoque_form_vizinho": est,
                "pool_form_vizinho": pool_ref,
                "pool_voronoi": smoke.get("pool_voronoi"),
                "estoque_celula": smoke.get("estoque_primario_celula"),
                "n_setores_celula": smoke.get("n_setores_celula"),
                "delta_pct_vs_vizinho": smoke.get("delta_pct"),
                "maps_no_vizinho": n_in_viz,
                "maps_no_coco": n_in_coco,
                "n_sites": smoke.get("n_sites"),
            }
        )

    rows_out.sort(
        key=lambda r: (r.get("pool_voronoi") is None, -(r.get("pool_voronoi") or -1))
    )
    out_path = ROOT / ".superpowers/sdd/voronoi-bordas-coco.json"
    out_path.write_text(json.dumps(rows_out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("pin=Cocó borda | demanda=polígono vizinho | rivais=20 Maps fixture")
    print(f"{'vizinho':22} {'pool_V':>6} {'pool_viz':>8} {'est_cel':>7} {'set':>4} {'maps_v':>6} {'pop':>7}")
    for r in rows_out:
        if r.get("status") != "ok" or r.get("pool_voronoi") is None:
            print(f"{r['vizinho']:22} STATUS={r.get('status')} {r}")
            continue
        print(
            f"{r['vizinho']:22} {r['pool_voronoi']:>6} {r['pool_form_vizinho']:>8} "
            f"{r['estoque_celula']:>7} {r['n_setores_celula']:>4} "
            f"{r['maps_no_vizinho']:>6} {r['pop_vizinho']:>7}"
        )
    print("wrote", out_path)
    if rows_out and rows_out[0].get("pool_voronoi") is not None:
        best = rows_out[0]
        print(
            f"MELHOR BORDA: {best['vizinho']} → {best['pool_voronoi']} alunos "
            f"(vizinho form {best['pool_form_vizinho']}, célula estoque {best['estoque_celula']})"
        )


if __name__ == "__main__":
    main()
