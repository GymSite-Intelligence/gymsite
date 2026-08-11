"""Catálogos/taxonomias recalibráveis — DADO em tabela (catalogos_metodologia), não
dict inline no código (regra: todo dado que gera insight é tabelizado e importado).

Espelha tools/parametros_metodologia: tabela Supabase é a fonte viva; _fallback() é o
seed rotulado usado se a tabela não responder. Accessor `catalogo(nome)` + utilitário
`normalizar_servicos()` (texto bruto/marketing → categorias de serviço limpas).
"""
from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

_CACHE: dict[str, list[dict[str, Any]]] = {}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip()


def _fallback(nome: str) -> list[dict[str, Any]]:
    """Seed rotulado (fallback se a tabela falhar). Reaproveita os dicts existentes —
    enquanto migram, são a fonte do seed; a tabela é a fonte viva."""
    if nome == "servicos":
        try:
            from agents.a9_positioning_strategist import _SERVICOS_CATALOGO
            from tools.competitor_offer_mapper import MODALIDADES_KEYWORDS

            return [
                {"chave": k, "valor": v, "sinonimos": MODALIDADES_KEYWORDS.get(k, [])}
                for k, v in _SERVICOS_CATALOGO.items()
            ]
        except Exception:
            return []
    # MRLR (IBAPE-GO, R²=0,8633) — seed espelhando a tabela (lida em 2026-07-06; conta
    # reproduzida na mão: Cocó 900m²/padrão 3/local 2/porte 4/PIB Fortaleza →
    # VU 26,37/m² × 900 = R$ 23.733, EXATO o run de 05/07). Antes os coeficientes
    # viviam SÓ no banco: a pausa do Supabase deixou o motor sem aluguel determinístico
    # e sem reprodutibilidade (auditoria 06/07). Calibração original em Goiás —
    # aplicação fora é extrapolação geográfica rotulada na metodologia.
    if nome == "mrlr_coef":
        return [{"chave": k, "valor": str(v), "sinonimos": [], "metadata": {"valor": v}}
                for k, v in {
                    "intercepto": 4.313769885, "ln_area": -0.8626002338,
                    "ln_padrao": 1.864588423, "local": 0.9845380613,
                    "ln_porte": 0.6497837846, "inv_pib": -74535651.84,
                    "fator_economico": 1.7713348,
                }.items()]
    if nome == "mrlr_escala":
        return [{"chave": k, "valor": str(v), "sinonimos": [], "metadata": {"valor": v}}
                for k, v in {
                    "local_zedus_zoc": 2, "local_zeis_zea": 1,
                    "porte_ate30k": 1, "porte_30a50k": 2, "porte_50a100k": 3,
                    "porte_acima100k": 4, "padrao_baixo": 1, "padrao_normal": 2,
                    "padrao_alto": 3, "fator_pibpc_corte": 50000,
                }.items()]
    if nome == "zoneamento_municipio":
        return [
            {
                "chave": "fortaleza",
                "valor": "CKAN",
                "sinonimos": [],
                "metadata": {
                    "cnae": "9313-1/00",
                    "ckan_base": "https://dados.fortaleza.ce.gov.br/api/3/action",
                    "subgrupos": ["SE", "SP", "PS"],
                    "dataset_zonas": "zonas-especiais",
                    "formato": "kmz",
                    "fora_malha": "permissivo",
                },
            },
            {
                "chave": "recife",
                "valor": "CKAN",
                "sinonimos": [],
                "metadata": {
                    "cnae": "9313-1/00",
                    "ckan_base": "https://dados.recife.pe.gov.br/api/3/action",
                    "dataset_zonas": "zoneamento",
                    "formato": "geojson",
                    "fora_malha": "cascade",
                    "subgrupos": ["SE"],
                    "camadas": [
                        {
                            "resource_name_contains": "Zeis",
                            "layer_label": "ZEIS",
                            "crs": "EPSG:4326",
                            "compat_na_malha": "RESTRITO",
                        },
                        {
                            "resource_name_contains": "Micro",
                            "layer_label": "MICRO",
                            "crs": "EPSG:31985",
                            "compat_default_na_malha": "CONDICIONADO",
                            "compat_prefixos": {
                                "ZEIS": "RESTRITO",
                                "ZDS": "CONDICIONADO",
                            },
                        },
                    ],
                },
            },
            {
                "chave": "belo horizonte",
                "valor": "CKAN",
                "sinonimos": ["bh", "belo-horizonte"],
                "metadata": {
                    "cnae": "9313-1/00",
                    "ckan_base": "https://ckan.pbh.gov.br/api/3/action",
                    "dataset_zonas": "zoneamento-lei-11181",
                    "formato": "geojson",
                    "resource_format": "JSON",
                    "resource_name_contains": "zoneamento_11181",
                    "layer_label": "ZONEAMENTO_11181",
                    "crs": "EPSG:31983",
                    "fora_malha": "cascade",
                    "compat_default_na_malha": "CONDICIONADO",
                    "compat_prefixos": {
                        "ZEIS": "RESTRITO",
                        "AEIS": "RESTRITO",
                        "PA-": "RESTRITO",
                        "PA_": "RESTRITO",
                        "OM-": "CONDICIONADO",
                        "OP-": "CONDICIONADO",
                        "AGEE": "CONDICIONADO",
                        "AGEUC": "CONDICIONADO",
                    },
                    "subgrupos": ["SE"],
                },
            },
        ]
    if nome == "zoneamento_osm_uso_obs":
        # Tag OSM → rótulo empírico (nunca PERMISSIVO/CONDICIONADO/RESTRITO).
        return [
            {"chave": k, "valor": v, "sinonimos": [], "metadata": {}}
            for k, v in {
                "commercial": "comercial_observado",
                "retail": "comercial_observado",
                "industrial": "industrial_observado",
                "residential": "residencial_observado",
                "grass": "area_verde_observada",
                "forest": "area_verde_observada",
                "farmland": "rural_observado",
                "construction": "em_transformacao_observado",
                "recreation_ground": "lazer_observado",
            }.items()
        ]
    return []


def catalogo(nome: str) -> list[dict[str, Any]]:
    """[{chave, valor, sinonimos}] do catálogo. Supabase (catalogos_metodologia) primeiro,
    _fallback() rotulado se indisponível. Cacheado por processo."""
    if nome in _CACHE:
        return _CACHE[nome]
    rows: list[dict[str, Any]] = []
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if os.environ.get("SUPABASE_URL") and key:
        try:
            from tools.supabase_client import load_create_client

            cli = load_create_client()(os.environ["SUPABASE_URL"], key)
            res = cli.table("catalogos_metodologia").select(
                "chave,valor,sinonimos,metadata").eq("catalogo", nome).execute()
            rows = [r for r in (getattr(res, "data", None) or []) if r.get("valor")]
        except Exception as e:
            print(f"[catalogos] Supabase indisponível ({nome}): {type(e).__name__}: {e}")
    if not rows:
        rows = _fallback(nome)
    _CACHE[nome] = rows
    return rows


def catalogo_lista(nome: str) -> list[str]:
    """Catálogo como lista de valores (ex.: padrões, keywords)."""
    return [c.get("valor") for c in catalogo(nome) if c.get("valor")]


def catalogo_map(nome: str) -> dict[str, str]:
    """Catálogo como dict chave→valor (ex.: olx_subdominio_uf, tipo_query_pt)."""
    return {c.get("chave"): c.get("valor") for c in catalogo(nome) if c.get("chave")}


def catalogo_num(nome: str) -> dict[str, float]:
    """Catálogo numérico: chave→metadata.valor (float). Para pesos/boosts."""
    out: dict[str, float] = {}
    for c in catalogo(nome):
        k = c.get("chave")
        v = (c.get("metadata") or {}).get("valor")
        if v is None:
            try:
                v = float(c.get("valor"))
            except (TypeError, ValueError):
                continue
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def normalizar_servicos(textos) -> list[str]:
    """Texto(s) bruto(s) de plano/oferta (marketing) → categorias de serviço LIMPAS
    (labels do catálogo 'servicos'), via match de sinônimos. Sem prosa de marketing."""
    if isinstance(textos, str):
        textos = [textos]
    blob = _norm(" ".join(str(t) for t in (textos or [])))
    if not blob:
        return []
    out: list[str] = []
    for c in catalogo("servicos"):
        chaves = list(c.get("sinonimos") or []) + [c.get("chave", "")]
        if any(_norm(k) and _norm(k) in blob for k in chaves):
            label = c.get("valor")
            if label and label not in out:
                out.append(label)
    return out
