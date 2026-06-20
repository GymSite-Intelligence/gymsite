"""
Seed da tabela de benchmark `parametros_metodologia` (Supabase).

REGRA DE OURO: a tabela Supabase é a source-of-truth recalibrável; `_DEFAULTS`
em parametros_metodologia.py é o espelho versionado (fallback rotulado).
Este script empurra _DEFAULTS → Supabase via upsert por `nome`, de modo que:
  - novas métricas aparecem na tabela (e na página /metodologia);
  - métricas já recalibradas na tabela NÃO são sobrescritas, a menos de --force.

Uso:
    python -m tools.parametros_seed              # insere só o que falta (seguro)
    python -m tools.parametros_seed --force      # sobrescreve TODAS as linhas pelo default
    python -m tools.parametros_seed --dry-run    # mostra o que faria
"""
from __future__ import annotations

import argparse
import os
import sys

from tools.parametros_metodologia import _DEFAULTS
from tools.db_schema import tbl


def _client():
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    url = os.environ.get("SUPABASE_URL")
    if not (url and key):
        sys.exit("[seed] SUPABASE_URL + SERVICE_ROLE_KEY ausentes — abortado.")
    from tools.supabase_client import load_create_client

    return load_create_client()(url, key)


def _row(nome: str, rec: dict) -> dict:
    return {
        "nome": nome,
        "valor": float(rec["valor"]),
        "fonte": rec.get("fonte"),
        "data_coleta": rec.get("data_coleta"),
        "metodo": rec.get("metodo"),
        "unidade": rec.get("unidade"),
        "categoria": rec.get("categoria"),
    }


def seed(*, force: bool = False, dry_run: bool = False) -> None:
    cli = _client()
    existentes = set()
    try:
        res = tbl(cli, "parametros_metodologia").select("nome").execute()
        existentes = {r["nome"] for r in (getattr(res, "data", None) or [])}
    except Exception as e:
        sys.exit(f"[seed] não consegui ler tabela: {type(e).__name__}: {e}")

    a_inserir, a_atualizar = [], []
    for nome, rec in _DEFAULTS.items():
        row = _row(nome, rec)
        if nome in existentes:
            if force:
                a_atualizar.append(row)
        else:
            a_inserir.append(row)

    print(f"[seed] {len(_DEFAULTS)} métricas no _DEFAULTS | "
          f"{len(existentes)} já na tabela | "
          f"inserir={len(a_inserir)} | "
          f"atualizar(force)={len(a_atualizar) if force else 0}")

    if dry_run:
        for r in a_inserir:
            print(f"   + {r['nome']:<32} {r['valor']:>10}  [{r['categoria']}]")
        if force:
            for r in a_atualizar:
                print(f"   ~ {r['nome']:<32} {r['valor']:>10}  [{r['categoria']}]")
        print("[seed] dry-run — nada gravado.")
        return

    payload = a_inserir + (a_atualizar if force else [])
    if not payload:
        print("[seed] nada a fazer (use --force pra atualizar categoria/fonte das existentes).")
        return

    # upsert por nome (PK/unique em `nome`)
    tbl(cli, "parametros_metodologia").upsert(payload, on_conflict="nome").execute()
    print(f"[seed] gravadas {len(payload)} linhas.")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="sobrescreve linhas existentes pelo default")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    seed(force=args.force, dry_run=args.dry_run)
