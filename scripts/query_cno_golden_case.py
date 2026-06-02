#!/usr/bin/env python3
"""
Consulta CNO ao vivo para um golden case (UUID do relatório).

Uso:
  python scripts/query_cno_golden_case.py <uuid>
  python scripts/query_cno_golden_case.py <uuid> --json-out eval/golden_dataset/<case>/cno_live.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from tools.cno_fitness_tools import (
    _map_headers,
    _resolve_municipio_codigo_cno,
    _val,
    calcular_benchmark_tempo_obra_cno,
    listar_obras_fitness_em_curso,
)

GOLDEN_ROOT = ROOT / "eval" / "golden_dataset"
_CNO_FALLBACKS = (
    Path(os.getenv("CNO_DATA_DIR", "")),
    Path(r"C:\Users\marce\Downloads\cno_extract"),
    ROOT / "data" / "cno",
)


def _resolve_cno_dir(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    for p in _CNO_FALLBACKS:
        if p and p not in candidates:
            candidates.append(p)
    for p in candidates:
        if (p / "cno.csv").is_file():
            return p
    return candidates[0] if candidates else Path(r"C:\Users\marce\Downloads\cno_extract")


def _find_case_dir(uuid: str) -> Path | None:
    for case_dir in sorted(GOLDEN_ROOT.iterdir()):
        if not case_dir.is_dir():
            continue
        exp_path = case_dir / "expected_output.json"
        if not exp_path.is_file():
            continue
        try:
            data = json.loads(exp_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("uuid") == uuid:
            return case_dir
    return None


def _discover_municipio_from_csv(cno_csv: Path, cidade: str) -> str | None:
    alvo = cidade.strip().upper()
    if not alvo:
        return None
    with open(cno_csv, encoding="latin-1", errors="replace") as f:
        reader = csv.DictReader(f)
        hdr = _map_headers(list(reader.fieldnames or []))
        for row in reader:
            mun_nome = ""
            for k, v in row.items():
                kl = (k or "").lower()
                if "nome" in kl and "munic" in kl and "codigo" not in kl:
                    mun_nome = (v or "").strip().upper()
                    break
            if alvo in mun_nome or mun_nome in alvo:
                return _val(row, hdr, "municipio")
    return None


def _resolve_municipio(cidade: str, uf: str, cno_dir: Path) -> str:
    code = _resolve_municipio_codigo_cno(cidade, uf)
    if code != "1389" or cidade.strip().upper() in ("FORTALEZA",):
        return code
    csv_path = cno_dir / "cno.csv"
    if csv_path.is_file():
        found = _discover_municipio_from_csv(csv_path, cidade)
        if found:
            return found
    return code


def _bench_dpm2(bench: dict) -> float | None:
    metrics = bench.get("metricas") if isinstance(bench.get("metricas"), dict) else {}
    val = metrics.get("dias_por_m2_mediana")
    return float(val) if val is not None else None


def _fmt_delta(actual: int | float | None, expected: int | float | None, tol: float | int) -> str:
    if expected is None or actual is None:
        return ""
    diff = abs(float(actual) - float(expected))
    if diff <= float(tol):
        return "OK"
    return f"DIFF {diff:.4g} (tol {tol})"


def query_live(
    *,
    cidade: str,
    uf: str,
    bairro: str,
    cno_dir: Path,
    limit: int = 30,
) -> dict[str, Any]:
    """CNO ao vivo: sempre município inteiro; bairro só recorta o resultado."""
    from tools.cno_fitness_tools import consultar_municipio_cnpj_cno

    out = consultar_municipio_cnpj_cno(
        cidade=cidade,
        uf=uf,
        cno_dir=cno_dir,
        bairro=bairro.strip() or None,
        limit=200,
    )
    if out.get("status") != "ok":
        raise RuntimeError(out.get("motivo") or out.get("status"))

    cno_mun = out.get("cno_fitness_keyword_municipio") or {}
    bench = out.get("benchmark_tempo_obra_cno") or {}
    por = (out.get("por_bairro") or {}).get(bairro) if bairro else None
    cno_bairro = (por or {}).get("cno_fitness_keyword_em_curso") or {}

    return {
        "municipio_rfb": out.get("municipio_rfb"),
        "cidade": cidade,
        "uf": uf,
        "bairro": bairro,
        "benchmark_tempo_obra": bench,
        "entrantes_municipio": out.get("entrantes_municipio"),
        "cruzamentos_municipio": out.get("cruzamentos_municipio"),
        "obras_em_curso": cno_mun,
        "dias_por_m2_mediana": _bench_dpm2(bench),
        "total_obras_em_curso_municipio": cno_mun.get("total_em_curso"),
        "total_obras_em_curso_bairro": (
            cno_bairro.get("total_em_curso_bairro") if bairro else cno_mun.get("total_em_curso")
        ),
        "obras_bairro": (cno_bairro.get("obras") or cno_mun.get("obras") or [])[:limit],
        "por_bairro": out.get("por_bairro"),
    }


def _print_comparison(case_id: str, live: dict[str, Any], golden: dict | None) -> None:
    cno_g = (golden or {}).get("cno_validation") if golden else None
    print(f"case_id={case_id}")
    print(
        f"  {live['cidade']}/{live['uf']} · bairro={live['bairro']} · "
        f"municipio_rfb={live['municipio_rfb']}"
    )
    print(
        f"  CNO ao vivo: em_curso_municipio={live['total_obras_em_curso_municipio']} "
        f"| em_curso_bairro={live['total_obras_em_curso_bairro']} "
        f"| dias/m² mediana={live['dias_por_m2_mediana']}"
    )

    for o in live["obras_bairro"][:8]:
        prev = (o.get("previsao_encerramento") or {}).get("data_prevista") or "—"
        print(
            f"    · {o.get('area_m2', 0):7.0f} m² | prev {prev} | "
            f"{o.get('bairro')} | {str(o.get('nome_obra', ''))[:65]}"
        )
    if live["total_obras_em_curso_bairro"] and live["total_obras_em_curso_bairro"] > 8:
        print(f"    … +{live['total_obras_em_curso_bairro'] - 8} obras no bairro")

    if not cno_g:
        print("  (sem cno_validation em expected_output.json — só consulta ao vivo)")
        return

    if cno_g.get("required") is False:
        print(f"  golden: CNO opcional — {cno_g.get('nota', '')[:120]}")
        return

    tol_cnt = int(cno_g.get("obras_count_tolerance", 2))
    exp_mun = cno_g.get("total_obras_em_curso_municipio")
    if exp_mun is None:
        exp_mun = cno_g.get("total_obras_em_curso_municipio_fitness")
    exp_bairro = cno_g.get("total_obras_em_curso_bairro")
    exp_dpm2 = cno_g.get("benchmark_dias_por_m2_mediana")
    tol_dpm2 = float(cno_g.get("benchmark_dias_por_m2_tolerance", 0.05))

    act_mun = live["total_obras_em_curso_municipio"]
    act_bairro = live["total_obras_em_curso_bairro"]
    act_dpm2 = live["dias_por_m2_mediana"]

    print("  --- vs golden (cno_validation) ---")
    if exp_mun is not None:
        print(
            f"    municipio: esperado={exp_mun} atual={act_mun} "
            f"{_fmt_delta(act_mun, exp_mun, tol_cnt)}"
        )
    if exp_bairro is not None:
        print(
            f"    bairro:    esperado={exp_bairro} atual={act_bairro} "
            f"{_fmt_delta(act_bairro, exp_bairro, tol_cnt)}"
        )
    if exp_dpm2 is not None and act_dpm2 is not None:
        print(
            f"    dias/m²:   esperado={exp_dpm2} atual={act_dpm2} "
            f"{_fmt_delta(act_dpm2, exp_dpm2, tol_dpm2)}"
        )

    exp_obras = cno_g.get("obras_em_curso_bairro") or []
    for ref in exp_obras:
        cno_ref = ref.get("cno")
        match = next((o for o in live["obras_bairro"] if o.get("cno") == cno_ref), None)
        if match:
            print(f"    obra ref {cno_ref}: encontrada ({match.get('nome_obra', '')[:50]})")
        else:
            print(f"    obra ref {cno_ref}: NÃO na lista em curso do bairro")

    ref_enc = cno_g.get("obra_referencia_encerrada_bairro")
    if isinstance(ref_enc, dict) and ref_enc.get("cno"):
        print(
            f"    ref encerrada (golden): CNO {ref_enc.get('cno')} "
            f"{ref_enc.get('area_m2')} m² — {ref_enc.get('nome_obra', '')[:50]}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta CNO para golden case por UUID")
    parser.add_argument("uuid", help="UUID do relatório (eval/golden_dataset)")
    parser.add_argument(
        "--cno-dir",
        type=Path,
        default=None,
        help="Pasta com cno.csv (default: CNO_DATA_DIR ou fallbacks locais)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Grava snapshot JSON da consulta",
    )
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    case_dir = _find_case_dir(args.uuid)
    if not case_dir:
        print(
            f"Golden case não encontrado para UUID {args.uuid}\n"
            f"Extraia antes: python scripts/extract_golden_case.py {args.uuid}",
            file=sys.stderr,
        )
        sys.exit(1)

    inp = json.loads((case_dir / "input.json").read_text(encoding="utf-8"))
    golden = json.loads((case_dir / "expected_output.json").read_text(encoding="utf-8"))
    case_id = golden.get("case_id") or case_dir.name
    cidade = (inp.get("cidade") or "").strip()
    bairro = (inp.get("bairro") or "").strip()
    uf = (inp.get("uf") or "").strip()

    if not cidade:
        print("input.json sem cidade", file=sys.stderr)
        sys.exit(1)

    cno_dir = _resolve_cno_dir(args.cno_dir)
    if not (cno_dir / "cno.csv").is_file():
        tried = ", ".join(str(p) for p in _CNO_FALLBACKS if p)
        print(
            f"CNO não encontrado em {cno_dir / 'cno.csv'}\n"
            f"Tentou: {tried}\n"
            f"Use --cno-dir com a pasta do extract (cno.csv).",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        live = query_live(
            cidade=cidade,
            uf=uf,
            bairro=bairro,
            cno_dir=cno_dir,
            limit=args.limit,
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print(f"  cno_dir={cno_dir}")
    _print_comparison(case_id, live, golden)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(live, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  JSON: {args.json_out}")


if __name__ == "__main__":
    main()
