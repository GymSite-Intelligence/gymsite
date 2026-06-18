"""Cascata de busca de imóveis comerciais (P1) — conserta a busca fraca:
o SearchAPI retornava PÁGINAS DE CATEGORIA do OLX (não anúncios) e sem lat/lon.

Nível 1: SearchAPI google_light com query OTIMIZADA (anúncio individual, exclui
categoria) → parser que descarta página de categoria e extrai área/preço.
Geocoding: Nominatim (grátis) preenche lat/lon → habilita zoneamento.
Ranking: score composto (área na faixa + preço + zona + boost de fonte).

TODO dado (subdomínios UF, padrões de categoria, pesos de ranking, boost) vem de
catalogos_metodologia via import — nada inline (regra: dado que gera insight = tabela).
Níveis 2 (Apify) e 3 (Places) ficam como ganchos opcionais.
"""
from __future__ import annotations

import logging
import os
import re

import httpx

logger = logging.getLogger("gymsite.listing_cascata")


def montar_query_otimizada(cidade: str, bairro: str, uf: str,
                           *, tipo_imovel: str = "galpão prédio loja sala comercial",
                           tipo_negocio: str = "alugar") -> str:
    """Query SearchAPI p/ ANÚNCIO INDIVIDUAL (não página de categoria). Subdomínio
    estadual do OLX (catálogo) + exclusão dos termos de categoria + 'R$' força preço."""
    from tools.catalogos import catalogo_map

    sub = (catalogo_map("olx_subdominio_uf").get((uf or "").upper()) or "www")
    return (f'site:{sub}.olx.com.br {tipo_imovel} {tipo_negocio} '
            f'{bairro} {cidade} "R$" -listagem -categoria -busca -resultados')


def _eh_categoria(url: str, titulo: str) -> bool:
    from tools.catalogos import catalogo_lista

    blob = f"{url} {titulo}".lower()
    return any(p.lower() in blob for p in catalogo_lista("listing_categoria_pattern"))


def extrair_dados_listing(result: dict) -> dict | None:
    """Resultado do SearchAPI → dado estruturado. None se for página de categoria."""
    url = str(result.get("link") or "")
    titulo = str(result.get("title") or "")
    snippet = str(result.get("snippet") or "")
    if not url or _eh_categoria(url, titulo):
        return None
    area = None
    m = re.search(r"(\d{2,5})\s*m[²2]", snippet, re.IGNORECASE)
    if m:
        area = int(m.group(1))
    preco = None
    mp = re.search(r"R\$\s*([\d.]+(?:,\d+)?)", snippet)
    if mp:
        t = mp.group(1).replace(".", "").replace(",", ".")
        try:
            preco = float(t)
        except ValueError:
            preco = None
        # Sanity: aluguel comercial mensal ~R$1k–100k. >100k = preço de VENDA misturado
        # no snippet (não é aluguel) → descarta o preço, mantém o imóvel.
        if preco is not None and not (1000 <= preco <= 100000):
            preco = None
    return {
        "fonte": "SearchAPI_OLX", "url": url, "titulo": titulo[:120], "snippet": snippet[:300],
        "area_m2": area, "preco": preco, "bairro": None,
        "endereco": None, "latitude": None, "longitude": None,
    }


def buscar_listings_searchapi(cidade: str, bairro: str, uf: str, **kw) -> list[dict]:
    """Nível 1: SearchAPI google_light com a query otimizada → anúncios individuais."""
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return []
    q = montar_query_otimizada(cidade, bairro, uf, **kw)
    try:
        from tools.api_cost_tracker import track_api_call

        with track_api_call("listing_cascata", "searchapi_google_light", 1):
            with httpx.Client(timeout=25) as c:
                data = c.get("https://www.searchapi.io/api/v1/search",
                             params={"engine": "google_light", "q": q, "gl": "br", "hl": "pt-br"},
                             headers={"Authorization": f"Bearer {key}"}).json()
    except Exception as exc:
        logger.debug("listing searchapi '%s': %s", q, exc)
        return []
    out = []
    for r in (data.get("organic_results") or [])[:15]:
        d = extrair_dados_listing(r) if isinstance(r, dict) else None
        if d:
            out.append(d)
    return out


def geocodar_candidatos(candidatos: list[dict], cidade: str, bairro: str, uf: str) -> list[dict]:
    """Nominatim preenche lat/lon nos candidatos sem coordenada (habilita zoneamento)."""
    from tools.nominatim_geocoder import nominatim_geocode

    for c in candidatos:
        if c.get("latitude") is not None and c.get("longitude") is not None:
            continue
        end = c.get("endereco") or f"{c.get('bairro') or bairro}, {cidade}, {uf}, Brasil"
        geo = nominatim_geocode(end)
        if geo:
            c["latitude"], c["longitude"] = geo["lat"], geo["lon"]
            c["endereco"] = c.get("endereco") or geo.get("display_name")
            c["geocode_fonte"] = "nominatim"
    return candidatos


def rankear_candidatos(candidatos: list[dict], area_min: int, area_max: int) -> list[dict]:
    """Score composto (pesos do catálogo): área na faixa + preço + zona + boost de fonte."""
    from tools.catalogos import catalogo_num

    pesos = catalogo_num("listing_ranking_peso")
    boost = catalogo_num("listing_fonte_boost")

    def _score(c: dict) -> float:
        s = 0.0
        area = c.get("area_m2") or 0
        if area and area_min <= area <= area_max:
            s += pesos.get("area_na_faixa", 2.0)
        elif area:
            s += pesos.get("area_fora_faixa", 1.0)
        if c.get("preco"):
            s += pesos.get("tem_preco", 1.0)
        compat = (c.get("compatibilidade") or "").upper()
        if compat == "PERMISSIVO":
            s += pesos.get("zona_permissivo", 3.0)
        elif compat == "CONDICIONADO":
            s += pesos.get("zona_condicionado", 1.0)
        elif compat == "RESTRITO":
            s += pesos.get("zona_restrito", -5.0)
        s += boost.get(c.get("fonte", ""), 0.0)
        return round(s, 1)

    for c in candidatos:
        c["score_listing"] = _score(c)
    return sorted(candidatos, key=lambda x: x.get("score_listing", 0), reverse=True)


def buscar_candidatos_cascata(cidade: str, bairro: str, uf: str,
                              area_m2_min: int, area_m2_max: int, **kw) -> list[dict]:
    """Orquestra a cascata P1: SearchAPI otimizado → Nominatim (lat/lon) → ranking.
    Níveis 2 (Apify) e 3 (Places) são ganchos futuros (precisam APIFY_TOKEN / custo)."""
    cands = buscar_listings_searchapi(cidade, bairro, uf, **kw)
    cands = geocodar_candidatos(cands, cidade, bairro, uf)
    cands = rankear_candidatos(cands, area_m2_min, area_m2_max)
    return cands
