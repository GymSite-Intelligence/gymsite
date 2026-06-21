"""seed_bairros_municipio — pré-popula o cache de bairros dos municípios prioritários.

Para cada (município, UF) força a varredura Places + persistência em
`bairros_municipio`, pra que o form de Novo Relatório nunca pague Places ao vivo
nesses municípios. Idempotente: municípios já varridos são pulados (a própria
listar_bairros serve do DB sem re-harvest).

Requer no ambiente: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e GOOGLE_MAPS_API_KEY.

Uso:
  python -m scripts.seed_bairros_municipio                         # lista padrão
  python -m scripts.seed_bairros_municipio "Fortaleza:CE,Eusébio:CE"
"""
from __future__ import annotations

import sys

from tools.bairros_municipio import listar_bairros

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Municípios prioritários (capitais/regiões com mais relatórios). Editável via arg.
PRIORITARIOS: list[tuple[str, str]] = [
    ("Fortaleza", "CE"),
    ("Eusébio", "CE"),
    ("Caucaia", "CE"),
    ("Maracanaú", "CE"),
    ("São Paulo", "SP"),
    ("Rio de Janeiro", "RJ"),
    ("Belo Horizonte", "MG"),
    ("Curitiba", "PR"),
    ("Porto Alegre", "RS"),
    ("Salvador", "BA"),
    ("Recife", "PE"),
    ("Brasília", "DF"),
    ("Niterói", "RJ"),
]


def _parse_arg(arg: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for par in arg.split(","):
        if ":" in par:
            mun, uf = par.split(":", 1)
            out.append((mun.strip(), uf.strip()))
    return out


def main() -> int:
    alvos = _parse_arg(sys.argv[1]) if len(sys.argv) > 1 else PRIORITARIOS
    print(f"Pré-seed de bairros: {len(alvos)} municípios")
    total = 0
    for municipio, uf in alvos:
        r = listar_bairros(municipio, uf)
        n = len(r.get("bairros", []))
        total += n
        marca = {"db": "cache", "places": "varrido", "places-nodb": "SEM-PERSIST"}.get(
            r.get("fonte", ""), r.get("fonte", "")
        )
        erro = f" — ERRO: {r['erro']}" if r.get("erro") else ""
        print(f"  {municipio}/{uf}: {n} bairros [{marca}]{erro}")
    print(f"Total: {total} bairros em {len(alvos)} municípios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
