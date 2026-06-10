"""
Extrai identificadores de fichas Google Maps a partir de URLs.

Suporta:
- place_id canônico (ChIJ...) via query `place_id:` ou parâmetro `1s...:0x...`
- Knowledge Graph ID (`/g/11c6ddhr68`) — retornado como `kgmid` (não é ChIJ)
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse


_RE_PLACE_ID_QUERY = re.compile(r"place_id:([A-Za-z0-9_-]+)", re.I)
_RE_CHIJ_IN_PATH = re.compile(r"(ChIJ[A-Za-z0-9_-]{20,})")
_RE_HEX_PLACE = re.compile(r"1s(0x[0-9a-f]+:0x[0-9a-f]+)", re.I)
_RE_KGMID = re.compile(r"(?:/|%2F)g/([A-Za-z0-9_-]+)", re.I)


def extrair_place_id_de_url(url: str) -> str | None:
    """
    Retorna place_id ChIJ quando detectável na URL do Maps.

    URLs só com `/g/11...` não viram ChIJ automaticamente — use
    `resolver_place_id` (Places API) com nome+coordenadas.
    """
    if not url or not isinstance(url, str):
        return None
    raw = url.strip()
    if not raw:
        return None

    m = _RE_PLACE_ID_QUERY.search(raw)
    if m:
        return m.group(1)

    m = _RE_CHIJ_IN_PATH.search(unquote(raw))
    if m:
        return m.group(1)

    m = _RE_HEX_PLACE.search(raw)
    if m:
        # Hex pair não é ChIJ — Places Nearby já devolve ChIJ; mantemos None.
        return None

    try:
        parsed = urlparse(raw)
        qs = parse_qs(parsed.query)
        for key in ("place_id", "q"):
            for val in qs.get(key, []):
                if val.startswith("ChIJ"):
                    return val
    except Exception:
        pass

    return None


def extrair_kgmid_de_url(url: str) -> str | None:
    """Retorna ID `/g/11c6ddhr68` quando presente (formato Knowledge Graph)."""
    if not url:
        return None
    m = _RE_KGMID.search(unquote(url))
    return f"g/{m.group(1)}" if m else None


def extrair_hex_ftid_de_url(url: str) -> str | None:
    """Retorna par `0x...:0x...` do bloco `1s` em URLs Google Maps."""
    if not url:
        return None
    m = _RE_HEX_PLACE.search(unquote(url))
    return m.group(1) if m else None


def montar_maps_url_place(
    nome: str,
    place_id: str,
    lat: float | None = None,
    lng: float | None = None,
    *,
    cidade: str = "",
    hex_ftid: str = "",
) -> str:
    """
    URL estável para Playwright abrir a ficha no Maps.

    `place/{nome}/@.../data=!...1sChIJ` redireciona para `place//` (painel
    vazio + login) em headless — evitado. Preferimos:
    1) busca georreferenciada (nome + coords) — scraper clica no 1º resultado;
    2) ficha com ftid hex (`0x:0x`) quando disponível em googleMapsUri;
    3) fallback `?q=place_id:ChIJ`.
    """
    from urllib.parse import quote_plus

    pid = (place_id or "").strip()
    if not pid and not (nome and lat is not None and lng is not None):
        return ""

    ftid = (hex_ftid or "").strip()
    if ftid and lat is not None and lng is not None and (lat or lng):
        return (
            f"https://www.google.com/maps/place//@{lat},{lng},17z/"
            f"data=!4m6!3m5!1s{ftid}!8m2!3d{lat}!4d{lng}"
        )

    if pid:
        # Validado Playwright 2026-06-03: abre ficha + aria-labels de pico.
        return f"https://www.google.com/maps/place/?q=place_id:{pid}&hl=pt-BR"

    query = " ".join(
        p for p in ((nome or "").strip(), (cidade or "").strip()) if p
    ) or "local"
    q = quote_plus(query[:140])
    return f"https://www.google.com/maps/search/{q}/@{lat},{lng},17z"
