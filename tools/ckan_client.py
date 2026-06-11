"""
Cliente mínimo CKAN Action API v3 (RPC JSON).

Uso: descoberta de pacotes (dados.gov.br e portais municipais).
Consumo de dados: resolver resource URL → APIs oficiais (IBGE, CVM), não só Solr.

Notas de campo (2026-06-12):
- Ações side-effect-free (package_search/show, status_show) vão por GET —
  doc CKAN 2.11 permite e gateways costumam tratar POST anônimo pior.
- dados.gov.br fica atrás de gateway federal que exige a chave
  "chave-api-dados-abertos" em TODAS as ações (até status_show). Configurar
  CKAN_API_KEY no .env quando obtida; sem ela, usar portais municipais
  diretos (dados.fortaleza.ce.gov.br responde aberto, testado).
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PORTAL = "https://dados.gov.br"
DEFAULT_TIMEOUT_S = 25.0

# Portais municipais/estaduais CKAN abertos, por cidade (lowercase).
PORTAIS_MUNICIPAIS = {
    "fortaleza": "https://dados.fortaleza.ce.gov.br",
}

_ACOES_GET = {"package_search", "package_show", "status_show", "organization_list", "group_list", "tag_list"}


def _auth_headers(portal_base: str) -> dict[str, str]:
    """Header de autenticação por portal. dados.gov.br usa chave do gateway
    federal; CKAN puro usa Authorization."""
    key = os.getenv("CKAN_API_KEY", "").strip()
    if not key:
        return {}
    header = os.getenv("CKAN_API_KEY_HEADER", "").strip()
    if not header:
        header = "chave-api-dados-abertos" if "dados.gov.br" in portal_base else "Authorization"
    return {header: key}


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
    GET (ações de leitura) ou POST /api/3/action/<action>.

    Retorna `result` quando success=true; senão levanta CkanApiError.
    """
    base = portal_base.rstrip("/")
    url = f"{base}/api/3/action/{action}"
    body = params or {}
    headers = {"User-Agent": "gymsite-intelligence/1.0", **_auth_headers(base)}
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True, headers=headers) as client:
            if action in _ACOES_GET:
                resp = client.get(url, params=body)
            else:
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


def portais_para_cidade(cidade: str) -> list[str]:
    """Portais a consultar, em ordem: municipal aberto primeiro, federal depois
    (o federal exige CKAN_API_KEY — sem ela, é pulado com 1 warning)."""
    portais = []
    municipal = PORTAIS_MUNICIPAIS.get((cidade or "").strip().lower())
    if municipal:
        portais.append(municipal)
    if os.getenv("CKAN_API_KEY", "").strip():
        portais.append(DEFAULT_PORTAL)
    elif not municipal:
        portais.append(DEFAULT_PORTAL)
    return portais


def search_datasets_for_city(
    cidade: str,
    uf: str,
    *,
    portal_base: str | None = None,
    max_per_query: int = 5,
) -> list[dict[str, Any]]:
    """
    Agrega resultados de package_search sem duplicar por id, varrendo o portal
    municipal (quando mapeado) e o federal (quando autenticado).
    Retorna lista resumida: id, name, title, organization, portal.
    """
    portais = [portal_base] if portal_base else portais_para_cidade(cidade)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for portal in portais:
        out.extend(_search_one_portal(cidade, uf, portal, max_per_query, seen))
    return out


def _search_one_portal(
    cidade: str,
    uf: str,
    portal: str,
    max_per_query: int,
    seen: set[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for q in discover_demografia_queries(cidade, uf):
        try:
            data = package_search(q, rows=max_per_query, portal_base=portal)
        except CkanApiError as exc:
            logger.warning("package_search falhou portal=%s q=%s: %s", portal, q, exc)
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
                    "portal": portal,
                }
            )
    return out
