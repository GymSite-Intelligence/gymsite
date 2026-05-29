#!/usr/bin/env python3
"""
Sanitiza `cidade` (nome oficial IBGE) e `bairro` (title case) em cnpj_fitness_estabelecimentos.

Uso:
  python tools/cnpj_sanitize_localidades.py --dry-run
  python tools/cnpj_sanitize_localidades.py
  python tools/cnpj_sanitize_localidades.py --only-cidade
  python tools/cnpj_sanitize_localidades.py --only-bairro
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)

from tools.cnpj_fitness_tools import _supabase_client

IBGE_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
PAGE = 1000
_PREPS = frozenset({"de", "da", "do", "das", "dos", "e"})
_RETRY_DELAYS = (2, 5, 10)


def _with_retries(fn, *, label: str = "op"):
    last: Exception | None = None
    for delay in _RETRY_DELAYS:
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as exc:
            last = exc
            print(f"[retry] {label}: {exc}", flush=True)
            time.sleep(delay)
    if last:
        raise last
    raise RuntimeError(f"falha: {label}")


def _strip_acentos(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _chave_localidade(nome: str, uf: str) -> tuple[str, str]:
    n = _strip_acentos((nome or "").lower())
    n = re.sub(r"[-']", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n, (uf or "").upper()[:2]


def _title_hifen(s: str) -> str:
    """Title case respeitando hífen: guajara-mirim -> Guajara-Mirim."""
    s = (s or "").strip()
    if not s:
        return ""

    def _w(word: str, *, first_in_phrase: bool) -> str:
        w = word.lower()
        if not first_in_phrase and w in _PREPS:
            return w
        return w[:1].upper() + w[1:] if w else ""

    out: list[str] = []
    first = True
    for chunk in re.split(r"(\s+|-)", s):
        if not chunk:
            continue
        if chunk in (" ", "-"):
            out.append(chunk)
            if chunk == " ":
                first = True
            continue
        out.append(_w(chunk, first_in_phrase=first))
        first = False
    return "".join(out)


def formatar_bairro_exibicao(s: str) -> str:
    return _title_hifen(s)


def _uf_ibge(m: dict) -> str:
    micro = m.get("microrregiao")
    if micro:
        return micro["mesorregiao"]["UF"]["sigla"]
    imediata = m.get("regiao-imediata") or m.get("regiao_imediata")
    if imediata:
        return imediata["regiao-intermediaria"]["UF"]["sigla"]
    raise KeyError(f"UF não encontrada para {m.get('nome')}")


def _fetch_ibge_index() -> dict[tuple[str, str], str]:
    r = httpx.get(IBGE_MUNICIPIOS, timeout=120.0)
    r.raise_for_status()
    index: dict[tuple[str, str], str] = {}
    for m in r.json():
        uf = _uf_ibge(m)
        nome = m["nome"]
        index[_chave_localidade(nome, uf)] = nome
    return index


def _resolve_cidade_ibge(
    cidade_atual: str, uf: str, ibge_index: dict[tuple[str, str], str]
) -> str | None:
    uf = (uf or "").upper()[:2]
    if not uf:
        return None
    for cand in (cidade_atual, _title_hifen(cidade_atual)):
        key = _chave_localidade(cand, uf)
        hit = ibge_index.get(key)
        if hit:
            return hit
    return None


def _fetch_all_rows(sb, fields: str) -> list[dict]:
    offset = 0
    rows: list[dict] = []
    while True:
        res = (
            sb.table("cnpj_fitness_estabelecimentos")
            .select(fields)
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = res.data or []
        if not batch:
            break
        rows.extend(batch)
        offset += PAGE
        if len(batch) < PAGE:
            break
    return rows


def sanitize(
    *,
    dry_run: bool = False,
    only_cidade: bool = False,
    only_bairro: bool = False,
) -> dict[str, int]:
    sb = _supabase_client()
    if sb is None:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY não configurados")

    do_cidade = not only_bairro
    do_bairro = not only_cidade

    ibge_index: dict[tuple[str, str], str] = {}
    if do_cidade:
        print("carregando municípios IBGE…", flush=True)
        ibge_index = _fetch_ibge_index()
        print(f"  {len(ibge_index)} chaves IBGE", flush=True)

    rows = _fetch_all_rows(
        sb, "id, municipio_codigo, uf, cidade, bairro"
    )
    print(f"registros: {len(rows)}", flush=True)

    # --- cidade: agrupa por municipio_codigo + uf ---
    cidade_updates = 0
    cidade_miss: set[tuple[str, str, str]] = set()
    if do_cidade:
        grupos: dict[tuple[str, str], str] = {}
        for row in rows:
            mc = (row.get("municipio_codigo") or "").strip()
            uf = (row.get("uf") or "").upper()[:2]
            atual = (row.get("cidade") or "").strip()
            if not mc or not uf or not atual:
                continue
            key = (mc, uf)
            if key in grupos:
                continue
            oficial = _resolve_cidade_ibge(atual, uf, ibge_index)
            if oficial and oficial != atual:
                grupos[key] = oficial
            elif not oficial:
                cidade_miss.add((mc, uf, atual))

        print(f"grupos cidade a corrigir: {len(grupos)}", flush=True)
        if cidade_miss:
            print(f"[warn] sem match IBGE: {len(cidade_miss)}", flush=True)
            for item in sorted(cidade_miss)[:10]:
                print(f"  - {item}")

        if not dry_run:
            for i, ((mc, uf), novo) in enumerate(grupos.items(), start=1):
                _with_retries(
                    lambda mc=mc, uf=uf, novo=novo: sb.table(
                        "cnpj_fitness_estabelecimentos"
                    )
                    .update({"cidade": novo})
                    .eq("municipio_codigo", mc)
                    .eq("uf", uf)
                    .execute(),
                    label=f"cidade {mc}/{uf}",
                )
                if i % 200 == 0:
                    print(f"  cidade grupos {i}/{len(grupos)}", flush=True)
            cidade_updates = len(grupos)
        else:
            for (mc, uf), novo in list(grupos.items())[:5]:
                print(f"  [dry-run] {mc}/{uf} -> {novo}")
            cidade_updates = len(grupos)

    # --- bairro: agrupa ids por valor sanitizado ---
    bairro_updates = 0
    if do_bairro:
        from collections import defaultdict

        by_novo: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            br = row.get("bairro")
            if not br or not isinstance(br, str):
                continue
            novo = formatar_bairro_exibicao(br)
            if novo and novo != br:
                by_novo[novo].append(row["id"])

        pending_ids = sum(len(v) for v in by_novo.values())
        print(f"bairros a corrigir: {pending_ids} linhas, {len(by_novo)} valores", flush=True)
        if dry_run:
            for novo, ids in list(by_novo.items())[:5]:
                print(f"  [dry-run] '{novo}' ({len(ids)} ids)")
            bairro_updates = pending_ids
        else:
            ops = 0
            client = sb
            for novo, ids in by_novo.items():
                for i in range(0, len(ids), 500):
                    chunk = ids[i : i + 500]
                    if ops and ops % 150 == 0:
                        client = _supabase_client()
                    _with_retries(
                        lambda c=client, chunk=chunk, novo=novo: c.table(
                            "cnpj_fitness_estabelecimentos"
                        )
                        .update({"bairro": novo})
                        .in_("id", chunk)
                        .execute(),
                        label=f"bairro {novo[:24]}",
                    )
                    bairro_updates += len(chunk)
                    ops += 1
                    if ops % 50 == 0:
                        print(
                            f"  bairros {bairro_updates}/{pending_ids}",
                            flush=True,
                        )

    return {
        "registros": len(rows),
        "cidade_grupos": cidade_updates,
        "bairro_linhas": bairro_updates,
        "ibge_miss": len(cidade_miss) if do_cidade else 0,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sanitiza cidade/bairro CNPJ fitness")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only-cidade", action="store_true")
    ap.add_argument("--only-bairro", action="store_true")
    args = ap.parse_args(argv)

    stats = sanitize(
        dry_run=args.dry_run,
        only_cidade=args.only_cidade,
        only_bairro=args.only_bairro,
    )
    print("done:", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
