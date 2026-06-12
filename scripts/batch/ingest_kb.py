#!/usr/bin/env python3
"""
Ingestão da base de conhecimento RAG (kb_chunks).

Fontes:
  --pdf docs/mapeamento_franquias_academia_brasil.pdf  (chunk por página)
  --json <arquivo.json>  lista de {fonte, titulo, url, ano_referencia, conteudo}

Re-ingestão é idempotente por fonte: deleta chunks da fonte antes de inserir.

Uso:
  python scripts/batch/ingest_kb.py --pdf docs/mapeamento_franquias_academia_brasil.pdf
  python scripts/batch/ingest_kb.py --json seeds/kb_franquias_web.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

_CHUNK_MAX = 2400  # ~600 tokens; página de PDF denso cabe inteira
_OVERLAP = 200


def _chunk_texto(texto: str) -> list[str]:
    texto = " ".join(texto.split())
    if len(texto) <= _CHUNK_MAX:
        return [texto] if texto else []
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fim = inicio + _CHUNK_MAX
        chunks.append(texto[inicio:fim])
        inicio = fim - _OVERLAP
    return chunks


def _rows_do_pdf(caminho: Path) -> list[dict]:
    import pypdf

    reader = pypdf.PdfReader(str(caminho))
    fonte = f"pdf:{caminho.stem}"
    rows = []
    for i, page in enumerate(reader.pages, start=1):
        texto = (page.extract_text() or "").strip()
        for j, chunk in enumerate(_chunk_texto(texto)):
            rows.append({
                "fonte": fonte,
                "titulo": f"Mapeamento Franquias Academia BR — pg {i}",
                "url": None,
                "ano_referencia": 2026,
                "conteudo": chunk,
                "metadados": {"pagina": i, "sub_chunk": j},
            })
    return rows


def _rows_do_json(caminho: Path) -> list[dict]:
    docs = json.loads(caminho.read_text(encoding="utf-8"))
    rows = []
    for d in docs:
        for j, chunk in enumerate(_chunk_texto(d["conteudo"])):
            rows.append({
                "fonte": d["fonte"],
                "titulo": d.get("titulo"),
                "url": d.get("url"),
                "ano_referencia": d.get("ano_referencia"),
                "conteudo": chunk,
                "metadados": {"sub_chunk": j},
            })
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", type=Path)
    p.add_argument("--json", type=Path)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    rows: list[dict] = []
    if args.pdf:
        rows += _rows_do_pdf(args.pdf)
    if args.json:
        rows += _rows_do_json(args.json)
    if not rows:
        print("nada a ingerir — use --pdf e/ou --json")
        return 1

    print(f"{len(rows)} chunks preparados")
    if args.dry_run:
        for r in rows[:3]:
            print(f"  [{r['fonte']}] {r['titulo']}: {r['conteudo'][:100]}...")
        return 0

    from services.kb_rag import embed_texto
    from db.supabase_writer import _get_client

    client = _get_client()
    if client is None:
        print("ERRO: credenciais Supabase ausentes")
        return 1

    # Idempotência: limpa fontes que serão re-inseridas
    fontes = sorted({r["fonte"] for r in rows})
    for fonte in fontes:
        client.table("kb_chunks").delete().eq("fonte", fonte).execute()
        print(f"limpos chunks antigos de {fonte}")

    ok, falhas = 0, 0
    for r in rows:
        emb = embed_texto(r["conteudo"], task_type="RETRIEVAL_DOCUMENT")
        if not emb:
            falhas += 1
            continue
        client.table("kb_chunks").insert({**r, "embedding": emb}).execute()
        ok += 1
        time.sleep(0.15)  # cortesia de rate

    print(f"ingeridos: {ok} | falhas embed: {falhas}")
    return 0 if falhas == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
