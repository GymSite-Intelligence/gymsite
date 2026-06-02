"""PostgREST via httpx — avoids supabase-py import (shadowed by repo supabase/)."""
from __future__ import annotations

import os
from typing import Any

_DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def sb_headers() -> tuple[str, dict[str, str]]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY ausentes no .env")
    return url, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def create_relatorio_stub_postgrest(
    payload: Any,
    *,
    org_id: str | None = None,
    user_id: str | None = None,
) -> tuple[str, str | None]:
    """Same fields as api.create_relatorio_stub (status=queued)."""
    import httpx

    base, headers = sb_headers()
    resolved_org = (
        org_id
        or getattr(payload, "org_id", None)
        or os.getenv("SUPABASE_GYMSITE_ORG_ID")
        or _DEFAULT_ORG_ID
    )
    h = {**headers, "Prefer": "return=representation"}
    r = httpx.post(
        f"{base}/rest/v1/relatorios",
        headers=h,
        json={
            "org_id": resolved_org,
            "user_id": user_id,
            "tipo_relatorio": "prospeccao_academia",
            "status": "queued",
            "schema_version": "1.6",
        },
        timeout=60,
    )
    r.raise_for_status()
    rows = r.json()
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("falha ao criar header do relatorio")
    relatorio_id = rows[0]["id"]
    created_at = rows[0].get("created_at")

    uf = getattr(payload, "uf", None) or ""
    r2 = httpx.post(
        f"{base}/rest/v1/relatorio_inputs",
        headers=headers,
        json={
            "relatorio_id": relatorio_id,
            "cidade": payload.cidade,
            "uf": (uf[:2] or None),
            "bairro": payload.bairro,
            "area_m2_min": payload.area_m2_min,
            "area_m2_max": payload.area_m2_max,
            "tamanho_preset": payload.tamanho_preset,
            "publico_alvo": payload.publico_alvo,
            "genero_alvo": payload.genero_alvo,
            "tipo_negocio": payload.tipo_negocio,
            "estacionamento_obrigatorio": payload.estacionamento_obrigatorio,
            "bairros_indicados": getattr(payload, "bairros_indicados", None),
            "a0_research_provider": (getattr(payload, "a0_research_provider", None) or "auto")[:16],
        },
        timeout=60,
    )
    r2.raise_for_status()
    return relatorio_id, created_at


def fetch_relatorio_status(uuid: str) -> dict[str, Any] | None:
    import httpx

    base, headers = sb_headers()
    r = httpx.get(
        f"{base}/rest/v1/relatorios",
        headers=headers,
        params={
            "id": f"eq.{uuid}",
            "select": "id,status,erro_mensagem,tempo_execucao_segundos",
            "limit": "1",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list) and data:
        return data[0]
    return None


def fetch_posicionamento_flag(uuid: str) -> bool:
    import httpx

    base, headers = sb_headers()
    r = httpx.get(
        f"{base}/rest/v1/relatorio_outputs",
        headers=headers,
        params={
            "relatorio_id": f"eq.{uuid}",
            "select": "posicionamento_estrategico",
            "limit": "1",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or not data:
        return False
    pos = data[0].get("posicionamento_estrategico")
    return isinstance(pos, dict) and bool(pos)

