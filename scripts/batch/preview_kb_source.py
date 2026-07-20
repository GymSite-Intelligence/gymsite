#!/usr/bin/env python3
"""Inventário (dry-run) de uma pasta antes de ingerir no RAG (kb_chunks).

Mostra ONDE os arquivos estão e QUANTOS chunks/vetores cada um geraria, reusando
o MESMO chunker do ingest_kb.py — assim a contagem bate com a ingestão real.
NÃO grava nada, NÃO chama embedding, NÃO toca no banco (a menos de --check-db,
que só LÊ os `fonte` já existentes pra marcar NOVO vs JÁ-INGERIDO).

Uso:
  python scripts/batch/preview_kb_source.py --dir docs/marketing
  python scripts/batch/preview_kb_source.py --dir docs/marketing --check-db
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.batch.ingest_kb import _chunk_texto, _rows_do_json, _rows_do_md, _rows_do_pdf

_EXTS = {".md", ".txt", ".pdf", ".json"}


def _fonte_esperada(caminho: Path) -> str:
    ext = caminho.suffix.lower()
    if ext == ".pdf":
        return f"pdf:{caminho.stem}"
    if ext == ".md":
        return f"md:{caminho.stem}"
    return caminho.stem


def _contar(caminho: Path) -> tuple[int, str]:
    ext = caminho.suffix.lower()
    try:
        if ext == ".md":
            return len(_rows_do_md(caminho)), "por seção (## )"
        if ext == ".pdf":
            return len(_rows_do_pdf(caminho)), "por página"
        if ext == ".json":
            return len(_rows_do_json(caminho)), "por item json"
        if ext == ".txt":
            txt = caminho.read_text(encoding="utf-8", errors="ignore")
            return len(_chunk_texto(txt)), "tamanho fixo (2400/200)"
    except Exception as exc:
        return 0, f"ERRO: {type(exc).__name__}: {exc}"
    return 0, "ignorado"


def _fontes_no_banco() -> set[str] | None:
    try:
        from db.supabase_writer import _get_client

        client = _get_client()
        if client is None:
            return None
        resp = client.table("kb_chunks").select("fonte").execute()
        return {r["fonte"] for r in (resp.data or []) if r.get("fonte")}
    except Exception as exc:
        print(f"(aviso: --check-db falhou, seguindo sem status: {exc})")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Inventário dry-run de uma pasta pro RAG.")
    ap.add_argument("--dir", type=Path, default=Path("docs/marketing"),
                    help="pasta a inventariar (default: docs/marketing)")
    ap.add_argument("--check-db", action="store_true",
                    help="marca NOVO vs JÁ-INGERIDO consultando os `fonte` no kb_chunks")
    args = ap.parse_args()

    base = (args.dir if args.dir.is_absolute() else ROOT / args.dir).resolve()
    if not base.exists():
        print(f"pasta não encontrada: {base}")
        return 1

    arquivos = sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in _EXTS)
    if not arquivos:
        print(f"nenhum arquivo {sorted(_EXTS)} em {base}")
        return 1

    ingeridas = _fontes_no_banco() if args.check_db else None

    print(f"\n=== INVENTÁRIO RAG (dry-run) · {base} ===")
    print(f"{'arquivo':<48} {'kb':>7} {'chunks':>7} {'corte':<22} status")
    print("-" * 100)

    total_chunks = 0
    total_kb = 0.0
    for p in arquivos:
        n, corte = _contar(p)
        total_chunks += n
        kb = p.stat().st_size / 1024
        total_kb += kb
        rel = str(p.relative_to(base))
        status = ""
        if ingeridas is not None:
            status = "JÁ-INGERIDO" if _fonte_esperada(p) in ingeridas else "NOVO"
        print(f"{rel[:47]:<48} {kb:>7.1f} {n:>7} {corte:<22} {status}")

    print("-" * 100)
    print(f"{'TOTAL':<48} {total_kb:>7.1f} {total_chunks:>7}")
    print(f"\n{len(arquivos)} arquivo(s) · {total_chunks} chunks ≈ {total_chunks} vetores a gerar.")
    print("(dry-run: nada foi gravado nem embedado. Ingestão real: scripts/batch/ingest_kb.py)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
