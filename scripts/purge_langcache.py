#!/usr/bin/env python3
"""
Purge seguro do LangCache via SDK oficial.

NÃO use redis-cli KEYS 'positioning_a9:*' — LangCache é API semântica; chaves
Redis internas não seguem o texto do prompt.

Uso:
  python scripts/purge_langcache.py --dry-run
  python scripts/purge_langcache.py --flush
  python scripts/purge_langcache.py --agent a9
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge LangCache")
    parser.add_argument("--dry-run", action="store_true", help="Apenas valida credenciais")
    parser.add_argument("--flush", action="store_true", help="Limpa todo o cache")
    parser.add_argument(
        "--agent",
        metavar="ID",
        help="Purge seletivo por atributo agent (ex: a9)",
    )
    args = parser.parse_args()

    try:
        from tools.langcache_client import is_langcache_configured, langcache_session
    except ModuleNotFoundError as e:
        if "langcache" in str(e):
            print(
                "Pacote 'langcache' ausente neste Python. Use:\n"
                "  .venv\\Scripts\\python scripts/purge_langcache.py ...\n"
                "  ou: pip install -r requirements.txt",
                file=sys.stderr,
            )
            sys.exit(1)
        raise

    if not is_langcache_configured():
        print("LangCache nao configurado. Verifique .env", file=sys.stderr)
        sys.exit(1)

    cache_id = os.getenv("LANGCACHE_CACHE_ID", "").strip()
    print(f"Credenciais LangCache validas | cache_id={cache_id[:8]}...")

    if args.dry_run:
        print("Dry-run completo. Use --flush ou --agent <id>.")
        return

    if args.agent:
        agent_id = args.agent.strip().lower()
        if not agent_id:
            print("agent vazio", file=sys.stderr)
            sys.exit(1)
        confirm = input(
            f"Isso apagara entradas com agent={agent_id!r}. Confirme 'yes': "
        )
        if confirm.strip().lower() != "yes":
            print("Cancelado")
            return
        try:
            from tools.langcache_client import _attributes_not_configured

            with langcache_session() as lc:
                if not hasattr(lc, "delete_query"):
                    print("SDK sem delete_query", file=sys.stderr)
                    sys.exit(1)
                try:
                    result = lc.delete_query(attributes={"agent": agent_id})
                except Exception as e:
                    if _attributes_not_configured(e):
                        print(
                            "Atributo 'agent' nao configurado no cache LangCache (Redis Cloud).\n"
                            "Configure prompt_hash e agent no console, ou use --flush.",
                            file=sys.stderr,
                        )
                        sys.exit(1)
                    raise
            print(f"Purge seletivo OK (agent={agent_id}): {result}")
        except Exception as e:
            print(f"Falha no purge seletivo: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.flush:
        print("Use --dry-run, --flush ou --agent <id>")
        return

    confirm = input(
        "Isso apagara TODO o cache (A0, A9, grounding). Confirme 'yes': "
    )
    if confirm.strip().lower() != "yes":
        print("Cancelado")
        return

    try:
        with langcache_session() as lc:
            if hasattr(lc, "flush"):
                result = lc.flush()
            elif hasattr(lc, "delete_query"):
                result = lc.delete_query()
            else:
                print("SDK nao suporta flush/delete_query", file=sys.stderr)
                sys.exit(1)
        print(f"Cache limpo com sucesso: {result}")
    except Exception as e:
        print(f"Falha no purge: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
