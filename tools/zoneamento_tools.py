"""ZoneamentoChecker (VEC-378) — camada de viabilidade REGULATÓRIA do GymSite.

Cascata ZEUS (nacional): CKAN municipal (ex.: Fortaleza) → proxy OSM landuse →
indisponível (orientar prefeitura). Com fonte legal, classifica PERMISSIVO /
CONDICIONADO / RESTRITO. Sem fonte: NUNCA assume PERMISSIVO.

Determinístico (sem LLM). Dado de compat LUOS / params ZEDUS / config município vem de
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

_ALERTA_PREFEITURA = (
    "Zoneamento oficial indisponível para {cidade}/{uf}. "
    "Avaliar uso e ocupação do solo junto à prefeitura do município antes de fechar o ponto."
)


def _municipio_cfg(cidade: str) -> dict | None:
    """Config do município (CKAN base, dataset, cnae) do catálogo zoneamento_municipio."""
    from tools.catalogos import catalogo

    alvo = (cidade or "").strip().lower()
    alvo_compact = alvo.replace("-", " ")
    for c in catalogo("zoneamento_municipio"):
        chave = (c.get("chave") or "").strip().lower()
        nomes = {chave, chave.replace("-", " ")}
        for s in c.get("sinonimos") or []:
            nomes.add(str(s).strip().lower())
        if alvo in nomes or alvo_compact in nomes:
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


def _fetch_geojson_resource(cfg: dict, *, needle: str | None = None) -> dict | None:
    """Baixa FeatureCollection GeoJSON/JSON do CKAN."""
    base, dataset = cfg.get("ckan_base"), cfg.get("dataset_zonas")
    if not base or not dataset:
        return None
    needle_l = (needle if needle is not None else cfg.get("resource_name_contains") or "").lower()
    fmt_prefer = (cfg.get("resource_format") or "").upper()
    try:
        with httpx.Client(
            timeout=120,
            follow_redirects=True,
            headers={"User-Agent": "GymSite-ZEUS/1.0 (ckan-geojson)"},
        ) as c:
            meta = c.get(f"{base}/package_show", params={"id": dataset}).json()
            if not meta.get("success"):
                return None
            recs = meta["result"].get("resources", [])
            candidatos = []
            for r in recs:
                fmt = (r.get("format") or "").upper()
                name = (r.get("name") or "").lower()
                if fmt not in ("GEOJSON", "JSON"):
                    continue
                if fmt_prefer and fmt != fmt_prefer and fmt_prefer not in ("GEOJSON", "JSON"):
                    continue
                if needle_l and needle_l not in name:
                    continue
                candidatos.append(r)
            if not candidatos:
                return None
            # Preferir o recurso mais recente pelo nome (YYYYMMDD_...) quando houver vários.
            geo = sorted(candidatos, key=lambda r: (r.get("name") or ""), reverse=True)[0]
            resp = c.get(geo["url"])
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning("zoneamento GeoJSON CKAN falha: %s", e)
        return None


def _rings_from_geometry(geom: dict) -> list[list[tuple[float, float]]]:
    """Extrai anéis exteriores brutos (x,y) de Polygon/MultiPolygon."""
    if not isinstance(geom, dict):
        return []
    t = geom.get("type")
    coords = geom.get("coordinates") or []
    rings: list[list[tuple[float, float]]] = []

    def _ring(pts) -> list[tuple[float, float]]:
        out: list[tuple[float, float]] = []
        for p in pts or []:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                try:
                    out.append((float(p[0]), float(p[1])))
                except (TypeError, ValueError):
                    continue
        return out

    if t == "Polygon" and coords:
        r = _ring(coords[0])
        if len(r) >= 3:
            rings.append(r)
    elif t == "MultiPolygon":
        for poly in coords:
            if poly:
                r = _ring(poly[0])
                if len(r) >= 3:
                    rings.append(r)
    return rings


def _parse_geojson_to_polygons(
    fc: dict,
    *,
    layer_label: str = "ZEIS",
    crs: str | None = None,
    sigla_keys: list[str] | None = None,
    nome_keys: list[str] | None = None,
) -> list[dict]:
    """FeatureCollection → polígonos em WGS84 (lon,lat)."""
    from tools.zeus_crs import anel_para_wgs84, crs_de_feature_collection

    crs_eff = crs_de_feature_collection(fc, default=crs)
    sk = sigla_keys or [
        "sigla_zona", "SIGLA_TIPO_ZONEAMENTO", "CDTIPO", "ZONA", "ZONA2", "SIGLA",
    ]
    nk = nome_keys or [
        "nome_geo", "DESC_TIPO_ZONEAMENTO", "NMNOME", "MACROZONA", "name", "BAIRRO",
    ]
    polygons: list[dict] = []
    for feat in fc.get("features") or []:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        sigla = layer_label
        for k in sk:
            if props.get(k):
                sigla = props.get(k)
                break
        nome = ""
        for k in nk:
            if props.get(k):
                nome = props.get(k)
                break
        for ring in _rings_from_geometry(geom):
            ring_wgs = anel_para_wgs84(ring, crs_eff)
            if len(ring_wgs) < 3:
                continue
            polygons.append({
                "polygon": ring_wgs,
                "sigla_zona": str(sigla).strip(),
                "tipo_zona": layer_label,
                "nome_geo": str(nome).strip(),
                "nome_zona": str(nome or layer_label),
                "folder": layer_label,
                "crs_origem": crs_eff,
                "props": props,
            })
    return polygons


def _veredito_de_label(forced: str) -> dict:
    forced = (forced or "").upper().strip()
    raw = {"PERMISSIVO": "A", "CONDICIONADO": "P", "RESTRITO": "I"}.get(forced, "I")
    forced = forced if forced in ("PERMISSIVO", "CONDICIONADO", "RESTRITO") else "RESTRITO"
    desc = {
        "PERMISSIVO": "Atividade adequada à zona (malha oficial municipal).",
        "CONDICIONADO": "Permitida com restrições — validar parâmetros na prefeitura.",
        "RESTRITO": (
            "Zona especial / restrição urbanística. "
            "Academia exige análise na prefeitura — não tratar como uso livre."
        ),
    }[forced]
    return {"compatibilidade": forced, "compat_raw": raw, "descricao": desc}


def _classificar(zona_sigla: str) -> dict:
    """Compat LUOS Fortaleza (catálogo) → PERMISSIVO/CONDICIONADO/RESTRITO."""
    from tools.catalogos import catalogo_map

    compat = catalogo_map("zoneamento_compat_se_fortaleza")
    key = (zona_sigla or "").upper().strip()
    raw = compat.get(key)
    if raw is None:
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


def _classificar_municipio(zona_sigla: str, cfg: dict, *, layer_cfg: dict | None = None) -> dict:
    """Override por camada / prefixos (BH, Recife) ou LUOS Fortaleza."""
    lc = layer_cfg or {}
    forced = (lc.get("compat_na_malha") or cfg.get("compat_na_malha") or "").upper().strip()
    if forced in ("PERMISSIVO", "CONDICIONADO", "RESTRITO"):
        return _veredito_de_label(forced)

    key = (zona_sigla or "").upper().strip()
    prefixos = lc.get("compat_prefixos") or cfg.get("compat_prefixos") or {}
    for pref, lab in sorted(prefixos.items(), key=lambda kv: -len(str(kv[0]))):
        if key.startswith(str(pref).upper()):
            return _veredito_de_label(str(lab))

    default = (lc.get("compat_default_na_malha") or cfg.get("compat_default_na_malha") or "").upper()
    if default in ("PERMISSIVO", "CONDICIONADO", "RESTRITO"):
        return _veredito_de_label(default)

    return _classificar(zona_sigla)


_COR_ZONA = {
    "ZEDUS": "#16A34A", "ZOC": "#16A34A", "ZEU": "#16A34A",
    "ZEIS": "#DC2626", "ZEA": "#DC2626",
    "ZEPH": "#D97706", "ZEPO": "#D97706", "ZEI": "#D97706", "AEA": "#D97706",
}


def _cor_de_sigla(s: str) -> str:
    s = (s or "").upper()
    for k, v in _COR_ZONA.items():
        if s.startswith(k):
            return v
    return "#64748B"


def _svg_mapa_zonas(lat: float, lon: float, polygons: list, *, raio: float = 0.025) -> str | None:
    """SVG self-contained dos POLÍGONOS de zona perto do candidato."""
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
        return (pad + (lo - minx) * sc, pad + (maxy - la) * sc)

    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
              f'style="width:100%;border:1px solid #E2E8F0;border-radius:4px;background:#F8FAFC;">']
    for p in prox[:40]:
        poly = p["polygon"]
        step = max(1, len(poly) // 50)
        poly = poly[::step]
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_px(lo, la) for lo, la in poly))
        cor = _cor_de_sigla(p.get("sigla_zona") or p.get("tipo_zona") or p.get("folder") or "")
        partes.append(f'<polygon points="{pts}" fill="{cor}" fill-opacity="0.22" stroke="{cor}" stroke-width="1"/>')
    cx, cy = _px(lon, lat)
    partes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#0F172A" stroke="#fff" stroke-width="2"/>')
    partes.append('</svg>')
    return "".join(partes)


def _png_mapa_zonas(lat: float, lon: float, polygons: list) -> str | None:
    """PNG OSM data URI — mesma geometria do SVG; fail-soft."""
    try:
        from tools.mapa_osm_real import try_mapa_zonas_data_uri

        return try_mapa_zonas_data_uri(list(polygons or []), float(lat), float(lon))
    except Exception:
        logger.warning("mapa_osm zonas PNG falhou", exc_info=True)
        return None


def _mapas_zonas(lat: float, lon: float, polygons: list) -> dict[str, str | None]:
    return {
        "mapa_svg": _svg_mapa_zonas(lat, lon, polygons),
        "mapa_png": _png_mapa_zonas(lat, lon, polygons),
    }


def _mapa_estatico_url(lat: float, lon: float, polygon: list | None, compat: str) -> str | None:
    """URL do mapa estático (Google Maps Static API). None se sem key."""
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
        step = max(1, len(polygon) // 40)
        pts = polygon[::step]
        path = "%7C".join(f"{la},{lo}" for lo, la in pts)
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


def _alerta_prefeitura(cidade: str, uf: str, *, extra: str | None = None) -> str:
    base = _ALERTA_PREFEITURA.format(cidade=cidade or "—", uf=uf or "—")
    return f"{base} {extra}".strip() if extra else base


def _bloco_indisponivel(
    cidade: str, bairro: str, uf: str,
    latitude: float, longitude: float, cnae: str,
    *, extra_alerta: str | None = None,
) -> dict[str, Any]:
    return {
        "status": "indisponivel",
        "cidade": cidade,
        "bairro": bairro,
        "uf": uf,
        "latitude": latitude,
        "longitude": longitude,
        "cnae": cnae,
        "compatibilidade": None,
        "compat_raw": None,
        "zona_sigla": None,
        "zona_nome": None,
        "nome_geo": bairro,
        "descricao": (
            "Sem plano diretor/LUOS digital para este município na cascata ZEUS. "
            "Não se assume permissividade."
        ),
        "restricoes": ["Validar zoneamento legal na prefeitura"],
        "alerta": _alerta_prefeitura(cidade, uf, extra=extra_alerta),
        "mapa_svg": None,
        "mapa_png": None,
        "fonte_dados": None,
        "camada": "fallback_honesto",
    }


def _buscar_osm_landuse(latitude: float, longitude: float, *, raio_m: int = 150) -> str | None:
    """Compat: retorna só a tag OSM predominante. Preferir consultar_osm_proxy."""
    from tools.zeus_osm_proxy import consultar_osm_proxy

    perfil = consultar_osm_proxy(latitude, longitude, raio_m=raio_m)
    return (perfil or {}).get("tag_osm")


def _bloco_proxy_osm(
    cidade: str, bairro: str, uf: str,
    latitude: float, longitude: float, cnae: str,
    uso_osm: str,
    *,
    perfil: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Camada 2 ZEUS: uso OBSERVADO no OSM — nunca veredito legal (PERMISSIVO etc.)."""
    from tools.zeus_osm_proxy import avaliar_completude, rotular_uso_observado

    p = dict(perfil or {})
    tag = (p.get("tag_osm") or uso_osm or "").strip().lower()
    uso_obs = p.get("uso_observado") or rotular_uso_observado(tag)
    if "completude" not in p:
        p.update(avaliar_completude(int(p.get("n_features") or 1)))
    baixa = (p.get("completude") or "") == "baixa"
    nota_c = p.get("nota_completude")
    desc = (
        f"Sem plano diretor digital para {cidade}/{uf}. "
        f"Uso do solo OBSERVADO no OpenStreetMap: {uso_obs} (tag {tag}). "
        "Isso descreve a realidade no terreno — NÃO significa permissão legal para academia."
    )
    alerta = (
        f"Sem plano diretor digital para {cidade}/{uf}. "
        f"Atividade/uso observado no OSM: {uso_obs}. "
        "Avaliar uso e ocupação do solo junto à prefeitura do município antes de fechar o ponto."
    )
    if nota_c:
        alerta = f"{alerta} {nota_c}"
    return {
        "status": "proxy_osm",
        "cidade": cidade,
        "bairro": bairro,
        "uf": uf,
        "latitude": latitude,
        "longitude": longitude,
        "cnae": cnae,
        "compatibilidade": "INDIVIDUALIZAR",
        "compat_raw": None,
        "zona_sigla": f"OSM:{tag}",
        "zona_nome": f"Uso observado OSM ({uso_obs})",
        "nome_geo": bairro,
        "uso_predominante_osm": tag,
        "uso_observado": uso_obs,
        "origem_tag": p.get("origem_tag") or "landuse",
        "descricao": desc,
        "restricoes": ["Validar zoneamento legal na prefeitura"],
        "alerta": alerta,
        "mapa_svg": None,
        "mapa_png": None,
        "fonte_dados": "OSM_landuse_proxy",
        "camada": "osm_proxy",
        "completude": p.get("completude") or "alta",
        "confianca": p.get("confianca") if p.get("confianca") is not None else 85,
        "n_features_osm": p.get("n_features"),
        "baixa_completude": baixa,
    }


def _carregar_poligonos_municipio(cidade: str, cfg: dict) -> list[dict] | None:
    """Cache por município: KMZ ou uma/várias camadas GeoJSON (c/ CRS)."""
    ckey = f"{cidade.strip().lower()}_zonas"
    if ckey in _polygons_cache:
        return _polygons_cache[ckey]
    formato = (cfg.get("formato") or "kmz").lower()
    if formato == "geojson":
        camadas = cfg.get("camadas")
        if isinstance(camadas, list) and camadas:
            polys: list[dict] = []
            for camada in camadas:
                if not isinstance(camada, dict):
                    continue
                needle = camada.get("resource_name_contains") or cfg.get("resource_name_contains")
                fc = _fetch_geojson_resource(cfg, needle=needle)
                if not fc:
                    logger.warning("camada GeoJSON vazia: %s/%s", cidade, needle)
                    continue
                layer = camada.get("layer_label") or needle or "ZONA"
                layer_polys = _parse_geojson_to_polygons(
                    fc,
                    layer_label=str(layer),
                    crs=camada.get("crs") or cfg.get("crs"),
                )
                for p in layer_polys:
                    p["_layer_cfg"] = camada
                polys.extend(layer_polys)
            if not polys:
                return None
        else:
            fc = _fetch_geojson_resource(cfg)
            if not fc:
                return None
            layer = cfg.get("layer_label") or cfg.get("resource_name_contains") or "ZONA"
            polys = _parse_geojson_to_polygons(
                fc, layer_label=str(layer), crs=cfg.get("crs"),
            )
            for p in polys:
                p["_layer_cfg"] = {}
    else:
        kmz = _fetch_kmz(cfg)
        if not kmz:
            return None
        polys = _parse_kmz_to_polygons(kmz)
    _polygons_cache[ckey] = polys
    logger.info("zoneamento: %d polígonos p/ %s (%s)", len(polys), cidade, formato)
    return polys


def _zoneamento_por_ckan(
    cidade: str, bairro: str, uf: str,
    latitude: float, longitude: float,
    endereco: str | None, cnae: str, cfg: dict,
) -> dict[str, Any]:
    """Camada 1: malha oficial municipal (KMZ ou GeoJSON CKAN)."""
    polys = _carregar_poligonos_municipio(cidade, cfg)
    if polys is None:
        return {"status": "ckan_indisponivel", "mensagem": "Malha de zoneamento indisponível (CKAN)."}

    zona = next(
        (p for p in polys if p.get("polygon")
         and _point_in_polygon(longitude, latitude, p["polygon"])),
        None,
    )
    fonte = f"CKAN_{(cidade or '').upper()}"
    base_url = (cfg.get("ckan_base") or "").replace("/api/3/action", "")
    dataset = cfg.get("dataset_zonas") or ""
    fonte_url = f"{base_url}/dataset/{dataset}" if base_url and dataset else None
    fora_mode = (cfg.get("fora_malha") or "permissivo").lower()

    if zona is None:
        if fora_mode == "cascade":
            # Malha parcial (ex.: só ZEIS) — fora NÃO é PERMISSIVO; segue OSM.
            return {
                "status": "fora_malha_cascade",
                "cidade": cidade,
                "bairro": bairro,
                "uf": uf,
                "latitude": latitude,
                "longitude": longitude,
                "cnae": cnae,
                "mensagem": (
                    f"Ponto fora da malha oficial parcial ({cfg.get('layer_label') or 'zonas'}). "
                    "Não se assume permissividade — cascata OSM."
                ),
                "fonte_dados": fonte,
                "camada": "ckan_municipal",
            }
        return {
            "status": "fora_de_zona",
            "cidade": cidade,
            "bairro": bairro,
            "uf": uf,
            "endereco": endereco,
            "latitude": latitude,
            "longitude": longitude,
            "cnae": cnae,
            "compatibilidade": "PERMISSIVO",
            "compat_raw": "A",
            "zona_sigla": "USO GERAL",
            "nome_geo": bairro,
            "descricao": "Fora de zona especial — uso geral (ZOC/ZEU), academia permitida.",
            "restricoes": [],
            "alerta": None,
            **_mapas_zonas(latitude, longitude, polys),
            "fonte_dados": fonte,
            "fonte_url": fonte_url,
            "camada": "ckan_municipal",
            "confianca": 100,
        }

    sigla = (zona.get("sigla_zona") or zona.get("tipo_zona") or "").strip()
    nome_geo = zona.get("nome_geo") or zona.get("name") or ""
    cls = _classificar_municipio(sigla, cfg, layer_cfg=zona.get("_layer_cfg") or {})
    params = _zedus_params(nome_geo) if sigla.upper().startswith("ZEDUS") else {}
    out = {
        "status": "ok",
        "cidade": cidade,
        "bairro": bairro,
        "uf": uf,
        "endereco": endereco,
        "latitude": latitude,
        "longitude": longitude,
        "cnae": cnae,
        "zona_sigla": sigla,
        "zona_nome": zona.get("nome_zona") or "",
        "nome_geo": nome_geo,
        "area_m2": zona.get("area_m2"),
        "subgrupo": (cfg.get("subgrupos") or ["SE"])[0],
        "classe": 1,
        **cls,
        "ia_maximo": params.get("ia_max"),
        "taxa_ocupacao": params.get("tx_ocup"),
        "altura_max": params.get("altura_max"),
        "restricoes": [],
        "alerta": None,
        **_mapas_zonas(latitude, longitude, polys),
        "fonte_dados": fonte,
        "fonte_url": fonte_url,
        "camada": "ckan_municipal",
        "confianca": 100,
    }
    if cls["compatibilidade"] == "RESTRITO":
        out["alerta"] = (
            f"Imóvel em {sigla} ({nome_geo}). Academia (CNAE {cnae}) é INADEQUADA "
            "nesta zona especial — validar na prefeitura / buscar outra localização."
        )
        out["restricoes"].append("Atividade vedada ou fortemente condicionada na zona especial")
    elif cls["compatibilidade"] == "CONDICIONADO":
        out["alerta"] = (
            f"Imóvel em {sigla} ({nome_geo}). Permitida com restrições — "
            "verificar parâmetros urbanísticos na prefeitura."
        )
        out["restricoes"].append("Necessita atender parâmetros urbanísticos locais")
    return out


def analisar_zoneamento_candidato(
    cidade: str, bairro: str, uf: str,
    latitude: float, longitude: float,
    endereco: str | None = None,
    cnae: str = "9313-1/00",
) -> dict[str, Any]:
    """Cascata ZEUS: CKAN municipal → proxy OSM landuse → indisponível (prefeitura).

    status: ok | fora_de_zona | proxy_osm | indisponivel | erro.
    NUNCA assume PERMISSIVO sem malha oficial completa do município.
    """
    if latitude is None or longitude is None:
        return {"status": "erro", "mensagem": "Candidato sem lat/lon (rodar geocoding antes)."}

    cfg = _municipio_cfg(cidade)
    if cfg:
        out = _zoneamento_por_ckan(
            cidade, bairro, uf, latitude, longitude, endereco, cnae, cfg)
        if out.get("status") not in ("ckan_indisponivel", "fora_malha_cascade"):
            return out
        logger.info(
            "zoneamento %s → cascata OSM (%s)",
            cidade, out.get("status"),
        )

    from tools.zeus_osm_proxy import consultar_osm_proxy

    perfil = consultar_osm_proxy(latitude, longitude)
    if perfil and perfil.get("tag_osm"):
        return _bloco_proxy_osm(
            cidade, bairro, uf, latitude, longitude, cnae,
            perfil["tag_osm"], perfil=perfil,
        )

    return _bloco_indisponivel(cidade, bairro, uf, latitude, longitude, cnae)
