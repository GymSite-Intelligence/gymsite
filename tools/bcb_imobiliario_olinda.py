"""
Referência macro de mercado imobiliário via Olinda/BCB.

Camada auxiliar (Tier macro) para complementar o Tier 1 de portais municipais.
Consulta o recurso público `MercadoImobiliario` em Olinda e extrai o valor mais
recente por série (campo `Info`).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/"
    "MercadoImobiliario/versao/v1/odata/mercadoimobiliario"
)
_DEFAULT_TIMEOUT_S = 15.0


def _parse_data_olinda(raw: Any) -> Optional[str]:
    """Normaliza datas do Olinda para ISO AAAA-MM-DD."""
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        try:
            # Alguns serviços expõem epoch em ms/s.
            if raw > 10_000_000_000:
                dt = datetime.fromtimestamp(raw / 1000.0, tz=timezone.utc)
            else:
                dt = datetime.fromtimestamp(raw, tz=timezone.utc)
            return dt.date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(raw, str):
        return None

    # Formato /Date(1714694400000)/
    m = re.match(r"/Date\((\d+)\)/", raw)
    if m:
        try:
            millis = int(m.group(1))
            dt = datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc)
            return dt.date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None

    # Tenta ISO direto.
    try:
        # Corta hora caso venha "2024-05-01T00:00:00Z".
        iso = raw.split("T")[0]
        dt = datetime.fromisoformat(iso)
        return dt.date().isoformat()
    except ValueError:
        return None


def _parse_valor(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str):
        return None
    txt = raw.strip()
    if not txt:
        return None
    # Suporta "1.234,56" ou "1234.56".
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    else:
        txt = txt.replace(" ", "").replace(".", "")
    try:
        return float(txt)
    except ValueError:
        return None


def fetch_mercado_imobiliario_series(
    *,
    info_contains: Optional[List[str]] = None,
    top: int = 1000,
) -> Dict[str, Any]:
    """
    Consulta o recurso MercadoImobiliario em Olinda/BCB.

    info_contains: lista de substrings (case-insensitive) para filtrar `Info`.
    Retorno: dict com `ok`, `erro` (opcional), `series` (lista) e metadados.
    """
    params = {
        "$format": "json",
        "$top": str(top),
        "$orderby": "Data desc",
    }
    # Alguns gateways do Olinda não interpretam "+" como espaço em $orderby,
    # o que faz httpx (que codifica "Data desc" como "Data+desc") receber HTTP 400.
    # Montamos a query string manualmente para garantir "%20" como separador.
    query = f"$format=json&$top={top}&$orderby=Data%20desc"
    url = f"{_BASE_URL}?{query}"
    try:
        r = httpx.get(url, timeout=_DEFAULT_TIMEOUT_S)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("bcb_olinda: HTTP %s ao consultar %s", exc.response.status_code, url)
        return {
            "ok": False,
            "erro": f"HTTP {exc.response.status_code} ao consultar Olinda/BCB",
            "series": [],
            "fonte": "Banco Central do Brasil — MercadoImobiliario (Olinda)",
            "url_base": url,
            "params": params,
        }
    except httpx.RequestError as exc:
        logger.warning("bcb_olinda: erro de rede ao consultar %s — %s", url, exc)
        return {
            "ok": False,
            "erro": f"Erro de rede ao consultar Olinda/BCB: {exc}",
            "series": [],
            "fonte": "Banco Central do Brasil — MercadoImobiliario (Olinda)",
            "url_base": url,
            "params": params,
        }

    try:
        payload = r.json()
    except ValueError:
        logger.warning("bcb_olinda: resposta não-JSON de %s", url)
        return {
            "ok": False,
            "erro": "Resposta inválida do serviço Olinda/BCB (não-JSON).",
            "series": [],
            "fonte": "Banco Central do Brasil — MercadoImobiliario (Olinda)",
            "url_base": url,
            "params": params,
        }

    # Olinda padrão: {"value": [...]} — reserva fallback para outros formatos.
    rows: List[Dict[str, Any]] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("value"), list):
            rows = payload["value"]  # type: ignore[assignment]
        elif isinstance(payload.get("d", {}).get("results"), list):  # SAP OData compat.
            rows = payload["d"]["results"]  # type: ignore[index, assignment]

    if not rows:
        return {
            "ok": False,
            "erro": "Nenhuma série encontrada em MercadoImobiliario.",
            "series": [],
            "fonte": "Banco Central do Brasil — MercadoImobiliario (Olinda)",
            "url_base": url,
            "params": params,
        }

    filters = [s.lower() for s in (info_contains or []) if s]

    latest_by_info: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        info_raw = row.get("Info") or row.get("info")
        info = str(info_raw or "").strip()
        if not info:
            continue

        if filters and not any(f in info.lower() for f in filters):
            continue

        data_raw = row.get("Data") or row.get("data")
        data_iso = _parse_data_olinda(data_raw)
        valor = _parse_valor(row.get("Valor") or row.get("valor"))
        if data_iso is None or valor is None:
            continue

        prev = latest_by_info.get(info)
        if prev is None or (prev.get("data") or "") < data_iso:
            # URL específica da série filtrada por Info.
            info_filter = quote(info, safe="")
            serie_url = (
                f"{_BASE_URL}?$format=json&$select=Data,Info,Valor"
                f"&$filter=Info%20eq%20'{info_filter}'"
            )
            latest_by_info[info] = {
                "info": info,
                "data": data_iso,
                "valor": valor,
                "url": serie_url,
            }

    series = sorted(latest_by_info.values(), key=lambda s: s["info"].lower())

    return {
        "ok": True,
        "series": series,
        "fonte": "Banco Central do Brasil — MercadoImobiliario (Olinda)",
        "url_base": url,
        "params": params,
    }


def extrair_resumo_imobiliario(cidade_contexto: Optional[str] = None) -> Dict[str, Any]:
    """
    Extrai resumo macro imobiliário para relatórios.

    Retorna dict com séries brutas e destaques para financiamento/crédito
    direcionado, quando identificáveis pelos nomes das séries.
    """
    resp = fetch_mercado_imobiliario_series()
    if not resp.get("ok"):
        norte = (
            "Falha ao consultar referência macro imobiliária no Banco Central. "
            "Considere seguir com Tier 1 (portais) e checagem local."
        )
        if cidade_contexto:
            norte = norte + f" Contexto: {cidade_contexto}."
        return {
            "ok": False,
            "erro": resp.get("erro"),
            "fonte": resp.get("fonte"),
            "url_base": resp.get("url_base"),
            "cidade_contexto": cidade_contexto,
            "series": [],
            "destaques": {},
            "norte": norte,
        }

    series: List[Dict[str, Any]] = list(resp.get("series") or [])

    # Heurísticas simples pra achar séries relevantes para crédito imobiliário.
    destaques: Dict[str, Dict[str, Any]] = {}
    for s in series:
        nome = str(s.get("info") or "").lower()
        if not nome:
            continue

        if "financiamento" in nome and "imobili" in nome and "residencial" in nome:
            destaques.setdefault("financiamento_residencial", s)
        elif "financiamento" in nome and "imobili" in nome and "comercial" in nome:
            destaques.setdefault("financiamento_comercial", s)
        elif "crédito" in nome and "direcionado" in nome and "imobili" in nome:
            destaques.setdefault("credito_direcionado_total", s)

    # Limita quantidade de séries brutas pra não poluir relatórios.
    series_compactas = series[:30]

    cidade_label = f" para {cidade_contexto}" if cidade_contexto else ""
    if destaques:
        partes = []
        for chave, s in destaques.items():
            label = chave.replace("_", " ")
            data = s.get("data") or "data não informada"
            valor = s.get("valor")
            if isinstance(valor, (int, float)):
                valor_txt = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                valor_txt = str(valor)
            partes.append(f"{label} em {data}: {valor_txt}")
        norte = (
            f"Referência macro imobiliária{cidade_label} (BCB/Olinda). "
            + " | ".join(partes)
        )
    else:
        norte = (
            f"Referência macro imobiliária{cidade_label} obtida em BCB/Olinda "
            "sem identificar séries específicas de financiamento/com crédito direcionado. "
            "Use as séries listadas como pano de fundo qualitativo."
        )

    return {
        "ok": True,
        "fonte": resp.get("fonte"),
        "url_base": resp.get("url_base"),
        "cidade_contexto": cidade_contexto,
        "series": series_compactas,
        "destaques": destaques,
        "norte": norte,
    }

