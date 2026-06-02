#!/usr/bin/env python3
"""
Consulta CNPJ fitness (entrantes) → CNO por município, com fallback opcional por bairro.

Fluxo: Supabase (entrantes 90d, CNAE 9313100) → match no CNO municipal inteiro.

Uso:
  python scripts/query_cnpj_cno.py --cidade Niterói --uf RJ
  python scripts/query_cnpj_cno.py --cidade Niterói --uf RJ --bairro Piratininga
  python scripts/query_cnpj_cno.py --cidade Niterói --uf RJ --bairros Itaipu,Piratininga,Camboinhas \\
    --json-out eval/golden_dataset/niteroi_camboinhas_20260513/cno_cruzamento_cnpj.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _stdout_reconfigure is not None:
    try:
        _stdout_reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "frontend" / ".env", override=False)

from tools.cno_fitness_tools import consultar_municipio_cnpj_cno, resolve_cno_data_dir


def _parse_bairros(bairro: str, bairros: str) -> list[str] | None:
    if bairros.strip():
        return [b.strip() for b in bairros.split(",") if b.strip()]
    if bairro.strip():
        return [bairro.strip()]
    return None


def _print_cruzamento(c: dict) -> None:
    obra = c.get("obra") or {}
    nome_obra = obra.get("nome_obra") or obra.get("nota") or "—"
    area = c.get("area_m2_obra") or obra.get("area_m2_max") or "?"
    tag = c.get("match_cno") or "sem_match"
    print(
        f"  [{tag}] {c.get('data_abertura')} | "
        f"{c.get('nome_fantasia') or c.get('cnpj')} | "
        f"area={area} | {c.get('bairro')} | {c.get('endereco') or c.get('cep')} | "
        f"obra: {str(nome_obra)[:55]}"
    )


def _emit_console(out: dict) -> None:
    meta = {
        k: v
        for k, v in out.items()
        if k
        not in (
            "cruzamentos",
            "cruzamentos_com_obra",
            "cruzamentos_municipio",
            "cruzamentos_com_obra_municipio",
            "por_bairro",
            "obras_fitness_em_curso",
            "obras_fitness_referencia",
        )
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))

    em = out.get("entrantes_municipio") or {}
    cno_mun = out.get("cno_fitness_keyword_municipio") or {}
    print(
        f"\n[1] Município — entrantes CNPJ: {em.get('total', 0)} | "
        f"com CNO: {em.get('com_match_cno', 0)} | sem CNO: {em.get('sem_match_cno', 0)}"
    )
    print(
        f"    CNO keyword (fitness) em curso no município: "
        f"{cno_mun.get('total_em_curso', '—')}"
    )

    print("\n--- Entrantes municipais com match CNO ---")
    for c in out.get("cruzamentos_com_obra_municipio") or []:
        _print_cruzamento(c)

    por_bairro = out.get("por_bairro")
    if por_bairro:
        print("\n[2] Recorte por bairro (sobre o município acima)")
        for nome, block in por_bairro.items():
            cno_b = (block.get("cno_fitness_keyword_em_curso") or {})
            print(
                f"\n--- Bairro: {nome} --- "
                f"entrantes: {block.get('total_entrantes')} | "
                f"com CNO: {block.get('com_match_cno')} | "
                f"CNO keyword em curso no bairro: {cno_b.get('total_em_curso_bairro', 0)}"
            )
            for c in block.get("cruzamentos_com_obra") or []:
                _print_cruzamento(c)
            for c in block.get("cruzamentos") or []:
                if c.get("match_cno"):
                    continue
                _print_cruzamento(c)
        return

    print("\n--- Sem obra CNO (município) ---")
    for c in out.get("cruzamentos_municipio") or out.get("cruzamentos") or []:
        if c.get("match_cno"):
            continue
        _print_cruzamento(c)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="CNPJ fitness (90d) → CNO — escopo municipal, filtro opcional por bairro"
    )
    ap.add_argument("--cidade", required=True, help="Nome do município (ex: Niterói, Fortaleza)")
    ap.add_argument("--uf", required=True, help="UF (ex: RJ, CE)")
    ap.add_argument("--bairro", default="", help="Recorte opcional — um bairro")
    ap.add_argument(
        "--bairros",
        default="",
        help="Recorte opcional — lista separada por vírgula (ex: Itaipu,Piratininga)",
    )
    ap.add_argument("--dias", type=int, default=90, help="Janela de entrantes CNPJ (dias)")
    ap.add_argument("--limit", type=int, default=200, help="Máx. entrantes consultados no Supabase")
    ap.add_argument("--cno-dir", default="", help="Pasta do extract CNO (default: env CNO_DATA_DIR)")
    ap.add_argument("--json-out", default="", help="Salvar JSON completo")
    args = ap.parse_args()

    try:
        cno_dir = resolve_cno_data_dir(args.cno_dir or None)
    except FileNotFoundError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    alvos = _parse_bairros(args.bairro, args.bairros)
    out = consultar_municipio_cnpj_cno(
        cidade=args.cidade,
        uf=args.uf,
        cno_dir=cno_dir,
        dias=args.dias,
        limit=args.limit,
        bairro=alvos[0] if alvos and len(alvos) == 1 else None,
        bairros=alvos if alvos and len(alvos) > 1 else None,
    )

    if out.get("status") != "ok":
        print(json.dumps(out, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    _emit_console(out)

    if args.json_out:
        dest = Path(args.json_out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON: {dest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
