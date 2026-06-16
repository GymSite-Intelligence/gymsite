"""
Renda e população por bairro — Fase B.

Ordem de fontes (regra de ouro: dado real com fonte/metodologia, não hardcode):
1. CKAN municipal (dado oficial por bairro) — ex.: Fortaleza, dataset
   "Desenvolvimento Humano por Bairro" (IDH-Renda → renda per capita via fórmula Atlas).
2. Piloto curado em data/bairro_renda_pilot/{cidade}_{uf}.json (fallback rotulado).
"""
from __future__ import annotations

import json
import logging
import math
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PILOT_DIR = ROOT / "data" / "bairro_renda_pilot"

# Inversão IDH-Renda → renda per capita (R$/mês). Fórmula Atlas Brasil / PNUD:
#   IDH-Renda = (ln(R) − ln(Rmin)) / (ln(Rmax) − ln(Rmin))
# → R = exp(IDH_Renda × (ln(Rmax) − ln(Rmin)) + ln(Rmin))
# Rmin/Rmax são as constantes oficiais do Atlas (renda per capita mensal, ref. 2010).
_ATLAS_RENDA_MIN = 8.59       # R$/mês — fonte: Atlas Brasil / PNUD (metodologia IDHM-Renda)
_ATLAS_RENDA_MAX = 4033.99    # R$/mês — idem

# Registry de datasets CKAN por cidade (slug cidade_uf). Bairro-renda oficial.
_CKAN_DATASETS: dict[str, dict[str, Any]] = {
    "fortaleza_ce": {
        "dataset_id": "desenvolvimento_humano_bairro",
        "bairro_col": "Bairros",
        "idh_renda_col": "IDH-Renda",
        "idh_col": "IDH",
        "ranking_col": "Ranking IDH",
        "data_referencia": "2010",
        "fonte": "CKAN dados.fortaleza.ce.gov.br — Desenvolvimento Humano por Bairro (IDH, base Censo 2010)",
    },
}

# Cache em processo do catálogo parseado por slug (evita re-baixar o XLSX por bairro).
_CKAN_CACHE: dict[str, dict[str, Any] | None] = {}


def _norm(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (s or "").strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _idhrenda_para_renda_pc(idh_renda: float) -> float:
    """IDH-Renda (0-1) → renda per capita mensal (R$), fórmula Atlas Brasil/PNUD."""
    ln_min, ln_max = math.log(_ATLAS_RENDA_MIN), math.log(_ATLAS_RENDA_MAX)
    return round(math.exp(idh_renda * (ln_max - ln_min) + ln_min), 2)


def _carregar_ckan_bairros(cidade: str, uf: str) -> dict[str, Any] | None:
    """Baixa+parseia o XLSX de bairros do CKAN municipal → {norm(bairro): {...}}.

    Cacheado por slug. Retorna None se cidade sem dataset, portal off, ou parse falhou.
    """
    slug = f"{_norm(cidade)}_{(uf or '').strip().lower()}"
    if slug in _CKAN_CACHE:
        return _CKAN_CACHE[slug]
    cfg = _CKAN_DATASETS.get(slug)
    if not cfg:
        _CKAN_CACHE[slug] = None
        return None
    try:
        import io

        import httpx

        from tools.ckan_client import PORTAIS_MUNICIPAIS, package_show

        portal = PORTAIS_MUNICIPAIS.get(_norm(cidade))
        pkg = package_show(cfg["dataset_id"], portal_base=portal)
        url = next(
            (r.get("url") for r in (pkg.get("resources") or [])
             if str(r.get("format", "")).lower() in ("xlsx", "xls")),
            None,
        )
        if not url:
            _CKAN_CACHE[slug] = None
            return None
        raw = httpx.get(url, timeout=40, follow_redirects=True).content

        import openpyxl

        ws = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True).active
        linhas = list(ws.iter_rows(values_only=True))
        if not linhas:
            _CKAN_CACHE[slug] = None
            return None
        header = [str(c or "").strip() for c in linhas[0]]
        idx = {col: header.index(col) for col in
               (cfg["bairro_col"], cfg["idh_renda_col"], cfg["idh_col"], cfg["ranking_col"])
               if col in header}
        catalogo: dict[str, Any] = {}
        for row in linhas[1:]:
            nome = row[idx[cfg["bairro_col"]]] if cfg["bairro_col"] in idx else None
            if not nome:
                continue
            try:
                idh_renda = float(row[idx[cfg["idh_renda_col"]]])
            except (TypeError, ValueError, KeyError):
                continue
            catalogo[_norm(str(nome))] = {
                "idh_renda": round(idh_renda, 4),
                "renda_media_per_capita": _idhrenda_para_renda_pc(idh_renda),
                "idh": row[idx[cfg["idh_col"]]] if cfg["idh_col"] in idx else None,
                "ranking_idh": row[idx[cfg["ranking_col"]]] if cfg["ranking_col"] in idx else None,
            }
        result = {"bairros": catalogo, "cfg": cfg} if catalogo else None
        _CKAN_CACHE[slug] = result
        return result
    except Exception as exc:  # rede/parse/portal — fallback pro piloto, nunca quebra
        logger.warning("CKAN bairro-renda %s falhou: %s: %s", slug, type(exc).__name__, exc)
        _CKAN_CACHE[slug] = None
        return None


def _pilot_path(cidade: str, uf: str) -> Path:
    slug = f"{_norm(cidade)}_{uf.strip().lower()}"
    return PILOT_DIR / f"{slug}.json"


def load_pilot_catalog(cidade: str, uf: str) -> dict[str, Any] | None:
    path = _pilot_path(cidade, uf)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def enrich_demografia_bairro(
    demografia: dict[str, Any],
    cidade: str,
    bairro: str,
    uf: str,
) -> dict[str, Any]:
    """
    Preenche demografia['bairro'] quando há entrada no piloto curado.
    """
    out = dict(demografia)
    bairro_block = dict(out.get("bairro") or {})
    bairro_block.setdefault("granularidade", "bairro")

    if not (bairro or "").strip():
        out["bairro"] = bairro_block
        return out

    # 1. CKAN municipal (dado oficial por bairro) — primário.
    ckan = _carregar_ckan_bairros(cidade, uf)
    if ckan:
        entry = (ckan.get("bairros") or {}).get(_norm(bairro))
        if entry:
            cfg = ckan["cfg"]
            bairro_block["renda_media"] = entry.get("renda_media_per_capita")
            bairro_block["renda_media_per_capita"] = entry.get("renda_media_per_capita")
            bairro_block["idh_renda"] = entry.get("idh_renda")
            bairro_block["idh"] = entry.get("idh")
            bairro_block["ranking_idh"] = entry.get("ranking_idh")
            bairro_block["fonte"] = cfg["fonte"]
            bairro_block["dataset_id"] = cfg["dataset_id"]
            bairro_block["data_referencia"] = cfg["data_referencia"]
            bairro_block["nota"] = (
                "Renda per capita derivada do IDH-Renda do bairro pela fórmula Atlas "
                "Brasil/PNUD (Rmin 8,59 / Rmax 4033,99; ref. Censo 2010). Sinal relativo "
                "de afluência do bairro, não valor corrente."
            )
            out["bairro"] = bairro_block
            return out

    # 2. Piloto curado (fallback rotulado).
    pilot = load_pilot_catalog(cidade, uf)
    if not pilot:
        out["bairro"] = bairro_block
        return out

    entry = (pilot.get("bairros") or {}).get(_norm(bairro))
    if not entry:
        out["bairro"] = bairro_block
        return out

    bairro_block["renda_media"] = entry.get("renda_media")
    bairro_block["populacao"] = entry.get("populacao")
    bairro_block["fonte"] = pilot.get("fonte", "bairro_renda_pilot")
    bairro_block["dataset_id"] = entry.get("dataset_id")
    bairro_block["data_referencia"] = pilot.get("data_referencia")
    bairro_block["nota"] = pilot.get("nota")
    out["bairro"] = bairro_block
    return out
