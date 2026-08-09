"""Live Voronoi smoke preview: Maps Cocó + polígono IBGE (CE.gpkg) + censo idade_sexo."""
from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

from pdf.html_builder import gerar_html  # noqa: E402
from pdf.models import RelatorioPdfModel  # noqa: E402
from tools.absorcao_margem_fresca import (  # noqa: E402
    _estoque_faixas,
    _penetracao_efetiva,
    faixas_primario_from_idade,
)
from tools.bairro_poligono import point_in_ring, resolver_bairro_poligono  # noqa: E402
from tools.censo_setor_tools import carregar_setores_idade_sexo  # noqa: E402
from tools.parametros_metodologia import param  # noqa: E402
from tools.voronoi_atratividade import (  # noqa: E402
    _ring_centroid,
    compute_voronoi_smoke,
    concorrentes_from_searchapi_local_results,
)


def main() -> None:
    poly = resolver_bairro_poligono(
        id_municipio="2304400",
        bairro="Cocó",
        cidade="Fortaleza",
        uf="CE",
    )
    if not poly or not poly.get("ring"):
        raise SystemExit(
            "FAIL: Cocó não resolveu em CE.gpkg — rode ingest_ibge_bairros_uf --uf CE"
        )

    ring = [(float(p[0]), float(p[1])) for p in poly["ring"]]
    print(
        "poly",
        poly.get("nm_bairro"),
        "cd",
        poly.get("cd_bairro"),
        "area_km2",
        poly.get("area_km2"),
        "ring_pts",
        len(ring),
    )

    fixture = json.loads(
        (ROOT / "tools/fixtures/searchapi_maps_coco_fortaleza.json").read_text(
            encoding="utf-8"
        )
    )
    rivals_all = concorrentes_from_searchapi_local_results(fixture)
    rivals = [
        r
        for r in rivals_all
        if point_in_ring(float(r["lng"]), float(r["lat"]), ring)
    ]
    print("rivals_maps", len(rivals_all), "inside_ibge", len(rivals))
    if len(rivals) < 1:
        raise SystemExit("FAIL: nenhum concorrente Maps dentro do polígono Cocó")

    rows = carregar_setores_idade_sexo("2304400", ring=ring)
    in_ring = [
        r
        for r in rows
        if r.get("lat") is not None
        and point_in_ring(float(r["lng"]), float(r["lat"]), ring)
    ]

    segs: dict = {}
    for label, hc, mc in (
        ("15-24", "h_15_24", "m_15_24"),
        ("25-39", "h_25_39", "m_25_39"),
        ("40-59", "h_40_59", "m_40_59"),
        ("60+", "h_60_mais", "m_60_mais"),
    ):
        segs[label] = {
            "total": sum(int(r.get(hc) or 0) + int(r.get(mc) or 0) for r in in_ring)
        }
    prim = faixas_primario_from_idade(25, 40)
    est_ring = _estoque_faixas(segs, prim)
    interesse = float(param("penetracao_potencial_fitness"))
    pen, _pk = _penetracao_efetiva(None, True)
    pool_ring = int(round(est_ring * interesse * pen))

    cen = _ring_centroid(ring)
    assert cen is not None
    sites = [{"lat": cen[0], "lng": cen[1], "peso": 1500.0, "is_candidato": True}]
    for r in rivals:
        sites.append(
            {"lat": r["lat"], "lng": r["lng"], "peso": 1500.0, "is_candidato": False}
        )

    pool_ref = 1221
    pop_b = sum(int(r.get("pessoas") or 0) for r in in_ring)
    smoke = compute_voronoi_smoke(
        sites=sites,
        ring=ring,
        setores=in_ring,
        pool_ref=pool_ref,
        pop_bairro=max(pop_b, 1),
        perfil_ab=True,
        idade_min=25,
        idade_max=40,
        pin_fonte="centroide_bairro",
    )

    meta = {
        "n_rivals_maps": len(rivals_all),
        "n_rivals_inside_ibge": len(rivals),
        "n_setores_ring": len(in_ring),
        "pop_ring": pop_b,
        "estoque_form_ring": est_ring,
        "pool_ring_proxy": pool_ring,
        "ring_fonte": "CE.gpkg IBGE bairro Cocó",
        "cd_bairro": poly.get("cd_bairro"),
        "area_km2": poly.get("area_km2"),
        "smoke": smoke,
    }
    (ROOT / ".superpowers/sdd/voronoi-live-smoke.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    model = RelatorioPdfModel(
        relatorio_id="preview-voronoi-ibge",
        data_execucao="2026-08-07",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        tipo_negocio="academia",
        area_m2_min=800,
        area_m2_max=1500,
        publico_alvo=None,
        veredito="TRANSICAO",
        score_bairro=None,
        score_top1=None,
        posicionamento_estrategico={
            "veredito_posicionamento": "TRANSICAO",
            "absorcao_margem_fresca": {
                "teto_unidade": 2100,
                "capacidade_parque_estimada": 14200,
                "pool_primario": 1221,
                "pool_secundario": 642,
                "margem_fresca": -12979,
                "rotulo": "roubo",
                "base_espacial": "poligono_ibge",
                "faixas_primario": ["25-39", "40-59"],
                "faixas_secundario": ["15-24", "60+"],
                "estoque_primario": 30520,
                "estoque_secundario": 16050,
                "carimbos": {},
                "voronoi_smoke": smoke,
            },
        },
    )
    html = gerar_html(model)
    note = (
        f'<div class="note">Smoke live IBGE: polígono {poly.get("nm_bairro")} '
        f'(cd {poly.get("cd_bairro")}, ~{poly.get("area_km2")} km²) · '
        f"{len(rivals)}/{len(rivals_all)} academias Maps dentro do bairro · "
        f"{len(in_ring)} setores · pop {pop_b} · estoque form {est_ring} · "
        f"pool bairro ~{pool_ring}.</div>"
    )
    html = html.replace("</body>", note + "</body>")
    outp = ROOT / "docs/superpowers/previews/2026-08-07-voronoi-smoke.html"
    outp.write_text(html, encoding="utf-8")

    print("status", smoke.get("status"))
    print("pool_voronoi", smoke.get("pool_voronoi"))
    print("delta_pct", smoke.get("delta_pct"))
    print("estoque_celula", smoke.get("estoque_primario_celula"))
    print("pop_celula", smoke.get("pop_celula"))
    print("n_setores_celula", smoke.get("n_setores_celula"))
    print("n_sites", smoke.get("n_sites"))
    print("metodo", smoke.get("metodo_pool"))
    print("pop_ring", pop_b, "pool_ring", pool_ring)
    print("wrote", outp)


if __name__ == "__main__":
    main()
