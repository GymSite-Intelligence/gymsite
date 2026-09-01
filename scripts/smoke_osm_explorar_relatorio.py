"""Smoke VEC-378: Explorar (geo+isócrona+POIs) + bloco relatório (ancoras).

Uso (repo root):
  .venv/Scripts/python.exe scripts/smoke_osm_explorar_relatorio.py

Rede: Nominatim / Overpass / Valhalla|ORS. Fail-soft imprime status.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Meireles / Fortaleza — mesmo ponto dos previews
LAT, LNG = -3.7278218, -38.5003721
ENDERECO = "Meireles, Fortaleza, CE, Brasil"


def _ok(label: str, cond: bool, detail: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    line = f"[{mark}] {label}" + (f" - {detail}" if detail else "")
    # Windows consoles often use cp1252; avoid UnicodeEncodeError on arrows/dashes.
    print(line.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace"))


def smoke_explorar() -> dict:
    print("\n=== EXPLORAR (OSM) ===")
    from tools.maps_fallback import geocode_nominatim, suggest_nominatim
    from tools.osm_isocronas import fetch_isocronas
    from tools.osm_pois import osm_pois, resumo_ancoras_ondeabrir
    from tools.space_syntax import fetch_pois_from_overpass

    t0 = time.time()
    geo = geocode_nominatim(ENDERECO)
    _ok(
        "geocode Nominatim",
        isinstance(geo, dict) and geo.get("lat") is not None and not geo.get("error"),
        str((geo or {}).get("fonte_geocode") or (geo or {}).get("error")),
    )

    sug = suggest_nominatim("Meireles Fortaleza", LAT, LNG)
    _ok("autocomplete Nominatim", isinstance(sug, list) and len(sug) >= 0, f"n={len(sug) if isinstance(sug, list) else 0}")

    pois = osm_pois(LAT, LNG, raio_m=1000, use_cache=True)
    _ok(
        "osm_pois Overpass",
        pois.get("status") in ("ok", "ok_vazio"),
        f"status={pois.get('status')} n={pois.get('n_pois')} cache={pois.get('cache')}",
    )

    flow_pois = fetch_pois_from_overpass(LAT, LNG, radius=1000, max_pois=40)
    _ok(
        "space_syntax <- osm_pois (unificado)",
        isinstance(flow_pois, list),
        f"n={len(flow_pois)} sample_keys={list(flow_pois[0].keys()) if flow_pois else []}",
    )

    iso = {}
    try:
        iso = fetch_isocronas(LAT, LNG, "pe")
        rings = iso.get("isocronas") or iso.get("features") or iso.get("faixas") or []
        _ok(
            "isocronas Explorar",
            bool(iso) and not iso.get("erro"),
            f"keys={list(iso.keys())[:6]} n={len(rings) if isinstance(rings, list) else '?'}",
        )
    except Exception as e:
        _ok("isocronas Explorar", False, f"{type(e).__name__}: {e}")

    resumo = resumo_ancoras_ondeabrir(LAT, LNG, raio_m=1000)
    _ok(
        "resumo OndeAbrir-like",
        resumo.get("status") in ("ok", "ok_vazio"),
        f"parking={resumo.get('estacionamentos_n')} escola={resumo.get('escolas_n')} transp={resumo.get('transporte_n')}",
    )

    print(f"explorar elapsed {time.time() - t0:.1f}s")
    return {"pois": pois, "resumo": resumo, "iso": iso, "flow_pois_n": len(flow_pois)}


def smoke_relatorio(resumo: dict) -> Path | None:
    print("\n=== RELATÓRIO (HTML) ===")
    rpt = ROOT / "metrics/relatorios/rpt_1786447780.json"
    if not rpt.exists():
        _ok("JSON Meireles", False, str(rpt))
        return None

    from pdf.adapters import relatorio_from_nested_json
    from pdf.html_builder import gerar_html

    d = json.loads(rpt.read_text(encoding="utf-8"))
    out = d.setdefault("output_consolidado", {})
    mv = out.setdefault("melhores_vias_prospeccao", {})
    if isinstance(mv, dict) and resumo:
        mv["ancoras_entorno"] = resumo
        for v in mv.get("top_vias") or []:
            if isinstance(v, dict) and not v.get("ancoras_proximas"):
                v["ancoras_proximas"] = [
                    f"{a['nome']} ({a['distancia_m']}m)"
                    for a in (resumo.get("ancoras_top") or [])[:5]
                    if isinstance(a, dict)
                ]

    # Também espelha no metadata path usado pelo builder se vier de adapters
    model = relatorio_from_nested_json(d)
    html = gerar_html(model)
    outp = ROOT / "docs/superpowers/previews/2026-08-26-smoke-osm-explorar-relatorio.html"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(html, encoding="utf-8")
    _ok("gerar_html Meireles", "GymSite" in html or "Meireles" in html or len(html) > 1000, f"bytes={len(html)}")
    _ok("preview gravado", outp.exists(), str(outp))
    return outp


def main() -> int:
    print("smoke OSM explorar+relatorio Meireles", LAT, LNG)
    data = smoke_explorar()
    smoke_relatorio(data.get("resumo") or {})
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
