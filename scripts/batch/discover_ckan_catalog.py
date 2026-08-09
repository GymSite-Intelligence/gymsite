#!/usr/bin/env python3
"""Descobre datasets CKAN / dados.gov — scout MACRO, ORG_SEED ou city.

Federal (dados.gov.br) usa API pública + ORG_SEED (Action /api/3 = 401).

Macro:
  python scripts/batch/discover_ckan_catalog.py --mode macro
  python scripts/batch/discover_ckan_catalog.py --mode macro --groups Habitação,Urbanismo

Org seed (idOrganizacao explícito):
  python scripts/batch/discover_ckan_catalog.py --mode org
  python scripts/batch/discover_ckan_catalog.py --mode org --orgs ibge,ministerio-das-cidades
  python scripts/batch/discover_ckan_catalog.py --mode org --nome censo,habit --require-group

City (municipal Action / legado):
  python scripts/batch/discover_ckan_catalog.py --mode city --cidade Fortaleza --uf CE

Vocabulário: cgugovbr/guia-ckan PREENCHIMENTO-CKAN.md
Federal exige CKAN_API_KEY (header chave-api-dados-abertos).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "ckan_catalog"


def _parse_csv(raw: str | None) -> list[str] | None:
    if not raw or not raw.strip():
        return None
    return [g.strip() for g in raw.split(",") if g.strip()]


def _expand_org_aliases(slugs: list[str] | None) -> list[str] | None:
    """Atalhos curtos → slug ORG_SEED."""
    if not slugs:
        return None
    aliases = {
        "ibge": "instituto-brasileiro-de-geografia-e-estatistica-ibge",
        "mcid": "ministerio-das-cidades",
        "cidades": "ministerio-das-cidades",
        "df": "distrito-federal",
        "bh": "prefeitura-de-belo-horizonte-pbh",
        "pbh": "prefeitura-de-belo-horizonte-pbh",
        "rj": "estado-do-rio-de-janeiro",
        "fortaleza": "prefeitura-municipal-de-fortaleza",
        "ana": "agencia-nacional-de-aguas-e-saneamento-basico",
        "me": "ministerio-da-economia-me",
        "al": "estado-de-alagoas-al",
    }
    out: list[str] = []
    for s in slugs:
        key = s.strip().lower()
        out.append(aliases.get(key, s.strip()))
    return out


def main() -> int:
    p = argparse.ArgumentParser(
        description="CKAN/dados.gov catalog scout: macro | org | city",
    )
    p.add_argument(
        "--mode",
        choices=("macro", "org", "city", "auto"),
        default="auto",
        help="auto=city se --cidade; senão macro. org=ORG_SEED explícito",
    )
    p.add_argument("--cidade", default=None, help="Obrigatório em --mode city")
    p.add_argument("--uf", default="CE")
    p.add_argument(
        "--portal",
        default=None,
        help="Força portal; city→municipal; macro federal→API pública",
    )
    p.add_argument(
        "--groups",
        default=None,
        help="Temas CGU separados por vírgula (macro/org). Default: CGU_GROUPS_DEMO_GEO",
    )
    p.add_argument(
        "--orgs",
        default=None,
        help="Slugs ORG_SEED (ou alias ibge,mcid,df,bh,rj,fortaleza,ipea,ana)",
    )
    p.add_argument(
        "--nome",
        default=None,
        help="Queries nomeConjuntoDados (csv). Org/macro; default=hints do tema",
    )
    p.add_argument(
        "--cobertura",
        default=None,
        choices=("FEDERAL", "ESTADUAL", "MUNICIPAL"),
        help="Filtro client-side coberturaEspacial",
    )
    p.add_argument(
        "--valor-cobertura",
        default=None,
        help="UF (ESTADUAL) ou IBGE 6 dígitos (MUNICIPAL)",
    )
    p.add_argument("--q", default="*:*", help="Query Solr (só Action municipal)")
    p.add_argument(
        "--rows",
        type=int,
        default=10,
        help="rows por grupo (Action) / influencia páginas nome (público)",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=8,
        help="Máx páginas por org (~15 itens/página na API pública)",
    )
    p.add_argument(
        "--require-group",
        action="store_true",
        help="Descarta datasets cujo tema não cruza --groups",
    )
    p.add_argument(
        "--no-enrich",
        action="store_true",
        help="Não hidrata detalhe (rápido; IPEA fica sem título útil)",
    )
    args = p.parse_args()

    from tools.ckan_client import (
        CGU_GROUPS_DEMO_GEO,
        ORG_SEED,
        ORG_SEED_PRIORITY,
        search_datasets_for_city,
        search_datasets_macro,
        search_datasets_org_seed,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    mode = args.mode
    if mode == "auto":
        mode = "city" if args.cidade else "macro"

    groups = _parse_csv(args.groups)
    org_slugs = _expand_org_aliases(_parse_csv(args.orgs))
    nome_queries = _parse_csv(args.nome)

    if mode == "city":
        if not args.cidade:
            p.error("--mode city exige --cidade")
        datasets = search_datasets_for_city(
            args.cidade, args.uf, portal_base=args.portal
        )
        slug = f"{args.cidade}_{args.uf}".lower().replace(" ", "_")
        out = OUT_DIR / f"{slug}.json"
        payload = {
            "mode": "city",
            "scouted_at": now,
            "cidade": args.cidade,
            "uf": args.uf,
            "portal": args.portal,
            "datasets_matched": datasets,
            "count": len(datasets),
        }
    elif mode == "org":
        datasets = search_datasets_org_seed(
            org_slugs=org_slugs,
            nome_queries=nome_queries,
            groups=groups or list(CGU_GROUPS_DEMO_GEO),
            cobertura=args.cobertura,
            valor_cobertura=args.valor_cobertura,
            max_pages_per_org=args.max_pages,
            enrich=not args.no_enrich,
            require_group_match=args.require_group,
        )
        parts = ["org"]
        if org_slugs:
            parts.append("-".join(s.split("-")[0] for s in org_slugs[:3]))
        else:
            parts.append("priority")
        if args.cobertura:
            parts.append(args.cobertura.lower())
        slug = "_".join(parts)
        out = OUT_DIR / f"{slug}.json"
        payload = {
            "mode": "org",
            "api": "publico",
            "scouted_at": now,
            "org_slugs": org_slugs or list(ORG_SEED_PRIORITY),
            "org_seed_keys": list(ORG_SEED.keys()),
            "groups": groups or list(CGU_GROUPS_DEMO_GEO),
            "nome_queries": nome_queries,
            "cobertura": args.cobertura,
            "valor_cobertura": args.valor_cobertura,
            "require_group_match": args.require_group,
            "datasets_matched": datasets,
            "count": len(datasets),
        }
    else:
        datasets = search_datasets_macro(
            groups=groups,
            q=args.q,
            cobertura=args.cobertura,
            valor_cobertura=args.valor_cobertura,
            rows_per_group=args.rows,
            portal_base=args.portal,
            enrich=not args.no_enrich,
            org_slugs=org_slugs,
            max_pages_per_org=args.max_pages,
            require_group_match=args.require_group,
        )
        parts = ["macro"]
        if args.cobertura:
            parts.append(args.cobertura.lower())
        if args.valor_cobertura:
            parts.append(str(args.valor_cobertura).lower())
        if groups:
            parts.append(
                "-".join(g.lower().replace(" ", "_")[:12] for g in groups[:3])
            )
        else:
            parts.append("demo_geo")
        slug = "_".join(parts)
        out = OUT_DIR / f"{slug}.json"
        payload = {
            "mode": "macro",
            "api": "publico" if not args.portal or "dados.gov.br" in args.portal else "action",
            "scouted_at": now,
            "vocab_ref": "cgugovbr/guia-ckan PREENCHIMENTO-CKAN.md",
            "groups": groups or list(CGU_GROUPS_DEMO_GEO),
            "org_slugs": org_slugs,
            "cobertura": args.cobertura,
            "valor_cobertura": args.valor_cobertura,
            "q": args.q,
            "portal": args.portal,
            "require_group_match": args.require_group,
            "datasets_matched": datasets,
            "count": len(datasets),
        }

    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"mode={mode} found={len(datasets)} written={out}")
    for d in datasets[:8]:
        title = d.get("title")
        pid = d.get("id")
        extra = ""
        if d.get("matched_group"):
            extra = f" [{d['matched_group']}]"
        if d.get("matched_via"):
            extra += f" via={d['matched_via']}"
        if d.get("join_uf"):
            extra += f" uf={d['join_uf']}"
        if d.get("join_ibge6"):
            extra += f" ibge6={d['join_ibge6']}"
        print(f"  - {title} ({pid}){extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
