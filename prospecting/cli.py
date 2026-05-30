"""
CLI do módulo de prospecção.

Uso:
    python -m prospecting.cli --cidade Fortaleza --uf CE
    python -m prospecting.cli --cidade Fortaleza --uf CE --dry-run
    python -m prospecting.cli --cidade Fortaleza --uf CE --dias 60 --limit 200
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prospecting.engine import run_prospeccao


def main() -> int:
    parser = argparse.ArgumentParser(description="Módulo de Prospecção CNPJ × CNO")
    parser.add_argument("--cidade", required=True, help="Município")
    parser.add_argument("--uf", default="CE", help="UF (default: CE)")
    parser.add_argument("--dias", type=int, default=90, help="Janela de dias CNPJ (default: 90)")
    parser.add_argument("--limit", type=int, default=500, help="Limite de entrantes (default: 500)")
    parser.add_argument("--cno-dir", type=Path, default=None, help="Diretório CSV do CNO")
    parser.add_argument("--org-id", default=None, help="UUID da organização")
    parser.add_argument("--webhook-url", default=None, help="URL do webhook Claw (override)")
    parser.add_argument("--dry-run", action="store_true", help="Não persiste nem envia webhook")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")

    args = parser.parse_args()

    result = run_prospeccao(
        cidade=args.cidade,
        uf=args.uf,
        dias=args.dias,
        limit=args.limit,
        cno_dir=args.cno_dir,
        org_id=args.org_id,
        webhook_url=args.webhook_url,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        stats = result.get("stats", {})
        print(f"✓ Prospecção finalizada: {args.cidade}/{args.uf}")
        print(f"  Total match CNO: {stats.get('total_match', 0)}")
        print(f"  Qualificados (score ≥ min): {stats.get('qualificados', 0)}")
        print(f"  Persistidos: {stats.get('persistidos', 0)}")
        print(f"  Webhooks entregues: {stats.get('webhooks_entregues', 0)}")
        print(f"  Webhooks falhos: {stats.get('webhooks_falhos', 0)}")
        print(f"  Webhooks skipped: {stats.get('webhooks_skipped', 0)}")
        if args.dry_run:
            print("  [DRY-RUN] Nada foi persistido.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
