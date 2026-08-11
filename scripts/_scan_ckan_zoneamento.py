"""Scan CKAN portals for plano diretor / zoneamento resources."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

PORTALS = [
    ("dados.gov.br", "https://dados.gov.br/api/3/action"),
    ("Fortaleza", "https://dados.fortaleza.ce.gov.br/api/3/action"),
    ("BH", "https://ckan.pbh.gov.br/api/3/action"),
    ("Recife", "https://dados.recife.pe.gov.br/api/3/action"),
    ("SP", "https://dados.prefeitura.sp.gov.br/api/3/action"),
    ("RJ", "https://www.data.rio/api/3/action"),
    ("Curitiba", "https://www.curitiba.pr.gov.br/dadosabertos/api/3/action"),
    ("Porto Alegre", "https://dadosabertos.poa.br/api/3/action"),
    ("Salvador", "https://dados.salvador.ba.gov.br/api/3/action"),
    ("Brasilia", "https://dados.df.gov.br/api/3/action"),
    ("Campinas", "https://dados.campinas.sp.gov.br/api/3/action"),
    ("Niteroi", "https://dados.niteroi.rj.gov.br/api/3/action"),
    ("Goiania", "https://dados.goiania.go.gov.br/api/3/action"),
    ("Manaus", "https://dados.manaus.am.gov.br/api/3/action"),
]

Q = 'zoneamento OR "plano diretor" OR "uso do solo" OR LUOS OR ZEIS'


def search(base: str, q: str = Q, rows: int = 10) -> dict:
    url = f"{base}/package_search"
    try:
        r = httpx.get(url, params={"q": q, "rows": rows}, timeout=25, follow_redirects=True)
        if r.status_code != 200:
            return {"erro": f"HTTP {r.status_code}"}
        data = r.json()
        if not data.get("success"):
            return {"erro": "success=false", "raw": str(data)[:200]}
        res = data["result"]
        out = []
        for p in res.get("results") or []:
            fmts = sorted({(rr.get("format") or "").upper() for rr in (p.get("resources") or [])})
            geo = [f for f in fmts if f in {"KMZ", "KML", "GEOJSON", "SHP", "SHAPEFILE", "ZIP", "GPKG", "JSON"}]
            out.append({
                "name": p.get("name"),
                "title": (p.get("title") or "")[:120],
                "formats": fmts,
                "geo_formats": geo,
                "n_res": len(p.get("resources") or []),
            })
        return {"count": res.get("count"), "hits": out}
    except Exception as e:
        return {"erro": str(e)[:200]}


def main() -> None:
    report: dict = {}
    for label, base in PORTALS:
        report[label] = search(base)
        st = report[label]
        if "erro" in st:
            print(f"{label}: ERRO {st['erro']}")
        else:
            print(f"{label}: count={st.get('count')} sample={len(st.get('hits') or [])}")
            for h in (st.get("hits") or [])[:5]:
                print(f"  - {h['name']} | {h['geo_formats'] or h['formats'][:4]} | {h['title'][:70]}")
    Path("artifacts/_zeus_ckan_scan.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved artifacts/_zeus_ckan_scan.json")


if __name__ == "__main__":
    main()
