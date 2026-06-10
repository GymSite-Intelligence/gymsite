"""
Cliente mínimo CKAN Action API v3 (RPC JSON).

Uso: descoberta de pacotes (dados.gov.br e portais municipais).
Consumo de dados: resolver resource URL → APIs oficiais (IBGE, CVM), não só Solr.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PORTAL = "https://dados.gov.br"
DEFAULT_TIMEOUT_S = 25.0


class CkanApiError(Exception):
    def __init__(self, action: str, message: str, *, help_text: str | None = None):
        super().__init__(f"CKAN {action}: {message}")
        self.action = action
        self.help_text = help_text


def ckan_action(
    action: str,
    params: dict[str, Any] | None = None,
    *,
    portal_base: str = DEFAULT_PORTAL,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Any:
    """
    POST /api/3/action/<action> com body JSON.

    Retorna `result` quando success=true; senão levanta CkanApiError.
    """
    base = portal_base.rstrip("/")
    url = f"{base}/api/3/action/{action}"
    body = params or {}
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.post(url, json=body)
    except httpx.HTTPError as exc:
        raise CkanApiError(action, str(exc)) from exc

    if resp.status_code >= 400:
        raise CkanApiError(action, f"HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise CkanApiError(action, "resposta não é JSON") from exc

    if not payload.get("success"):
        err = payload.get("error") or {}
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise CkanApiError(action, msg or "success=false", help_text=payload.get("help"))

    return payload.get("result")


def package_search(
    query: str,
    *,
    rows: int = 10,
    start: int = 0,
    fq: str | None = None,
    portal_base: str = DEFAULT_PORTAL,
) -> dict[str, Any]:
    """Busca facetada Solr via CKAN."""
    params: dict[str, Any] = {"q": query, "rows": rows, "start": start}
    if fq:
        params["fq"] = fq
    result = ckan_action("package_search", params, portal_base=portal_base)
    if not isinstance(result, dict):
        return {"count": 0, "results": []}
    return result


def package_show(
    package_id: str,
    *,
    portal_base: str = DEFAULT_PORTAL,
) -> dict[str, Any]:
    """Metadados completos de um dataset (package)."""
    result = ckan_action(
        "package_show",
        {"id": package_id},
        portal_base=portal_base,
    )
    if not isinstance(result, dict):
        raise CkanApiError("package_show", "result inválido")
    return result


def discover_demografia_queries(cidade: str, uf: str) -> list[str]:
    """Queries sugeridas para batch (demografia / bairro / censo)."""
    cidade = (cidade or "").strip()
    uf = (uf or "").strip().upper()
    return [
        f"{cidade} renda bairro",
        f"{cidade} {uf} censo demografia",
        f"{cidade} populacao ibge",
        "ipece fortaleza bairros" if cidade.lower() == "fortaleza" else f"ipece {cidade}",
    ]


def search_datasets_for_city(
    cidade: str,
    uf: str,
    *,
    portal_base: str = DEFAULT_PORTAL,
    max_per_query: int = 5,
) -> list[dict[str, Any]]:
    """
    Agrega resultados de package_search sem duplicar por id.
    Retorna lista resumida: id, name, title, organization, url.
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for q in discover_demografia_queries(cidade, uf):
        try:
            data = package_search(q, rows=max_per_query, portal_base=portal_base)
        except CkanApiError as exc:
            logger.warning("package_search falhou q=%s: %s", q, exc)
            continue
        for pkg in data.get("results") or []:
            if not isinstance(pkg, dict):
                continue
            pid = str(pkg.get("id") or pkg.get("name") or "")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            org = pkg.get("organization") or {}
            out.append(
                {
                    "id": pid,
                    "name": pkg.get("name"),
                    "title": pkg.get("title"),
                    "organization": org.get("title") if isinstance(org, dict) else org,
                    "portal": portal_base,
                }
            )
    return out
