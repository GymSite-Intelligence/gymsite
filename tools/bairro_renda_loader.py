"""
Renda e população por bairro — Fase B.

Ordem de fontes (regra de ouro: dado real com fonte/metodologia, não hardcode):
1. Tabela nacional `renda_bairro` (IBGE Censo 2022; DF = PDAD Ampliada 2024 por RA).
2. CKAN municipal (dado oficial por bairro) — ex.: Fortaleza IDH-Renda.
3. Piloto curado em data/bairro_renda_pilot/{cidade}_{uf}.json (fallback rotulado).
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


def _resolve_pilot_entry(pilot: dict[str, Any], bairro: str) -> dict[str, Any] | None:
    """Lookup piloto com aliases (ex.: asa norte → plano piloto)."""
    bn = _norm(bairro)
    bairros = pilot.get("bairros") or {}
    if bn in bairros:
        return bairros[bn]
    aliases = pilot.get("aliases") or {}
    target = aliases.get(bn)
    if target and _norm(target) in bairros:
        return bairros[_norm(target)]
    return None


def _renda_bairro_ibge(cidade: str, uf: str, bairro: str) -> dict | None:
    """Renda do bairro da tabela NACIONAL `renda_bairro` (IBGE/PDAD). best-effort."""
    import os
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not (os.environ.get("SUPABASE_URL") and key):
        return None
    try:
        from tools.supabase_client import load_create_client

        cli = load_create_client()(os.environ["SUPABASE_URL"], key)
        bn = _norm(bairro)
        # aliases DF (Asa Norte → Plano Piloto) — mesma mapa do posicionamento
        try:
            from tools.posicionamento_renda import _ALIAS_BAIRRO

            alias = _ALIAS_BAIRRO.get(((uf or "").strip().upper(), bn))
            if alias:
                bn = _norm(alias)
        except Exception:
            pass
        q = cli.table("renda_bairro").select("*").eq("bairro_norm", bn)
        if (uf or "").strip():
            q = q.eq("uf", uf.strip().upper())
        rows = getattr(q.limit(5).execute(), "data", None) or []
        if not rows:
            return None
        cnorm = _norm(cidade)
        pick = next((r for r in rows if _norm(r.get("cidade") or "") == cnorm), None)
        if pick is None:
            if len(rows) > 1:
                return None
            pick = rows[0]
        # DF: rejeita linha municipal artificial (bairro == cidade) se pediu RA/bairro real
        if (
            (uf or "").strip().upper() == "DF"
            and _norm(pick.get("bairro") or "") == cnorm
            and bn != cnorm
        ):
            return None
        return pick
    except Exception as exc:
        print(f"[bairro_renda] renda_bairro IBGE indisponível: {type(exc).__name__}: {exc}")
        return None


def enrich_demografia_bairro(
    demografia: dict[str, Any],
    cidade: str,
    bairro: str,
    uf: str,
) -> dict[str, Any]:
    """
    Preenche demografia['bairro']. Ordem: renda_bairro nacional (IBGE/PDAD) >
    CKAN 2010 (Atlas IDH-Renda) > piloto curado.
    """
    out = dict(demografia)
    bairro_block = dict(out.get("bairro") or {})
    bairro_block.setdefault("granularidade", "bairro")

    if not (bairro or "").strip():
        out["bairro"] = bairro_block
        return out

    # 0. Tabela nacional renda_bairro (IBGE 2022 ou PDAD DF 2024) — PRIMÁRIO.
    ibge = _renda_bairro_ibge(cidade, uf, bairro)
    if ibge and ibge.get("renda_pc"):
        fonte = ibge.get("fonte") or ""
        is_pdad = "PDAD" in fonte
        bairro_block["renda_media"] = ibge.get("renda_pc")  # per capita (compat cutoffs A2)
        bairro_block["renda_media_per_capita"] = ibge.get("renda_pc")
        bairro_block["renda_resp_domicilio"] = ibge.get("renda_media")
        bairro_block["renda_percentil"] = ibge.get("percentil_municipio")
        bairro_block["ranking_municipio"] = ibge.get("ranking_municipio")
        bairro_block["fonte"] = fonte
        bairro_block["data_referencia"] = str(ibge.get("ano") or ("2024" if is_pdad else "2022"))
        if is_pdad:
            bairro_block["nota"] = (
                "Renda per capita domiciliar (mediana ponderada) por RA — PDAD Ampliada 2024 "
                "(IPEDF CODEPLAN). Aliases Receita (Asa Norte etc.) mapeiam para RA."
            )
            bairro_block["granularidade"] = "ra"
        else:
            bairro_block["nota"] = (
                "Renda do responsável pelo domicílio por bairro (IBGE Censo 2022); "
                "per capita = renda / (pessoas/domicílios). Fonte nacional."
            )
        out["bairro"] = bairro_block
        return out

    # 1. CKAN municipal (dado oficial por bairro, base Censo 2010) — fallback.
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

    # 2. Piloto curado (fallback rotulado; DF = PDAD RAs).
    pilot = load_pilot_catalog(cidade, uf)
    if not pilot:
        out["bairro"] = bairro_block
        return out

    entry = _resolve_pilot_entry(pilot, bairro)
    if not entry:
        out["bairro"] = bairro_block
        return out

    bairro_block["renda_media"] = entry.get("renda_media") or entry.get("renda_pc")
    bairro_block["renda_media_per_capita"] = entry.get("renda_pc") or entry.get("renda_media")
    bairro_block["populacao"] = entry.get("populacao")
    bairro_block["fonte"] = pilot.get("fonte", "bairro_renda_pilot")
    bairro_block["dataset_id"] = entry.get("dataset_id")
    bairro_block["data_referencia"] = pilot.get("data_referencia")
    bairro_block["nota"] = pilot.get("nota")
    if "PDAD" in (pilot.get("fonte") or ""):
        bairro_block["granularidade"] = "ra"
    out["bairro"] = bairro_block
    return out
