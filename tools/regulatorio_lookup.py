"""Lookups determinísticos do domínio regulatório (CREF / anuidade PJ).

CWA só nas tabelas fechadas seedadas em tools/regulatorio_seeds/. Lacunas municipais
continuam OWA (fora deste módulo).
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "regulatorio_seeds"
_CREF_SEED = _DATA_DIR / "regulatorio_cref_por_uf.json"
_ANUIDADE_SEED = _DATA_DIR / "regulatorio_anuidade_pj_2026.json"

_UF_NOMES: dict[str, str] = {
    "ACRE": "AC",
    "ALAGOAS": "AL",
    "AMAPA": "AP",
    "AMAZONAS": "AM",
    "BAHIA": "BA",
    "CEARA": "CE",
    "DISTRITO FEDERAL": "DF",
    "ESPIRITO SANTO": "ES",
    "GOIAS": "GO",
    "MARANHAO": "MA",
    "MATO GROSSO": "MT",
    "MATO GROSSO DO SUL": "MS",
    "MINAS GERAIS": "MG",
    "PARA": "PA",
    "PARAIBA": "PB",
    "PARANA": "PR",
    "PERNAMBUCO": "PE",
    "PIAUI": "PI",
    "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN",
    "RIO GRANDE DO SUL": "RS",
    "RONDONIA": "RO",
    "RORAIMA": "RR",
    "SANTA CATARINA": "SC",
    "SAO PAULO": "SP",
    "SERGIPE": "SE",
    "TOCANTINS": "TO",
}


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def normalizar_uf(uf: str | None) -> str | None:
    if not uf or not str(uf).strip():
        return None
    raw = str(uf).strip()
    if len(raw) == 2 and raw.isalpha():
        return raw.upper()
    key = re.sub(r"\s+", " ", _strip_accents(raw).upper())
    return _UF_NOMES.get(key)


def _parse_data_ref(data_ref: str | date | datetime | None) -> date:
    if data_ref is None:
        return date.today()
    if isinstance(data_ref, datetime):
        return data_ref.date()
    if isinstance(data_ref, date):
        return data_ref
    s = str(data_ref).strip()[:10]
    return date.fromisoformat(s)


@lru_cache(maxsize=1)
def _load_cref_seed() -> dict[str, Any]:
    return json.loads(_CREF_SEED.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_anuidade_seed() -> dict[str, Any]:
    return json.loads(_ANUIDADE_SEED.read_text(encoding="utf-8"))


def _cref_codigo(label: str) -> int | None:
    m = re.search(r"CREF(\d+)", label or "", re.I)
    return int(m.group(1)) if m else None


def resolver_cref_por_uf(
    uf: str,
    data_ref: str | date | datetime | None = None,
) -> dict[str, Any]:
    """Resolve em qual CREF registrar a academia na UF (tabela fechada).

    Antes de 02/01/2027, UFs em transição usam o CREF pai (nunca o regional
    instituído mas ainda inoperante).
    """
    uf_n = normalizar_uf(uf)
    seed = _load_cref_seed()
    meta = seed["meta"]
    if not uf_n or uf_n not in seed["ufs"]:
        return {
            "status": "erro",
            "uf": uf_n,
            "cref_registro": None,
            "erro": "UF inválida ou ausente — informe a sigla (ex.: PB) ou o nome do estado.",
        }

    row = seed["ufs"][uf_n]
    ref = _parse_data_ref(data_ref)
    corte = date.fromisoformat(meta["corte_novos_regionais"])
    regras: list[str] = []

    em_transicao_seed = bool(row.get("em_transicao"))
    cref_futuro = row.get("cref_futuro")
    if em_transicao_seed and cref_futuro and ref >= corte:
        cref_registro = cref_futuro
        em_transicao = False
        regras.append("CORTE_NOVOS_REGIONAIS_ATINGIDO")
    elif em_transicao_seed and cref_futuro:
        cref_registro = row["cref_hoje"]
        em_transicao = True
        regras.extend(["UF_EM_TRANSICAO", "NAO_REGISTRAR_EM_CREF_INOPERANTE"])
    else:
        cref_registro = row["cref_hoje"]
        em_transicao = False
        regras.append("JURISDICAO_ESTAVEL")

    return {
        "status": "ok",
        "uf": uf_n,
        "cref_registro": cref_registro,
        "cref_codigo": _cref_codigo(cref_registro),
        "em_transicao": em_transicao,
        "cref_futuro": cref_futuro if em_transicao_seed else None,
        "vigencia_futuro": meta["corte_novos_regionais"] if em_transicao_seed else None,
        "resolucao_criacao": row.get("resolucao_criacao"),
        "data_ref": ref.isoformat(),
        "regras_aplicadas": regras,
        "citacao": {
            "valor": cref_registro,
            "base": f"jurisdição de registro PJ academia em {uf_n}",
            "fonte": meta["fonte"],
            "janela": meta["verificado_em"],
        },
        "aviso": (
            f"A partir de {meta['corte_novos_regionais']} o registro passa para "
            f"{cref_futuro}. Até lá, registre em {row['cref_hoje']}."
            if em_transicao
            else "Confirme a jurisdição vigente no CONFEF/CREF regional."
        ),
    }


def _resolver_cref_label_para_anuidade(
    *,
    uf: str | None,
    cref: int | str | None,
    data_ref: str | date | datetime | None,
) -> dict[str, Any]:
    seed_cref = _load_cref_seed()
    inops = seed_cref["cref_inoperantes_ate_corte"]
    corte = date.fromisoformat(seed_cref["meta"]["corte_novos_regionais"])
    ref = _parse_data_ref(data_ref)
    regras: list[str] = []
    redirecionado_de = None

    codigo: str | None = None
    if cref is not None and str(cref).strip():
        m = re.search(r"(\d+)", str(cref))
        codigo = str(int(m.group(1))) if m else None

    if codigo and codigo in inops and ref < corte:
        pai = inops[codigo]["pai"]
        redirecionado_de = inops[codigo]["label"]
        regras.append("CREF_INOPERANTE")
        return {
            "status": "ok",
            "cref_registro": pai,
            "cref_codigo": _cref_codigo(pai),
            "uf": inops[codigo].get("uf"),
            "redirecionado_de": redirecionado_de,
            "cref_operante": pai,
            "regras_aplicadas": regras,
        }

    if codigo:
        anu = _load_anuidade_seed()["por_cref"].get(codigo)
        if anu:
            return {
                "status": "ok",
                "cref_registro": anu["label"],
                "cref_codigo": int(codigo),
                "uf": (anu.get("ufs") or [None])[0],
                "regras_aplicadas": regras,
            }

    if uf:
        r = resolver_cref_por_uf(uf, data_ref=data_ref)
        if r.get("status") == "ok":
            regras.extend(r.get("regras_aplicadas") or [])
            return {
                "status": "ok",
                "cref_registro": r["cref_registro"],
                "cref_codigo": r["cref_codigo"],
                "uf": r["uf"],
                "regras_aplicadas": regras,
            }

    return {
        "status": "erro",
        "erro": "Informe uf (ex.: PB) ou cref (ex.: 10 / CREF10).",
        "regras_aplicadas": regras,
    }


def consultar_anuidade_pj_cref(
    uf: str | None = None,
    cref: int | str | None = None,
    exercicio: int | None = None,
    data_ref: str | date | datetime | None = None,
) -> dict[str, Any]:
    """Anuidade PJ: valor-base nacional (CWA) + nota regional quando curada.

    O valor FINAL com desconto continua com orientação de confirmar no regional.
    """
    seed = _load_anuidade_seed()
    meta = seed["meta"]
    exercicio_seed = int(meta["exercicio"])
    ex = int(exercicio) if exercicio is not None else exercicio_seed

    if ex != exercicio_seed:
        return {
            "status": "exercicio_nao_coberto",
            "exercicio": ex,
            "exercicio_seed": exercicio_seed,
            "valor_base_centavos": None,
            "aviso": (
                f"Seed cobre só o exercício {exercicio_seed}. "
                "Confirme a anuidade no CREF regional / Res. CONFEF do ano."
            ),
        }

    resolved = _resolver_cref_label_para_anuidade(uf=uf, cref=cref, data_ref=data_ref)
    if resolved.get("status") != "ok":
        return {**resolved, "exercicio": ex, "valor_base_centavos": None}

    codigo = str(resolved["cref_codigo"])
    # Após redirecionamento de CREF inoperante, a linha é a do pai.
    row = seed["por_cref"].get(codigo) or {}
    status = row.get("status") or "consultar_regional"
    regras = list(resolved.get("regras_aplicadas") or [])
    regras.append("VALOR_BASE_NACIONAL")

    centavos = int(meta["valor_base_centavos"])
    reais = f"{centavos // 100},{centavos % 100:02d}"

    out: dict[str, Any] = {
        "status": status,
        "exercicio": ex,
        "uf": resolved.get("uf") or (normalizar_uf(uf) if uf else None),
        "cref_registro": resolved["cref_registro"],
        "cref_codigo": resolved["cref_codigo"],
        "valor_base_centavos": centavos,
        "valor_base_reais": reais,
        "nota_regional": row.get("nota_regional"),
        "fonte_regional": row.get("fonte_regional"),
        "regras_aplicadas": regras,
        "citacao": {
            "valor": f"R$ {reais}",
            "base": meta["base_descricao"],
            "fonte": meta["fonte_base"],
            "janela": str(ex),
        },
        "aviso": meta["aviso"],
    }
    if resolved.get("redirecionado_de"):
        out["redirecionado_de"] = resolved["redirecionado_de"]
        out["cref_operante"] = resolved.get("cref_operante")
    return out
