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


import math
import unicodedata


def _norm_bairro(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def extrair_bairro_anuncio(titulo: str, snippet: str = "") -> str | None:
    """Bairro embutido no anúncio OLX. Formato típico: 'Apartamento à venda -
    Meireles, Fortaleza - CE 123'. Pega o token entre o 1º ' - ' e a vírgula.
    É o sinal mais forte e barato de bairro real (sem geocode)."""
    blob = f"{titulo or ''}"
    # `.` no char class captura bairro com abreviação (ex: "Eng. Luciano Cavalcante",
    # "Pe. Cícero") — sem isso o regex parava no ponto e devolvia None, deixando o
    # listing passar só pelo raio (vazava bairro adjacente, ex: Eng. Luciano em Cocó).
    m = re.search(r"-\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'.\s]{2,40}?)\s*,", blob)
    if m:
        cand = m.group(1).strip(" .")
        # descarta capturas óbvias de tipo de imóvel (não é bairro)
        if not re.search(r"\b(apartamento|casa|sala|loja|galp|terreno|ponto|quarto|comercial)\b",
                         _norm_bairro(cand)):
            return cand
    return None


def filtrar_por_bairro(candidatos: list[dict], cidade: str, bairro: str, uf: str) -> list[dict]:
    """Descarta listings que NÃO caem no bairro alvo (vazamento do SearchAPI: traz
    anúncio de Meireles/Guararapes/Caucaia numa busca de Cocó). Dois sinais:
      1) bairro textual do título OLX ≠ alvo → dropa (barato, sem API);
      2) geocode do anúncio: suburb/neighbourhood do Nominatim ≠ alvo, OU distância
         ao centroide do bairro > raio (param) → dropa.
    Sobreviventes ficam com lat/lon REAL do anúncio (não centroide do bairro)."""
    from tools.nominatim_geocoder import nominatim_geocode
    from tools.parametros_metodologia import param

    alvo = _norm_bairro(bairro)
    if not alvo:
        return candidatos
    raio = param("cascata_raio_bairro_km") or 2.0

    # Centroide do bairro alvo (uma vez) p/ a checagem de raio.
    cen = nominatim_geocode(f"{bairro}, {cidade}, {uf}, Brasil")
    clat = cen["lat"] if cen else None
    clon = cen["lon"] if cen else None

    out: list[dict] = []
    for c in candidatos:
        # (1) bairro textual do título
        bt = extrair_bairro_anuncio(c.get("titulo") or "", c.get("snippet") or "")
        if bt:
            btn = _norm_bairro(bt)
            if btn and btn != alvo and alvo not in btn and btn not in alvo:
                c["descarte_motivo"] = f"bairro do anúncio '{bt}' ≠ '{bairro}'"
                continue

        # (2) geocode real do anúncio (rua/bairro do título), checa suburb + raio
        consulta = c.get("endereco") or (
            f"{bt}, {cidade}, {uf}, Brasil" if bt else f"{bairro}, {cidade}, {uf}, Brasil")
        geo = nominatim_geocode(consulta)
        if geo:
            c["latitude"], c["longitude"] = geo["lat"], geo["lon"]
            c["endereco"] = c.get("endereco") or geo.get("display_name")
            c["geocode_fonte"] = "nominatim"
            addr = geo.get("address") or {}
            sub = _norm_bairro(addr.get("suburb") or addr.get("neighbourhood")
                               or addr.get("city_district") or "")
            if sub and sub != alvo and alvo not in sub and sub not in alvo:
                c["descarte_motivo"] = f"suburb geocode '{sub}' ≠ '{bairro}'"
                continue
            if clat is not None and clon is not None:
                dist = _haversine_km(geo["lat"], geo["lon"], clat, clon)
                if dist > raio:
                    c["descarte_motivo"] = f"{dist:.1f}km do centroide > {raio}km"
                    continue
        out.append(c)
    return out


def geocodar_candidatos(candidatos: list[dict], cidade: str, bairro: str, uf: str) -> list[dict]:
    """Filtra por bairro (descarta vazamento) E preenche lat/lon real do anúncio.
    Substitui o geocode-no-centroide ingênuo, que dava o mesmo ponto pra todo
    anúncio e deixava Meireles passar por Cocó."""
    return filtrar_por_bairro(candidatos, cidade, bairro, uf)


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
