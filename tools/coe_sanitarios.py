"""Municipal COE sanitary sizing — closed seeds (CWA) + OWA fallback.

João Pessoa (Lei 1.347/1971 art. 367) sizes gym/ginásio fixtures by training
floor area (m²), not by headcount. São Paulo (Lei 16.642/2017) uses lotação
by sex. Unknown cities → status municipio_nao_coberto (caller may use the
generic estimativa_nao_oficial tool).
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

_SEEDS_DIR = Path(__file__).resolve().parent / "coe_seeds"


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents(s or "").lower()).strip()


@lru_cache(maxsize=1)
def _load_all_seeds() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(_SEEDS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        mun = data.get("municipio") or ""
        uf = (data.get("uf") or "").upper()
        keys = {_norm_key(mun), _norm_key(f"{mun} {uf}"), _norm_key(f"{mun}/{uf}")}
        for a in data.get("aliases") or []:
            keys.add(_norm_key(str(a)))
        for k in keys:
            if k:
                out[k] = data
        if uf and mun:
            out[_norm_key(f"{mun}|{uf}")] = data
    return out


def _resolve_seed(cidade: str | None, uf: str | None) -> dict[str, Any] | None:
    seeds = _load_all_seeds()
    c = _norm_key(cidade or "")
    u = (uf or "").strip().upper()
    if not c:
        return None
    if u:
        hit = seeds.get(_norm_key(f"{cidade}|{uf}"))
        if hit and (hit.get("uf") or "").upper() == u:
            return hit
        hit = seeds.get(c)
        if hit and (hit.get("uf") or "").upper() == u:
            return hit
        return None
    return seeds.get(c)


def _citacao(seed: dict[str, Any], valor: str, base: str) -> dict[str, str]:
    return {
        "valor": valor,
        "base": base,
        "fonte": seed.get("lei") or "COE municipal",
        "janela": str(seed.get("janela") or seed.get("verificado_em") or ""),
    }


def _calc_jp_por_area(seed: dict[str, Any], area_treino_m2: float) -> dict[str, Any]:
    regra = seed["regras"]["sanitarios_por_100m2_treino_por_sexo"]
    base = float(regra["base_m2"])
    kits = max(1, math.ceil(float(area_treino_m2) / base)) if area_treino_m2 > 0 else 0
    ps = regra["por_sexo"]
    bacias_f = kits * int(ps["bacias"])
    bacias_m = kits * int(ps["bacias"])
    chuv_f = kits * int(ps["chuveiros"])
    chuv_m = kits * int(ps["chuveiros"])
    lav_f = kits * int(ps["lavatorios"])
    lav_m = kits * int(ps["lavatorios"])
    mict_m = kits * int(ps["mictorios"])
    vest = seed["regras"]["vestiario_m2_por_10m2_treino"]
    vest_m2 = round(float(area_treino_m2) * float(vest["vestiario_m2_por_treino_m2"]), 1)

    return {
        "status": "ok",
        "tipo": "coe_municipal",
        "municipio": seed["municipio"],
        "uf": seed["uf"],
        "modo": "ginasio_por_area_treino",
        "area_treino_m2": float(area_treino_m2),
        "kits_por_sexo": kits,
        "bacias_femininas": bacias_f,
        "bacias_masculinas": bacias_m,
        "lavatorios_femininos": lav_f,
        "lavatorios_masculinos": lav_m,
        "chuveiros_femininos": chuv_f,
        "chuveiros_masculinos": chuv_m,
        "mictorios_masculinos": mict_m,
        "vestiario_m2_total_min": vest_m2,
        "assimetrico": True,
        "regras_aplicadas": ["JP_ART_367_POR_AREA", "JP_ART_366_VESTIARIO", "MICTORIO_SO_MASCULINO"],
        "citacao": _citacao(
            seed,
            f"{bacias_f} bacias F / {bacias_m} bacias M + {chuv_f} chuveiros/sexo",
            f"ginásio · {area_treino_m2:g} m² de treino · art. 367 (kit/100 m²/sexo)",
        ),
        "aviso": (
            "Cota oficial do COE João Pessoa para ginásio (art. 367), por área de treino. "
            "Confirme o enquadramento da academia com arquiteto local / prefeitura antes do projeto."
        ),
        "fonte_url": seed.get("fonte_url"),
    }


def _calc_sp_por_lotacao(seed: dict[str, Any], lotacao: int) -> dict[str, Any]:
    regra = seed["regras"]["sanitarios_por_lotacao_por_sexo"]
    frac = float(seed.get("fracao_por_sexo_padrao") or 0.5)
    ppc = max(1, int(regra["pessoas_por_conjunto"]))
    lot = max(0, int(lotacao))
    por_sexo = math.ceil(lot * frac) if lot else 0
    conjuntos = math.ceil(por_sexo / ppc) if por_sexo else 0
    ps = regra["por_sexo"]
    bac = conjuntos * int(ps["bacias"])
    lav = conjuntos * int(ps["lavatorios"])
    chu = conjuntos * int(ps["chuveiros"])
    return {
        "status": "ok",
        "tipo": "coe_municipal",
        "municipio": seed["municipio"],
        "uf": seed["uf"],
        "modo": "lotacao_por_sexo",
        "lotacao": lot,
        "pessoas_por_sexo_assumidas": por_sexo,
        "bacias_femininas": bac,
        "bacias_masculinas": bac,
        "lavatorios_femininos": lav,
        "lavatorios_masculinos": lav,
        "chuveiros_femininos": chu,
        "chuveiros_masculinos": chu,
        "mictorios_masculinos": bac // 2,
        "assimetrico": False,
        "regras_aplicadas": ["SP_COE_16642_POR_LOTACAO", "FRACAO_SEXO_50_50"],
        "citacao": _citacao(
            seed,
            f"{bac} bacias + {lav} lavatórios + {chu} chuveiros por sexo",
            f"lotação {lot} · 50/50 · 1 conjunto/sexo a cada {ppc} usuários · Lei 16.642/2017",
        ),
        "aviso": (
            "Cota do COE São Paulo (Lei 16.642/2017) com fração 50/50 por sexo. "
            "Ajuste a fração se o público for claramente assimétrico. Confirme no projeto."
        ),
        "premissas": {
            "pessoas_por_conjunto": ppc,
            "fracao_por_sexo": frac,
            "vestiario_circulacao_m2_por_chuveiro": regra.get("vestiario_circulacao_m2_por_chuveiro"),
            "distancia_max_treino_sanitario_m": regra.get("distancia_max_treino_sanitario_m"),
        },
        "fonte_url": seed.get("fonte_url"),
    }


def calcular_sanitarios_municipio(
    cidade: str,
    uf: str = "",
    lotacao: int | None = None,
    area_treino_m2: float | None = None,
    espectadores: int | None = None,
) -> dict[str, Any]:
    """Official municipal COE sizing when a curated seed exists.

    Prefer this over the generic estimativa whenever cidade/UF is known.
    """
    seed = _resolve_seed(cidade, uf or None)
    if not seed:
        return {
            "status": "municipio_nao_coberto",
            "tipo": "coe_municipal",
            "cidade": cidade,
            "uf": (uf or "").upper() or None,
            "aviso": (
                "Ainda não temos o Código de Obras deste município na tabela curada. "
                "Use calcular_sanitarios_por_lotacao só como ESTIMATIVA NÃO-OFICIAL e "
                "confirme no COE da prefeitura."
            ),
            "regras_aplicadas": ["OWA_MUNICIPIO_AUSENTE"],
        }

    preferida = seed.get("entrada_preferida")
    area = float(area_treino_m2) if area_treino_m2 is not None else None
    lot = int(lotacao) if lotacao is not None else None
    esp = int(espectadores) if espectadores is not None else None

    # João Pessoa — area-first
    if preferida == "area_treino_m2":
        if area is not None and area > 0:
            return _calc_jp_por_area(seed, area)
        if esp is not None and esp > 0 and "publico_espectadores" in seed.get("regras", {}):
            reg = seed["regras"]["publico_espectadores"]
            grupos = math.ceil(esp / int(reg["por_grupo"]))
            bac = grupos * int(reg["bacias"])
            lav = grupos * int(reg["lavatorios"])
            return {
                "status": "ok",
                "tipo": "coe_municipal",
                "municipio": seed["municipio"],
                "uf": seed["uf"],
                "modo": "publico_espectadores",
                "espectadores": esp,
                "bacias_total": bac,
                "lavatorios_total": lav,
                "regras_aplicadas": ["JP_ART_367_PARAGRAFO_UNICO_PUBLICO"],
                "citacao": _citacao(
                    seed,
                    f"{bac} vasos + {lav} lavatórios (público)",
                    f"{esp} espectadores · art. 367 § único · 1 vaso+2 lav/100",
                ),
                "aviso": (
                    "Cota de sanitários de USO DO PÚBLICO (espectadores), não a dos atletas/usuários "
                    "do ginásio. Para alunos/atletas informe a área de treino (m²)."
                ),
                "fonte_url": seed.get("fonte_url"),
            }
        miss = seed.get("sem_area_treino") or {}
        return {
            "status": miss.get("status") or "precisa_area_treino",
            "tipo": "coe_municipal",
            "municipio": seed["municipio"],
            "uf": seed["uf"],
            "lotacao_informada": lot,
            "regra_resumo": (
                "por sexo, a cada 100 m² de treino: 1 vaso + 3 chuveiros + 2 lavatórios "
                "+ 2 mictórios (masculino)"
            ),
            "aviso": miss.get("mensagem") or "Informe a área útil de treino em m².",
            "regras_aplicadas": ["JP_EXIGE_AREA_TREINO"],
            "citacao": _citacao(
                seed,
                "área de treino necessária",
                "ginásio · art. 367 · dimensionamento por m² (não por lotação)",
            ),
            "fonte_url": seed.get("fonte_url"),
        }

    # São Paulo — lotação
    if preferida == "lotacao":
        if lot is None or lot <= 0:
            return {
                "status": "precisa_lotacao",
                "tipo": "coe_municipal",
                "municipio": seed["municipio"],
                "uf": seed["uf"],
                "aviso": "Informe a lotação (ocupação máxima simultânea) para aplicar o COE de São Paulo.",
                "regras_aplicadas": ["SP_EXIGE_LOTACAO"],
            }
        return _calc_sp_por_lotacao(seed, lot)

    return {
        "status": "erro",
        "tipo": "coe_municipal",
        "aviso": f"Seed de {seed.get('municipio')} sem entrada_preferida suportada.",
    }


def municipios_cobertos() -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    for seed in _load_all_seeds().values():
        key = f"{seed.get('municipio')}|{seed.get('uf')}"
        seen[key] = {"municipio": seed["municipio"], "uf": seed["uf"]}
    return sorted(seen.values(), key=lambda x: (x["uf"], x["municipio"]))
