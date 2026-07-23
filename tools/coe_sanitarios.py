"""Municipal COE sanitary sizing — closed seeds (CWA) + OWA fallback.

João Pessoa (Lei 1.347/1971 art. 367) sizes gym/ginásio fixtures by training
floor area (m²), not by headcount. São Paulo (Lei 16.642/2017) uses lotação
by sex. Fortaleza (Lei 5.530/1981 art. 365) confirms athlete locker area by
m²; athlete fixture table (Anexo II) is not curated yet. Rio (LC 198/2019
art. 24) sizes commercial salas by m² / meeting places by público or
espectadores. Unknown cities → status municipio_nao_coberto.
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


def _estimativa_por_pico(lotacao: int) -> dict[str, Any]:
    """Planning lens by peak occupancy — NEVER the legal COE count."""
    lot = max(0, int(lotacao))
    ppc = 20
    conjuntos = math.ceil(lot / ppc) if lot else 0
    por_genero = math.ceil(conjuntos / 2) if conjuntos else 0
    acessiveis = max(1, math.ceil(conjuntos * 0.05)) if conjuntos else 0
    return {
        "tipo": "estimativa_nao_oficial",
        "papel": "planejamento_por_pico",
        "lotacao_pico": lot,
        "bacias_total": conjuntos,
        "lavatorios_total": conjuntos,
        "bacias_por_genero": por_genero,
        "lavatorios_por_genero": por_genero,
        "mictorios_masc_possiveis": por_genero // 2,
        "pecas_acessiveis_min": acessiveis,
        "premissas": {"pessoas_por_conjunto": ppc, "fracao_sexo": 0.5, "pct_acessivel": 0.05},
        "aviso": (
            "Métrica de PLANEJAMENTO pelo pico de lotação (regra genérica ~1 conjunto/20 "
            "pessoas, 50/50). NÃO substitui o Código de Obras do município."
        ),
    }


def _com_estimativa_pico(payload: dict[str, Any], lotacao: int | None) -> dict[str, Any]:
    if lotacao is None or int(lotacao) <= 0:
        return payload
    out = dict(payload)
    out["estimativa_por_pico"] = _estimativa_por_pico(int(lotacao))
    regras = list(out.get("regras_aplicadas") or [])
    if "LENTE_PICO_PLANEJAMENTO" not in regras:
        regras.append("LENTE_PICO_PLANEJAMENTO")
    out["regras_aplicadas"] = regras
    return out


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


def _calc_fortaleza_vestiario(seed: dict[str, Any], area_treino_m2: float) -> dict[str, Any]:
    """Art. 365 VI — locker area only; athlete fixture table not curated."""
    regra = seed["regras"]["vestiario_atletas_por_area_treino"]
    area = float(area_treino_m2)
    limite = float(regra.get("limite_area_treino_m2") or 10000)
    area_efetiva = min(area, limite) if area > 0 else 0.0
    ratio = float(regra["vestiario_m2_por_treino_m2"])
    min_sexo = float(regra["min_m2_por_sexo"])
    prop_total = area_efetiva * ratio
    por_sexo = max(min_sexo, prop_total / 2.0) if area_efetiva > 0 else 0.0
    total = round(por_sexo * 2.0, 1)
    pecas = seed["regras"].get("pecas_atletas") or {}
    return {
        "status": "parcial_coe",
        "tipo": "coe_municipal",
        "municipio": seed["municipio"],
        "uf": seed["uf"],
        "modo": "vestiario_por_area_treino",
        "area_treino_m2": area,
        "area_treino_m2_efetiva_para_cota": area_efetiva,
        "vestiario_m2_por_sexo_min": round(por_sexo, 1),
        "vestiario_m2_total_min": total,
        "bacias_femininas": None,
        "bacias_masculinas": None,
        "chuveiros_femininos": None,
        "chuveiros_masculinos": None,
        "pecas_atletas": {
            "status": pecas.get("status") or "tabela_anexo_ii_nao_curada",
            "artigo": pecas.get("artigo"),
            "aviso": pecas.get("descricao"),
        },
        "regras_aplicadas": [
            "FOR_ART_365_VI_VESTIARIO",
            "FOR_ART_365_V_TABELA_NAO_CURADA",
        ],
        "citacao": _citacao(
            seed,
            f"{total:g} m² de vestiário (mín. {min_sexo:g} m²/sexo)",
            f"prática de esporte · {area_efetiva:g} m² · art. 365 VI (1 m²/25 m²)",
        ),
        "aviso": (
            "Cota PARCIAL do COE Fortaleza: só o vestiário de atletas (art. 365 VI) está "
            "confirmado neste seed. Bacias/chuveiros/lavatórios dos atletas dependem da "
            "tabela do art. 365 V / Anexo II — ainda não curada. Confirme com arquiteto "
            "local / prefeitura antes do projeto."
        ),
        "fonte_url": seed.get("fonte_url"),
    }


def _rio_banheiro_funcionarios(seed: dict[str, Any]) -> dict[str, Any]:
    reg = seed["regras"]["banheiro_funcionarios"]
    return {
        "bacias": int(reg["bacias"]),
        "lavatorios": int(reg["lavatorios"]),
        "chuveiros": int(reg["chuveiros"]),
        "artigo": reg.get("artigo"),
        "descricao": reg.get("descricao"),
    }


def _rio_vestiarios_nota(seed: dict[str, Any]) -> dict[str, Any]:
    reg = seed["regras"].get("vestiarios_chuveiros_clientela") or {}
    return {
        "obrigatorio": bool(reg.get("obrigatorio")),
        "cota_numerica_no_coe": bool(reg.get("cota_numerica_no_coe")),
        "fonte": reg.get("fonte"),
        "descricao": reg.get("descricao"),
    }


def _calc_rio_salas_por_area(seed: dict[str, Any], area_util_m2: float) -> dict[str, Any]:
    regra = seed["regras"]["salas_comerciais_por_area"]
    base = max(1.0, float(regra["base_m2"]))
    area = float(area_util_m2)
    blocos = math.ceil(area / base) if area > 0 else 0
    sanitarios = blocos * int(regra["sanitarios_por_bloco"])
    return {
        "status": "ok",
        "tipo": "coe_municipal",
        "municipio": seed["municipio"],
        "uf": seed["uf"],
        "modo": "salas_comerciais_por_area",
        "area_util_m2": area,
        "sanitarios_coletivos_min": sanitarios,
        "banheiro_funcionarios": _rio_banheiro_funcionarios(seed),
        "vestiarios_chuveiros_clientela": _rio_vestiarios_nota(seed),
        "regras_aplicadas": [
            "RJ_LC198_ART24_PAR1_SALAS",
            "RJ_LC198_ART25_FUNCIONARIOS",
            "RJ_VESTIARIOS_QUALITATIVO_SMS",
        ],
        "citacao": _citacao(
            seed,
            f"{sanitarios} sanitário(s) coletivo(s) + 1 banheiro funcionários",
            f"salas · {area:g} m² úteis · art. 24 §1 (1/250 m²) + art. 25",
        ),
        "aviso": (
            "Cota do COE Rio (LC 198/2019) para salas comerciais por área útil. "
            "Vestiários/chuveiros da clientela são exigência sanitária sem cota numérica "
            "neste COE — use estimativa_por_pico só como planejamento. Confirme enquadramento "
            "com arquiteto / prefeitura."
        ),
        "fonte_url": seed.get("fonte_url"),
    }


def _calc_rio_reuniao(
    seed: dict[str, Any],
    *,
    area_publico_m2: float | None = None,
    espectadores: int | None = None,
) -> dict[str, Any]:
    regra = seed["regras"]["locais_reuniao"]
    grupos = 0
    base_txt = ""
    if area_publico_m2 is not None and area_publico_m2 > 0:
        base_m2 = max(1.0, float(regra["por_m2_publico"]))
        grupos = math.ceil(float(area_publico_m2) / base_m2)
        base_txt = f"{area_publico_m2:g} m² de público · art. 24 §2 (1 kit/100 m²)"
    elif espectadores is not None and espectadores > 0:
        por = max(1, int(regra["por_espectadores"]))
        grupos = math.ceil(int(espectadores) / por)
        base_txt = f"{espectadores} espectadores · art. 24 §2 (1 kit/500)"
    bac = grupos * int(regra["bacias"])
    lav = grupos * int(regra["lavatorios"])
    return {
        "status": "ok",
        "tipo": "coe_municipal",
        "municipio": seed["municipio"],
        "uf": seed["uf"],
        "modo": "locais_reuniao",
        "area_publico_m2": area_publico_m2,
        "espectadores": espectadores,
        "bacias_total": bac,
        "lavatorios_total": lav,
        "mictorio_facultativo": bool(regra.get("mictorio_facultativo")),
        "banheiro_funcionarios": _rio_banheiro_funcionarios(seed),
        "vestiarios_chuveiros_clientela": _rio_vestiarios_nota(seed),
        "regras_aplicadas": [
            "RJ_LC198_ART24_PAR2_REUNIAO",
            "RJ_LC198_ART25_FUNCIONARIOS",
            "RJ_VESTIARIOS_QUALITATIVO_SMS",
        ],
        "citacao": _citacao(
            seed,
            f"{bac} vasos + {lav} lavatórios (público) + 1 banheiro funcionários",
            base_txt,
        ),
        "aviso": (
            "Cota de sanitários de USO DO PÚBLICO em locais de reunião (art. 24 §2), "
            "não a cota de salas comerciais. Para academia típica prefira área útil "
            "(art. 24 §1). Confirme o enquadramento com arquiteto local."
        ),
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
    When `lotacao` (pico) is given, also attaches `estimativa_por_pico` as a
    separate PLANNING lens — never as the legal COE count.
    """
    seed = _resolve_seed(cidade, uf or None)
    if not seed:
        return _com_estimativa_pico(
            {
                "status": "municipio_nao_coberto",
                "tipo": "coe_municipal",
                "cidade": cidade,
                "uf": (uf or "").upper() or None,
                "aviso": (
                    "Ainda não temos o Código de Obras deste município na tabela curada. "
                    "Abaixo, se houver pico, vai uma estimativa de planejamento; o número "
                    "legal continua sendo o COE da prefeitura."
                ),
                "regras_aplicadas": ["OWA_MUNICIPIO_AUSENTE"],
            },
            lotacao,
        )

    preferida = seed.get("entrada_preferida")
    area = float(area_treino_m2) if area_treino_m2 is not None else None
    lot = int(lotacao) if lotacao is not None else None
    esp = int(espectadores) if espectadores is not None else None

    # João Pessoa — area-first
    if preferida == "area_treino_m2":
        if area is not None and area > 0:
            return _com_estimativa_pico(_calc_jp_por_area(seed, area), lot)
        if esp is not None and esp > 0 and "publico_espectadores" in seed.get("regras", {}):
            reg = seed["regras"]["publico_espectadores"]
            grupos = math.ceil(esp / int(reg["por_grupo"]))
            bac = grupos * int(reg["bacias"])
            lav = grupos * int(reg["lavatorios"])
            return _com_estimativa_pico(
                {
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
                        "Cota de sanitários de USO DO PÚBLICO (espectadores), não a dos "
                        "atletas/usuários do ginásio. Para alunos/atletas informe a área de "
                        "treino (m²). Se informou pico de alunos, veja também estimativa_por_pico."
                    ),
                    "fonte_url": seed.get("fonte_url"),
                },
                lot,
            )
        miss = seed.get("sem_area_treino") or {}
        return _com_estimativa_pico(
            {
                "status": miss.get("status") or "precisa_area_treino",
                "tipo": "coe_municipal",
                "municipio": seed["municipio"],
                "uf": seed["uf"],
                "lotacao_informada": lot,
                "regra_resumo": (
                    "por sexo, a cada 100 m² de treino: 1 vaso + 3 chuveiros + 2 lavatórios "
                    "+ 2 mictórios (masculino)"
                ),
                "aviso": (
                    (miss.get("mensagem") or "Informe a área útil de treino em m².")
                    + (
                        " Enquanto isso, estimativa_por_pico traz uma métrica de planejamento "
                        "pelo pico — sem valor legal."
                        if lot and lot > 0
                        else ""
                    )
                ),
                "regras_aplicadas": ["JP_EXIGE_AREA_TREINO"],
                "citacao": _citacao(
                    seed,
                    "área de treino necessária",
                    "ginásio · art. 367 · dimensionamento por m² (não por lotação)",
                ),
                "fonte_url": seed.get("fonte_url"),
            },
            lot,
        )

    # São Paulo — lotação (COE already uses peak; still expose the generic lens only if useful?
    # SP COE IS the lotação path — don't duplicate confusing second count unless different.
    if preferida == "lotacao":
        if lot is None or lot <= 0:
            return {
                "status": "precisa_lotacao",
                "tipo": "coe_municipal",
                "municipio": seed["municipio"],
                "uf": seed["uf"],
                "aviso": "Informe a lotação (ocupação máxima simultânea / pico) para aplicar o COE de São Paulo.",
                "regras_aplicadas": ["SP_EXIGE_LOTACAO"],
            }
        # SP official already is peak-based; no second generic lens (avoids two similar numbers).
        return _calc_sp_por_lotacao(seed, lot)

    # Fortaleza — vestiário por área; peças Anexo II ainda não curadas
    if preferida == "area_treino_parcial_vestiario":
        if area is not None and area > 0:
            return _com_estimativa_pico(_calc_fortaleza_vestiario(seed, area), lot)
        miss = seed.get("sem_area_treino") or {}
        return _com_estimativa_pico(
            {
                "status": miss.get("status") or "precisa_area_treino",
                "tipo": "coe_municipal",
                "municipio": seed["municipio"],
                "uf": seed["uf"],
                "lotacao_informada": lot,
                "regra_resumo": (
                    "vestiário de atletas: 1 m² por 25 m² de prática de esporte "
                    "(mín. 8 m²/sexo); peças sanitárias no Anexo II ainda não curadas"
                ),
                "aviso": (
                    (miss.get("mensagem") or "Informe a área útil de treino em m².")
                    + (
                        " Enquanto isso, estimativa_por_pico traz uma métrica de planejamento "
                        "pelo pico — sem valor legal."
                        if lot and lot > 0
                        else ""
                    )
                ),
                "regras_aplicadas": ["FOR_EXIGE_AREA_TREINO"],
                "citacao": _citacao(
                    seed,
                    "área de prática de esporte necessária",
                    "ginásio/clube · art. 365 VI · vestiário por m²",
                ),
                "fonte_url": seed.get("fonte_url"),
            },
            lot,
        )

    # Rio — área útil (salas) ou espectadores (locais de reunião)
    if preferida == "area_util_ou_espectadores":
        if area is not None and area > 0:
            return _com_estimativa_pico(_calc_rio_salas_por_area(seed, area), lot)
        if esp is not None and esp > 0:
            return _com_estimativa_pico(
                _calc_rio_reuniao(seed, espectadores=esp),
                lot,
            )
        miss = seed.get("sem_area_treino") or {}
        return _com_estimativa_pico(
            {
                "status": miss.get("status") or "precisa_area_util",
                "tipo": "coe_municipal",
                "municipio": seed["municipio"],
                "uf": seed["uf"],
                "lotacao_informada": lot,
                "banheiro_funcionarios": _rio_banheiro_funcionarios(seed),
                "vestiarios_chuveiros_clientela": _rio_vestiarios_nota(seed),
                "regra_resumo": (
                    "salas comerciais: 1 sanitário / 250 m² úteis (art. 24 §1); "
                    "locais de reunião: 1 vaso+1 lav / 100 m² público ou / 500 espectadores "
                    "(art. 24 §2); banheiro funcionários obrigatório (art. 25)"
                ),
                "aviso": (
                    (miss.get("mensagem") or "Informe a área útil em m².")
                    + (
                        " Enquanto isso, estimativa_por_pico traz uma métrica de planejamento "
                        "pelo pico — sem valor legal."
                        if lot and lot > 0
                        else ""
                    )
                ),
                "regras_aplicadas": [
                    "RJ_EXIGE_AREA_OU_ESPECTADORES",
                    "RJ_LC198_ART25_FUNCIONARIOS",
                    "RJ_VESTIARIOS_QUALITATIVO_SMS",
                ],
                "citacao": _citacao(
                    seed,
                    "área útil ou espectadores necessários",
                    "LC 198/2019 art. 24 · cotas por m² / público",
                ),
                "fonte_url": seed.get("fonte_url"),
            },
            lot,
        )

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
