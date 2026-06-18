"""ZoneamentoChecker (VEC-378) — camada de viabilidade REGULATÓRIA do GymSite.

Valida se o endereço do candidato permite academia (CNAE 9313-1/00) pela LUOS de
Fortaleza: baixa o KMZ das Zonas Especiais (CKAN), faz point-in-polygon com o lat/lon
do candidato (que a cascata P1 / Nominatim fornece), e classifica PERMISSIVO /
CONDICIONADO / RESTRITO. Pega o furo: candidato score 9.0 num ZEIS é inviável legal.

Determinístico (sem LLM). TODO dado (compat LUOS, params ZEDUS, config município) vem de
catalogos_metodologia via import — nada inline (regra: dado que gera insight = tabela).
Cache de polígonos por processo; KMZ ~450 KB, parse local, custo zero (CKAN sem key).
"""
from __future__ import annotations

import io
import logging
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger("gymsite.zoneamento")

_polygons_cache: dict[str, list[dict]] = {}


def _municipio_cfg(cidade: str) -> dict | None:
    """Config do município (CKAN base, dataset, cnae) do catálogo zoneamento_municipio."""
    from tools.catalogos import catalogo

    alvo = (cidade or "").strip().lower()
    for c in catalogo("zoneamento_municipio"):
        if (c.get("chave") or "").lower() == alvo:
            return c.get("metadata") or {}
    return None


def _parse_kmz_to_polygons(kmz_bytes: bytes) -> list[dict]:
    """Extrai polígonos + atributos (sigla_zona, nome_geo, area_m2) do KMZ."""
    polygons: list[dict] = []
    kmz = zipfile.ZipFile(io.BytesIO(kmz_bytes))
    kml_name = next((n for n in kmz.namelist() if n.endswith(".kml")), None)
    if not kml_name:
        return polygons
    root = ET.fromstring(kmz.read(kml_name).decode("utf-8", "ignore"))
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    for folder in root.findall(".//kml:Folder", ns):
        fn = folder.find("kml:name", ns)
        folder_name = fn.text if fn is not None else ""
        for pm in folder.findall(".//kml:Placemark", ns):
            attrs: dict[str, Any] = {"folder": folder_name}
            nm = pm.find("kml:name", ns)
            if nm is not None:
                attrs["name"] = nm.text
            ext = pm.find("kml:ExtendedData", ns)
            if ext is not None:
                for sd in ext.findall(".//kml:SimpleData", ns):
                    attrs[sd.get("name")] = sd.text
            coords_elem = pm.find(".//kml:coordinates", ns)
            if coords_elem is not None and coords_elem.text:
                coords = []
                for pt in coords_elem.text.strip().split():
                    p = pt.split(",")
                    if len(p) >= 2:
                        try:
                            coords.append((float(p[0]), float(p[1])))
                        except ValueError:
                            continue
                if coords:
                    attrs["polygon"] = coords
                    polygons.append(attrs)
    return polygons


def _point_in_polygon(lon: float, lat: float, polygon: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _fetch_kmz(cfg: dict) -> bytes | None:
    base, dataset = cfg.get("ckan_base"), cfg.get("dataset_zonas")
    if not base or not dataset:
        return None
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as c:
            meta = c.get(f"{base}/package_show", params={"id": dataset}).json()
            if not meta.get("success"):
                return None
            recs = meta["result"].get("resources", [])
            kmz = next((r for r in recs if (r.get("format") or "").upper() == "KMZ"), None)
            if not kmz:
                return None
            r = c.get(kmz["url"])
            return r.content if r.status_code == 200 else None
    except Exception as e:
        logger.warning("zoneamento CKAN falha: %s", e)
        return None


def _classificar(zona_sigla: str) -> dict:
    """Compat LUOS (catálogo) → PERMISSIVO/CONDICIONADO/RESTRITO. A/P/I por zona."""
    from tools.catalogos import catalogo_map

    compat = catalogo_map("zoneamento_compat_se_fortaleza")
    key = (zona_sigla or "").upper().strip()
    raw = compat.get(key)
    if raw is None:  # ZEIS 1/2/3 — match por prefixo
        for k, v in compat.items():
            if key.startswith(k.upper()):
                raw = v
                break
    raw = raw or "I"
    if raw == "A":
        return {"compatibilidade": "PERMISSIVO", "compat_raw": "A",
                "descricao": "Atividade adequada à zona. Sem restrição adicional."}
    if raw == "P":
        return {"compatibilidade": "CONDICIONADO", "compat_raw": "P",
                "descricao": "Permitida com restrições de recuo, área ou porte."}
    return {"compatibilidade": "RESTRITO", "compat_raw": "I",
            "descricao": "Atividade inadequada/vedada na zona. Necessita análise técnica."}


_COR_ZONA = {
    "ZEDUS": "#16A34A", "ZOC": "#16A34A", "ZEU": "#16A34A",  # comerciais → permissivo
    "ZEIS": "#DC2626", "ZEA": "#DC2626",                      # restritivos
    "ZEPH": "#D97706", "ZEPO": "#D97706", "ZEI": "#D97706", "AEA": "#D97706",
}


def _cor_de_sigla(s: str) -> str:
    s = (s or "").upper()
    for k, v in _COR_ZONA.items():
        if s.startswith(k):
            return v
    return "#64748B"


def _svg_mapa_zonas(lat: float, lon: float, polygons: list, *, raio: float = 0.025) -> str | None:
    """SVG self-contained dos POLÍGONOS de zona perto do candidato (não marcador de
    imóvel): cada zona colorida por tipo + ponto do candidato. Sem Google/key. Embutível
    inline no PDF (WeasyPrint) e na UI. raio em graus (~2,5 km)."""
    prox = []
    for p in (polygons or []):
        poly = p.get("polygon")
        if not poly:
            continue
        if any(abs(lo - lon) <= raio and abs(la - lat) <= raio for lo, la in poly):
            prox.append(p)
    if not prox:
        return None
    xs = [lo for p in prox for lo, _ in p["polygon"]] + [lon]
    ys = [la for p in prox for _, la in p["polygon"]] + [lat]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W, H, pad = 560.0, 300.0, 8.0
    dx, dy = (maxx - minx) or 1e-6, (maxy - miny) or 1e-6
    sc = min((W - 2 * pad) / dx, (H - 2 * pad) / dy)

    def _px(lo, la):
        return (pad + (lo - minx) * sc, pad + (maxy - la) * sc)  # flip y (lat sobe)

    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
              f'style="width:100%;border:1px solid #E2E8F0;border-radius:4px;background:#F8FAFC;">']
    for p in prox[:40]:
        poly = p["polygon"]
        step = max(1, len(poly) // 50)  # amostra ~50 vértices/polígono (tamanho do SVG)
        poly = poly[::step]
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_px(lo, la) for lo, la in poly))
        cor = _cor_de_sigla(p.get("sigla_zona") or p.get("tipo_zona") or p.get("folder") or "")
        partes.append(f'<polygon points="{pts}" fill="{cor}" fill-opacity="0.22" stroke="{cor}" stroke-width="1"/>')
    cx, cy = _px(lon, lat)
    partes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#0F172A" stroke="#fff" stroke-width="2"/>')
    partes.append('</svg>')
    return "".join(partes)


def _mapa_estatico_url(lat: float, lon: float, polygon: list | None, compat: str) -> str | None:
    """URL do mapa estático (Google Maps Static API): candidato (marcador) + polígono da
    zona (quando há), colorido pela compatibilidade. None se sem key. Embutível no PDF/UI.
    (Maps Static API habilitada no projeto; a key serve server-side como o Street View.)"""
    try:
        from tools.google_maps_key import get_google_maps_api_key

        key = get_google_maps_api_key()
    except Exception:
        key = ""
    if not key:
        return None
    cor = {"PERMISSIVO": "0x16A34A", "CONDICIONADO": "0xD97706", "RESTRITO": "0xDC2626"}.get(compat, "0x0E5C66")
    parts = [f"center={lat},{lon}", "zoom=15", "size=560x230", "scale=2", "language=pt-BR",
             f"markers=color:red%7C{lat},{lon}"]
    if polygon and len(polygon) >= 3:
        step = max(1, len(polygon) // 40)  # Static Maps limita o tamanho da URL
        pts = polygon[::step]
        path = "%7C".join(f"{la},{lo}" for lo, la in pts)  # polygon = (lon,lat)
        parts.append(f"path=color:{cor}A0%7Cfillcolor:{cor}30%7Cweight:2%7C{path}")
    return f"https://maps.googleapis.com/maps/api/staticmap?{'&'.join(parts)}&key={key}"


def _zedus_params(nome_geo: str) -> dict:
    from tools.catalogos import catalogo

    alvo = (nome_geo or "").upper()
    for c in catalogo("zoneamento_zedus_param"):
        k = (c.get("chave") or "").upper()
        if k and (k in alvo or alvo in k):
            return c.get("metadata") or {}
    return {}


def analisar_zoneamento_candidato(cidade: str, bairro: str, uf: str,
                                  latitude: float, longitude: float,
                                  endereco: str | None = None,
                                  cnae: str = "9313-1/00") -> dict[str, Any]:
    """Macro-tool: lat/lon → zona (point-in-polygon no KMZ) → compatibilidade LUOS.
    status: ok | fora_de_zona | nao_suportado | erro. Best-effort."""
    cfg = _municipio_cfg(cidade)
    if not cfg:
        return {"status": "nao_suportado", "cidade": cidade,
                "mensagem": f"Município '{cidade}' sem adapter de zoneamento."}
    if latitude is None or longitude is None:
        return {"status": "erro", "mensagem": "Candidato sem lat/lon (rodar geocoding antes)."}

    ckey = f"{cidade.strip().lower()}_zonas"
    polys = _polygons_cache.get(ckey)
    if polys is None:
        kmz = _fetch_kmz(cfg)
        if not kmz:
            return {"status": "erro", "mensagem": "KMZ de zoneamento indisponível (CKAN)."}
        polys = _parse_kmz_to_polygons(kmz)
        _polygons_cache[ckey] = polys
        logger.info("zoneamento: %d polígonos p/ %s", len(polys), cidade)

    zona = next((p for p in polys if p.get("polygon")
                 and _point_in_polygon(longitude, latitude, p["polygon"])), None)
    if zona is None:
        # Fora das zonas especiais = zona de uso geral (ZOC/ZEU) → permissivo.
        return {"status": "fora_de_zona", "cidade": cidade, "bairro": bairro,
                "latitude": latitude, "longitude": longitude, "cnae": cnae,
                "compatibilidade": "PERMISSIVO", "compat_raw": "A",
                "zona_sigla": "USO GERAL", "nome_geo": bairro,
                "descricao": "Fora de zona especial — uso geral (ZOC/ZEU), academia permitida.",
                "restricoes": [], "alerta": None,
                "mapa_svg": _svg_mapa_zonas(latitude, longitude, polys),
                "fonte_dados": f"CKAN_{cidade.upper()}"}

    sigla = (zona.get("sigla_zona") or zona.get("tipo_zona") or "").strip()
    nome_geo = zona.get("nome_geo") or zona.get("name") or ""
    cls = _classificar(sigla)
    params = _zedus_params(nome_geo) if sigla.upper().startswith("ZEDUS") else {}
    out = {
        "status": "ok", "cidade": cidade, "bairro": bairro, "uf": uf, "endereco": endereco,
        "latitude": latitude, "longitude": longitude, "cnae": cnae,
        "zona_sigla": sigla, "zona_nome": zona.get("nome_zona") or "", "nome_geo": nome_geo,
        "area_m2": zona.get("area_m2"), "subgrupo": (cfg.get("subgrupos") or ["SE"])[0], "classe": 1,
        **cls,
        "ia_maximo": params.get("ia_max"), "taxa_ocupacao": params.get("tx_ocup"),
        "altura_max": params.get("altura_max"), "restricoes": [], "alerta": None,
        "mapa_svg": _svg_mapa_zonas(latitude, longitude, polys),
        "fonte_dados": f"CKAN_{cidade.upper()}",
        "fonte_url": f"https://dados.fortaleza.ce.gov.br/dataset/{cfg.get('dataset_zonas')}",
    }
    if cls["compatibilidade"] == "RESTRITO":
        out["alerta"] = (f"Imóvel em {sigla} ({nome_geo}). Academia (CNAE {cnae}) é INADEQUADA "
                         "nesta zona — buscar candidato em ZEDUS, ZOC ou ZEU.")
        out["restricoes"].append("Atividade vedada na zona especial identificada")
    elif cls["compatibilidade"] == "CONDICIONADO":
        out["alerta"] = (f"Imóvel em {sigla} ({nome_geo}). Permitida com restrições — "
                         "verificar recuos e parâmetros urbanísticos (Anexo 8 LUOS).")
        out["restricoes"].append("Necessita atender recuos do Anexo 8 da LUOS")
    return out
