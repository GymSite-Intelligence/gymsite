"""Deep probe: User-Agent + package_show known IDs + alternate CKAN bases."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

UA = {"User-Agent": "GymSite-ZEUS/1.0 (pesquisa-plano-diretor; contato@getgymsite.com.br)"}

BASES = [
    ("dados.gov.br", "https://dados.gov.br/api/3/action"),
    ("dados.gov.br-alt", "https://www.dados.gov.br/api/3/action"),
    ("Fortaleza", "https://dados.fortaleza.ce.gov.br/api/3/action"),
    ("BH-ckan", "https://ckan.pbh.gov.br/api/3/action"),
    ("BH-dados", "https://dados.pbh.gov.br/api/3/action"),
    ("Recife", "https://dados.recife.pe.gov.br/api/3/action"),
    ("SP-pref", "https://dados.prefeitura.sp.gov.br/api/3/action"),
    ("SP-estado", "https://dadosabertos.sp.gov.br/api/3/action"),
    ("RJ-data", "https://www.data.rio/api/3/action"),
    ("RJ-opendata", "https://opendata.rio/api/3/action"),
    ("Curitiba", "https://www.curitiba.pr.gov.br/dadosabertos/consulta/api/3/action"),
    ("POA", "https://dadosabertos.poa.br/api/3/action"),
    ("Natal", "https://dados.natal.rn.gov.br/api/3/action"),
    ("JoaoPessoa", "https://dados.joaopessoa.pb.gov.br/api/3/action"),
    ("Vitoria", "https://dados.vitoria.es.gov.br/api/3/action"),
]

KNOWN = [
    ("Fortaleza", "https://dados.fortaleza.ce.gov.br/api/3/action", "zonas-especiais"),
    ("Fortaleza", "https://dados.fortaleza.ce.gov.br/api/3/action", "zona-especial-zedus"),
    ("BH", "https://dados.pbh.gov.br/api/3/action", "zoneamento-lei-11181"),
    ("BH", "https://ckan.pbh.gov.br/api/3/action", "zoneamento-lei-11181"),
    ("Recife", "https://dados.recife.pe.gov.br/api/3/action", "zoneamento"),
    ("SP", "https://dados.prefeitura.sp.gov.br/api/3/action", "plano-diretor-estrategico-pde-municipio-de-sao-paulo"),
    ("SP", "https://dados.prefeitura.sp.gov.br/api/3/action", "zoneamento"),
]


def pkg_search(base: str, q: str, rows: int = 12) -> dict:
    try:
        r = httpx.get(
            f"{base}/package_search",
            params={"q": q, "rows": rows},
            headers=UA,
            timeout=25,
            follow_redirects=True,
        )
        if r.status_code != 200:
            return {"erro": f"HTTP {r.status_code}"}
        data = r.json()
        if not data.get("success"):
            return {"erro": "success=false"}
        res = data["result"]
        hits = []
        for p in res.get("results") or []:
            resources = []
            for rr in p.get("resources") or []:
                resources.append({
                    "name": (rr.get("name") or "")[:80],
                    "format": (rr.get("format") or "").upper(),
                    "url": (rr.get("url") or "")[:160],
                })
            fmts = sorted({x["format"] for x in resources if x["format"]})
            hits.append({
                "name": p.get("name"),
                "title": (p.get("title") or "")[:120],
                "formats": fmts,
                "resources": resources[:12],
            })
        return {"count": res.get("count"), "hits": hits}
    except Exception as e:
        return {"erro": str(e)[:200]}


def pkg_show(base: str, package_id: str) -> dict:
    try:
        r = httpx.get(
            f"{base}/package_show",
            params={"id": package_id},
            headers=UA,
            timeout=25,
            follow_redirects=True,
        )
        if r.status_code != 200:
            return {"erro": f"HTTP {r.status_code}"}
        data = r.json()
        if not data.get("success"):
            return {"erro": "success=false", "error": data.get("error")}
        p = data["result"]
        resources = [{
            "name": (rr.get("name") or "")[:100],
            "format": (rr.get("format") or "").upper(),
            "url": rr.get("url"),
            "mimetype": rr.get("mimetype"),
        } for rr in (p.get("resources") or [])]
        return {
            "name": p.get("name"),
            "title": p.get("title"),
            "resources": resources,
            "formats": sorted({r["format"] for r in resources if r["format"]}),
        }
    except Exception as e:
        return {"erro": str(e)[:200]}


def main() -> None:
    report: dict = {"searches": {}, "known": {}}
    queries = [
        "zoneamento",
        "plano diretor",
        "zonas especiais",
        "uso e ocupacao",
    ]
    for label, base in BASES:
        report["searches"][label] = {}
        for q in queries:
            st = pkg_search(base, q, rows=8)
            report["searches"][label][q] = st
            if "erro" in st:
                print(f"{label} [{q}]: ERRO {st['erro']}")
            else:
                n = st.get("count")
                print(f"{label} [{q}]: count={n}")
                for h in (st.get("hits") or [])[:3]:
                    print(f"   · {h['name']} {h['formats']}")

    for label, base, pid in KNOWN:
        key = f"{label}:{pid}"
        st = pkg_show(base, pid)
        report["known"][key] = st
        if "erro" in st:
            print(f"SHOW {key}: ERRO {st['erro']}")
        else:
            print(f"SHOW {key}: formats={st.get('formats')}")
            for rr in st.get("resources") or []:
                print(f"   · {rr['format']:10} {rr['name'][:60]}")

    Path("artifacts/_zeus_ckan_deep.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved artifacts/_zeus_ckan_deep.json")


if __name__ == "__main__":
    main()
