#!/usr/bin/env python3
"""Comprime prompt de enrichment a partir do cache JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE_DIR = Path(__file__).resolve().parent / "cache"
OUT_DIR = Path(__file__).resolve().parent / "output"


def _pick_cache(cidade: str, bairro: str, uf: str) -> Path:
    slug = "_".join(
        x
        for x in [
            cidade.strip().lower(),
            (bairro or "").strip().lower(),
            uf.strip().lower(),
        ]
        if x
    )
    path = CACHE_DIR / f"{slug}.json"
    if not path.exists():
        raise FileNotFoundError(f"Cache ausente: {path} (rode cache_enrichment.py)")
    return path


def compress_from_cache(data: dict) -> str:
    loc = data.get("local") or {}
    comp = data.get("competicao_local") or {}
    al = data.get("aluguel_portais") or {}
    bcb = data.get("bcb_imobiliario") or {}
    # Raiz (build_cache) ou bloco aninhado
    _n_osm = data.get("competicao_osm_unidades")
    _redes_root = data.get("redes_detectadas_osm")
    lines = [
        "# Contexto local (cache deterministico)",
        "Local: {}/{} {}".format(loc.get("cidade"), loc.get("bairro"), loc.get("uf")),
        "cache_key: {}".format(data.get("cache_key")),
    ]
    if comp.get("status") == "ok" or _n_osm is not None:
        redes_list = comp.get("redes_detectadas_osm") or _redes_root or []
        redes = ", ".join(redes_list) if redes_list else "n/d"
        n = comp.get("total_unidades_osm", _n_osm if _n_osm is not None else 0)
        lines.append("Competicao (OSM, raio): {} unidades; redes: {}".format(n, redes))
    else:
        lines.append(
            "Competicao: {} {}".format(
                comp.get("status", "indisponivel"), comp.get("motivo", "")
            ).strip()
        )
    if al.get("n_validos") is not None:
        faixa = al.get("faixa_rs_m2") or {}
        lines.append(
            "Aluguel comercial (portais LEGADO cache): n={} conf={} p25/med/p75={}/{}/{} R$/m2".format(
                al.get("n_validos"),
                al.get("confianca"),
                faixa.get("p25"),
                faixa.get("mediana"),
                faixa.get("p75"),
            )
        )
    else:
        lines.append("Aluguel viabilidade: A4 MRLR no relatório (bundle sem portais).")
    if bcb and bcb.get("status") != "erro":
        snippet = json.dumps(bcb, ensure_ascii=False)
        lines.append("BCB: " + snippet[:400])
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cidade", default="Fortaleza")
    p.add_argument("--bairro", default="Meireles")
    p.add_argument("--uf", default="CE")
    p.add_argument("--cache-file", default="")
    args = p.parse_args()

    path = Path(args.cache_file) if args.cache_file else _pick_cache(args.cidade, args.bairro, args.uf)
    data = json.loads(path.read_text(encoding="utf-8"))
    text = compress_from_cache(data)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / ("prompt_%s.md" % path.stem)
    out.write_text(text, encoding="utf-8")
    print(text)
    print("---")
    print("written:", out)
    print("chars:", len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
