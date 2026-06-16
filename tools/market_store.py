"""
Armazém Supabase de market_bundles + snapshots (opt-in).

Substitui FS-local quando MARKET_BUNDLE_SUPABASE é truthy E há credenciais.
Tudo é best-effort: nenhuma função levanta exceção — falha vira None/False e o
chamador cai no FS. Mantém local dev / testes intactos (flag off por padrão).
"""
from __future__ import annotations

import os
from typing import Any

_TRUTHY = {"1", "true", "yes", "on"}


def supabase_enabled() -> bool:
    if (os.environ.get("MARKET_BUNDLE_SUPABASE") or "").strip().lower() not in _TRUTHY:
        return False
    return bool(os.environ.get("SUPABASE_URL") and _service_key())


def _service_key() -> str | None:
    return (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )


_CLIENT: Any | None = None


def _client() -> Any | None:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    try:
        from tools.supabase_client import load_create_client

        create_client = load_create_client()
        _CLIENT = create_client(os.environ["SUPABASE_URL"], _service_key())
        return _CLIENT
    except Exception as e:  # pragma: no cover - ambiente sem credencial
        print(f"[market_store] client indisponível: {type(e).__name__}: {e}")
        return None


def upsert_bundle(slug: str, bundle: dict[str, Any]) -> bool:
    """Grava/atualiza um bundle na tabela. Retorna sucesso."""
    if not supabase_enabled():
        return False
    cli = _client()
    if cli is None:
        return False
    loc = bundle.get("local") or {}
    row = {
        "slug": slug,
        "cidade": loc.get("cidade") or "",
        "bairro": loc.get("bairro"),
        "uf": (loc.get("uf") or "").upper(),
        "gerado_em": bundle.get("gerado_em"),
        "valido_ate": bundle.get("valido_ate"),
        "stale": bool(bundle.get("stale", False)),
        "payload": bundle,
    }
    try:
        cli.table("market_bundles").upsert(row, on_conflict="slug").execute()
        return True
    except Exception as e:
        print(f"[market_store] upsert_bundle falhou ({slug}): {type(e).__name__}: {e}")
        return False


def fetch_bundle(slug: str) -> dict[str, Any] | None:
    """Lê payload do bundle por slug. None se ausente/erro."""
    if not supabase_enabled():
        return None
    cli = _client()
    if cli is None:
        return None
    try:
        res = cli.table("market_bundles").select("payload").eq("slug", slug).limit(1).execute()
        data = getattr(res, "data", None) or []
        if data and isinstance(data[0].get("payload"), dict):
            return data[0]["payload"]
        return None
    except Exception as e:
        print(f"[market_store] fetch_bundle falhou ({slug}): {type(e).__name__}: {e}")
        return None


def upsert_snapshot(nome: str, payload: dict[str, Any]) -> bool:
    if not supabase_enabled():
        return False
    cli = _client()
    if cli is None:
        return False
    row = {"nome": nome, "payload": payload, "gerado_em": payload.get("gerado_em")}
    try:
        cli.table("market_snapshots").upsert(row, on_conflict="nome").execute()
        return True
    except Exception as e:
        print(f"[market_store] upsert_snapshot falhou ({nome}): {type(e).__name__}: {e}")
        return False


def fetch_snapshot(nome: str) -> dict[str, Any] | None:
    if not supabase_enabled():
        return None
    cli = _client()
    if cli is None:
        return None
    try:
        res = cli.table("market_snapshots").select("payload").eq("nome", nome).limit(1).execute()
        data = getattr(res, "data", None) or []
        if data and isinstance(data[0].get("payload"), dict):
            return data[0]["payload"]
        return None
    except Exception as e:
        print(f"[market_store] fetch_snapshot falhou ({nome}): {type(e).__name__}: {e}")
        return None
