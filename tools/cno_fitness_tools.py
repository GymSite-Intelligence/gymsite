"""
Cruzamento CNO (Cadastro Nacional de Obras) x entrantes CNPJ fitness.

Área (m²) vem do CNO quando há match confiável — alimenta benchmark m²/aluno do A4.
Sem match: não estimar área (sem inventar).
"""
from __future__ import annotations

import csv
import logging
import os
import re
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from tools.bairro_normalize import (
    bairro_em_alvo,
    formatar_bairro_exibicao,
    normalizar_bairro,
)
from tools.cnpj_fitness_tools import listar_entrantes_cnpj_fitness
from tools.financial_tools import (
    CNO_SITUACAO_EM_CURSO,
    CNO_SITUACAO_ENCERRADA,
    MATRICULADOS_POR_M2,
    projecao_demanda_receita_obra,
)
from tools.parametros_metodologia import param, param_int

_ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger("gymsite.cno")
_encoding_replacement_hits = 0

_METODOS_CLASSIFICACAO = frozenset({"keyword", "cnpj_cnae", "cnpj_cnae_area_atipica"})


def _note_encoding_field(cno_id: str, field: str, value: str) -> None:
    """Log debug quando leitura CSV pode ter perdido caracteres (errors=replace)."""
    global _encoding_replacement_hits
    if not value:
        return
    suspicious = "\ufffd" in value or (
        "?" in value and value != "?" and value.count("?") >= 2
    )
    if not suspicious:
        return
    _encoding_replacement_hits += 1
    logger.debug(
        "CNO %s campo %s: possível problema de encoding: %s",
        cno_id,
        field,
        value[:120],
    )


def _flush_encoding_replacement_log(context: str) -> None:
    global _encoding_replacement_hits
    if _encoding_replacement_hits >= 10:
        logger.warning(
            "CNO %s: %d campos com possível replacement de encoding no CSV",
            context,
            _encoding_replacement_hits,
        )
    _encoding_replacement_hits = 0

# Faixa plausível para unidade fitness comercial (obra) — sourced via param()
_AREA_MIN_M2 = param("cno_area_min_m2")
_AREA_MAX_M2 = param("cno_area_max_m2")

# CNAE do negócio (CNPJ) — NÃO confundir com CNAE da obra (4120400 = construção)
_CNAE_ACADEMIA = "9313100"

# ── Regra composta CNO fitness ─────────────────────────────────────────────
# Filtro primário: keywords no nome + área + exclusões.
# Alta confiança: CNPJ responsável com CNAE principal 9313100.

_KEYWORDS_OBRA_FITNESS = (
    "academ",
    "fitness",
    "gym",
    "pilates",
    "crossfit",
    "cross fit",
    "condicionamento",
    "muscul",
    "smart fit",
    "selfit",
    "bluefit",
    "bodytech",
    "ayo fit",
    "max forma",
    "panobianco",
    "top up",
    "greenlife",
    "bio ritmo",
    "velocity",
    "curves",
    "contorno",
)

_KEYWORDS_EXCLUSAO_OBRA = (
    "centros academicos",
    "uece",
    "universidade",
    "educacao e tecnologia",
    "reitoria",
    "escola",
    "cas da ",
    "manut dos centros",
    "centro educativo",
    "fundacao educacional",
    "instituto federal",
    "senac",
    "sesi",
    "prefeitura",
    "secretaria de educacao",
    "creche",
    "bercario",
    "muro de contorno",
    "contorno do campus",
)

# Duração obra (encerradas): filtros de plausibilidade — sourced via param()
_DURACAO_MIN_DIAS = param_int("cno_duracao_min_dias")
_DURACAO_MAX_DIAS = param_int("cno_duracao_max_dias")
_DIAS_POR_M2_MIN = param("cno_dias_por_m2_min")
_DIAS_POR_M2_MAX = param("cno_dias_por_m2_max")


def _normalize_cnae(cnae: str | None) -> str:
    return re.sub(r"\D", "", cnae or "")


def _match_keywords_fitness(nome: str) -> bool:
    n = (nome or "").lower()
    return any(kw in n for kw in _KEYWORDS_OBRA_FITNESS)


def _match_exclusao(nome: str) -> bool:
    n = (nome or "").lower()
    return any(ex in n for ex in _KEYWORDS_EXCLUSAO_OBRA)


def _eh_obra_fitness(
    nome_obra: str,
    area_m2: float,
    cnpj_responsavel_cnae_principal: str | None = None,
) -> tuple[bool, str]:
    """
    Classifica obra fitness no CNO.

    Retorna (eh_fitness, metodo) com metodo em
    keyword | cnpj_cnae | cnpj_cnae_area_atipica | "" (não fitness).
    """
    cnae_norm = _normalize_cnae(cnpj_responsavel_cnae_principal)
    if cnae_norm == _CNAE_ACADEMIA or cnae_norm.startswith("931310"):
        if _AREA_MIN_M2 <= area_m2 <= _AREA_MAX_M2:
            return True, "cnpj_cnae"
        return True, "cnpj_cnae_area_atipica"

    if not (_AREA_MIN_M2 <= area_m2 <= _AREA_MAX_M2):
        return False, ""
    if _match_exclusao(nome_obra):
        return False, ""
    if _match_keywords_fitness(nome_obra):
        return True, "keyword"
    return False, ""


def _load_cno_cnaes_index(cno_dir: Path) -> dict[str, list[dict]]:
    """Índice CNO → CNAEs da obra (enriquecimento; não filtro primário)."""
    path = cno_dir / "cno_cnaes.csv"
    by_cno: dict[str, list[dict]] = {}
    if not path.is_file():
        return by_cno
    with open(path, encoding="latin-1", errors="replace") as f:
        for row in csv.DictReader(f):
            cno_id = (row.get("CNO") or "").strip()
            if not cno_id:
                continue
            by_cno.setdefault(cno_id, []).append(
                {"cnae": (row.get("CNAE") or "").strip()}
            )
    return by_cno


def _fitness_cnpj_cnae_index(cidade: str, uf: str) -> dict[str, str]:
    """CNPJ responsável → CNAE principal (entrantes fitness do município)."""
    out: dict[str, str] = {}
    try:
        resp = listar_entrantes_cnpj_fitness(cidade, uf, dias=3650, limit=10_000)
        for row in resp.get("entrantes") or []:
            if not isinstance(row, dict):
                continue
            cnpj = _digits(str(row.get("cnpj") or ""))
            if len(cnpj) != 14:
                continue
            cnae = _normalize_cnae(row.get("cnae_principal") or row.get("cnae_fiscal_principal"))
            out[cnpj] = cnae or _CNAE_ACADEMIA
    except Exception as e:
        # Sem log, uma falha aqui (timeout/auth) descartava silenciosamente o
        # match por CNAE — obras com CNAE certo e nome atípico sumiam.
        logger.warning("CNPJ CNAE index falhou (%s: %s); fallback vazio", type(e).__name__, e)
    return out


def _load_obras_fitness_municipio(
    cno_dir: Path,
    municipio: str,
    cidade: str,
    uf: str,
    *,
    cnpj_cnae_por_cnpj: dict[str, str] | None = None,
    **kwargs: Any,
) -> list[dict]:
    # Prod: lê do banco (minerado do BigQuery) quando CNO_SOURCE=supabase.
    if _cno_supabase_enabled():
        obras = _supabase_obras_fitness_municipio(municipio, **kwargs)
        if obras is not None:  # None = erro → fallback CSV; [] = município sem obras (ok)
            return obras
    idx = cnpj_cnae_por_cnpj if cnpj_cnae_por_cnpj is not None else _fitness_cnpj_cnae_index(cidade, uf)
    return _load_fortaleza_cno(cno_dir, municipio, cnpj_cnae_por_cnpj=idx, **kwargs)


def _cnpj_cnae_from_entrantes(entrantes_resp: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for e in entrantes_resp.get("entrantes") or []:
        cnpj = _digits(str(e.get("cnpj") or ""))
        if len(cnpj) != 14:
            continue
        cnae = _normalize_cnae(e.get("cnae_principal") or e.get("cnae_fiscal_principal"))
        out[cnpj] = cnae or _CNAE_ACADEMIA
    return out


MUNICIPIO_CNO_INDISPONIVEL = "indisponivel"
_municipio_cno_cache: dict[tuple[str, str], str] = {}


def _ascii_fold(s: str) -> str:
    """Fold para ASCII A-Z0-9 (tolera acentos e mojibake utf-8 lido como latin-1)."""
    import unicodedata

    base = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]", "", base.upper())


def _discover_municipio_codigo_csv(cno_dir: Path, cidade: str) -> str | None:
    """Resolve o código RFB do município lendo o nome no próprio cno.csv."""
    alvo = _ascii_fold(cidade)
    main = cno_dir / "cno.csv"
    if not alvo or not main.is_file():
        return None
    with open(main, encoding="latin-1", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        hdr = _map_headers(fieldnames)  # pyright: ignore[reportArgumentType]
        nome_col = next(
            (
                h
                for h in fieldnames
                if "nome" in h.lower() and "munic" in h.lower() and "digo" not in h.lower()
            ),
            None,
        )
        if not nome_col or not hdr.get("municipio"):
            return None
        for row in reader:
            nome = _ascii_fold(row.get(nome_col) or "")
            if nome and (alvo == nome or alvo in nome or nome in alvo):
                code = _val(row, hdr, "municipio")
                if code:
                    return code
    return None


def _resolve_municipio_codigo_cno(
    cidade: str, uf: str = "CE", *, cno_dir: str | Path | None = None
) -> str:
    """
    Código do município na tabela RFB/CNO (ex.: Fortaleza = 1389).

    Ordem: mapa estático IBGE→RFB → descoberta dinâmica no cno.csv pelo nome.
    Sem mapeamento retorna ``MUNICIPIO_CNO_INDISPONIVEL`` — nunca assume Fortaleza.
    """
    cache_key = ((cidade or "").strip().upper(), (uf or "").strip().upper())
    cached = _municipio_cno_cache.get(cache_key)
    if cached:
        return cached

    try:
        from tools.ibge_tools import buscar_municipio
        from tools.rfb_cnpj_fitness_loader import IBGE_TO_RFB_MUNICIPIO

        mun = buscar_municipio(cidade, uf)
        if mun and mun.get("codigo"):
            mapped = IBGE_TO_RFB_MUNICIPIO.get(str(mun["codigo"]))
            if mapped:
                _municipio_cno_cache[cache_key] = mapped
                return mapped
    except Exception:
        pass

    # Supabase: resolve o código RFB pela própria tabela (IBGE→RF) — cobre cidades
    # fora do mapa estático sem precisar do extract local.
    if _cno_supabase_enabled():
        try:
            from tools.ibge_tools import buscar_municipio

            mun = buscar_municipio(cidade, uf)
            ibge = str(mun.get("codigo")) if mun and mun.get("codigo") else None
            if ibge:
                res = (
                    _cno_client()
                    .table("cno_obras_fitness")
                    .select("id_municipio_rf")
                    .eq("id_municipio", ibge)
                    .limit(1)
                    .execute()
                )
                data = getattr(res, "data", None) or []
                # RF code se a cidade tem obras; senão o próprio IBGE (cidade coberta,
                # 0 obras → loader casa id_municipio e devolve ok+vazio, não indisponivel).
                code = str(data[0]["id_municipio_rf"]) if (data and data[0].get("id_municipio_rf")) else ibge
                _municipio_cno_cache[cache_key] = code
                return code
        except Exception:
            pass

    if cno_dir is not None:
        try:
            found = _discover_municipio_codigo_csv(Path(cno_dir), cidade)
            if found:
                _municipio_cno_cache[cache_key] = found
                return found
        except Exception:
            pass

    return MUNICIPIO_CNO_INDISPONIVEL


def _map_headers(fieldnames: list[str]) -> dict[str, str]:
    """Mapeia chaves lógicas → nome real da coluna (encoding latin-1)."""
    m: dict[str, str] = {}
    for h in fieldnames:
        hl = h.lower()
        if h == "CNO" or hl == "cno":
            m["cno"] = h
        elif hl == "cep":
            m["cep"] = h
        elif hl == "nome" and "pais" not in hl and "munic" not in hl:
            m["nome"] = h
        elif "rea total" in hl or "area total" in hl:
            m["area"] = h
        elif "digo do municipio" in hl or "codigo do municipio" in hl:
            m["municipio"] = h
        elif "respons" in hl:
            m["cnpj"] = h
        elif hl == "logradouro":
            m["logradouro"] = h
        elif "mero do logradouro" in hl:
            m["numero"] = h
        elif hl == "bairro":
            m["bairro"] = h
        elif "data de in" in hl and "respons" not in hl and "registro" not in hl:
            m["data_inicio"] = h
        elif "situa" in hl and "data" not in hl:
            m["situacao"] = h
        elif "data da situa" in hl:
            m["data_situacao"] = h
    return m


def _val(row: dict, hdr: dict[str, str], key: str) -> str:
    col = hdr.get(key)
    if not col:
        return ""
    return (row.get(col) or "").strip()


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _float(s: str) -> float:
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _nome_score(obra_nome: str, fantasia: str, razao: str = "") -> int:
    o = (obra_nome or "").lower()
    texto = f"{fantasia or ''} {razao or ''}".lower()
    if not texto.strip() or not o:
        return 0
    score = 0
    marcas = (
        "fabrica", "monstro", "smart fit", "selfit", "bluefit", "bodytech",
        "academ", "fitness", "crossfit", "pilates", "muscul", "condicionamento",
    )
    score += sum(2 for m in marcas if m in texto and m in o)
    tokens = [t for t in re.split(r"\W+", texto) if len(t) >= 4]
    score += sum(1 for t in tokens if t in o)
    return score


def _normalizar_logradouro(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _load_cno_obras_municipio(
    cno_dir: Path,
    municipio: str,
    *,
    somente_em_curso: bool | None = None,
    situacao_filtro: Literal["em_curso", "encerrada", "todas"] | None = None,
    area_min: float = 0.0,
    area_max: float = 999_999.0,
) -> list[dict]:
    """Todas as obras do município no CNO (sem filtro fitness — base do cruzamento CNPJ→CNO)."""
    main = cno_dir / "cno.csv"
    if not main.is_file():
        return []

    obras: list[dict] = []
    with open(main, encoding="latin-1", errors="replace") as f:
        reader = csv.DictReader(f)
        hdr = _map_headers(reader.fieldnames or [])  # pyright: ignore[reportArgumentType]
        for row in reader:
            if _val(row, hdr, "municipio") != municipio:
                continue
            area = _float(_val(row, hdr, "area"))
            if area < area_min or area > area_max:
                continue
            situacao_cod = _val(row, hdr, "situacao").zfill(2) if _val(row, hdr, "situacao") else ""
            situacao = _situacao_label(situacao_cod)
            if situacao_filtro == "em_curso" and situacao != "em_curso":
                continue
            if situacao_filtro == "encerrada" and situacao != "encerrada":
                continue
            if somente_em_curso is True and situacao != "em_curso":
                continue
            if somente_em_curso is False and situacao == "em_curso":
                continue

            cno_id = _val(row, hdr, "cno")
            nome = _val(row, hdr, "nome")
            _note_encoding_field(cno_id, "nome", nome)
            obras.append(
                {
                    "cno": cno_id,
                    "cnpj_responsavel": _digits(_val(row, hdr, "cnpj")),
                    "cep": _digits(_val(row, hdr, "cep")),
                    "nome_obra": nome,
                    "area_m2": area,
                    "situacao_obra": situacao,
                    "situacao_codigo": situacao_cod or None,
                    "logradouro": _val(row, hdr, "logradouro"),
                    "numero": _val(row, hdr, "numero"),
                    "bairro": _val(row, hdr, "bairro"),
                    "bairro_chave": normalizar_bairro(_val(row, hdr, "bairro")),
                    "data_inicio": _val(row, hdr, "data_inicio") or None,
                    "classificacao_fitness": _eh_obra_fitness(nome, area)[0],
                }
            )
    _flush_encoding_replacement_log(f"obras_municipio:{municipio}")
    return obras


def _match_obra_cno_entrante(
    entrante: dict[str, Any],
    obras_municipio: list[dict],
) -> tuple[dict | None, str | None, str | None]:
    """
    Busca obra CNO para um CNPJ fitness (fluxo CNPJ → CNO).

    Retorna (obra|resumo_parcial, metodo, confianca).
    """
    cnpj = _digits(entrante.get("cnpj") or "")
    cep8 = _digits(entrante.get("cep") or "")[:8]
    fantasia = entrante.get("nome_fantasia") or ""
    razao = entrante.get("razao_social") or ""
    num_e = _digits(str(entrante.get("numero") or ""))
    log_e = _normalizar_logradouro(entrante.get("logradouro") or "")

    if len(cnpj) == 14:
        for o in obras_municipio:
            if o.get("cnpj_responsavel") == cnpj:
                return o, "cnpj_responsavel", "alta"

    candidatos_cep = [
        o for o in obras_municipio
        if cep8 and len(cep8) == 8 and (o.get("cep") or "").startswith(cep8)
    ]
    candidatos_cep.sort(
        key=lambda o: (
            0 if o.get("situacao_obra") == "em_curso" else 1,
            -float(o.get("area_m2") or 0),
        )
    )

    for o in candidatos_cep:
        num_o = _digits(str(o.get("numero") or ""))
        if num_e and num_o and num_e == num_o:
            return o, "endereco_cep_numero", "alta"

    # Logradouro parcial só sem número no CNPJ — evita confundir nºs da mesma via
    if not num_e:
        for o in candidatos_cep:
            log_o = _normalizar_logradouro(o.get("logradouro") or "")
            if log_e and log_o and (log_e in log_o or log_o in log_e):
                return o, "endereco_cep_logradouro", "alta"

    scored = sorted(
        (
            (o, _nome_score(o["nome_obra"], fantasia, razao))
            for o in candidatos_cep
        ),
        key=lambda x: (-x[1], -float(x[0].get("area_m2") or 0)),
    )
    if scored and scored[0][1] >= 1:
        return scored[0][0], "nome_obra_cep8", "media"

    if candidatos_cep:
        areas = [float(o["area_m2"]) for o in candidatos_cep if o.get("area_m2")]
        if areas:
            return (
                {
                    "area_m2_min": min(areas),
                    "area_m2_max": max(areas),
                    "obras_no_cep": len(candidatos_cep),
                    "nota": "várias obras no CEP; sem match por nome/endereço",
                },
                "cep8_multiplas_obras",
                "baixa",
            )

    return None, None, None


def _capacidade_por_m2(area: float, perfil: str = "mid") -> dict[str, int]:
    mat = MATRICULADOS_POR_M2.get(perfil, MATRICULADOS_POR_M2["mid"])
    return {
        "matriculas_conservador": int(area * mat["conservador"]),
        "matriculas_realista": int(area * mat["realista"]),
        "matriculas_agressivo": int(area * mat["agressivo"]),
    }


def _inferir_faixa_ticket(nome_obra: str) -> str:
    n = (nome_obra or "").lower()
    if any(
        x in n
        for x in (
            "smart fit",
            "selfit",
            "bluefit",
            "ayo fit",
            "ayo ",
            "live fit",
            "pratique",
        )
    ):
        return "low"
    if any(x in n for x in ("bodytech", "bio ritmo", "velocity")):
        return "premium"
    return "mid"


def _parse_date_br(s: str) -> date | None:
    s = (s or "").strip()
    if not s or s in ("0", "0000-00-00"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def _faixa_porte_m2(area: float) -> str:
    if area < 600:
        return "pequena"
    if area < 1_500:
        return "media"
    return "grande"


def _percentil(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    s = sorted(vals)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _situacao_label(codigo: str) -> str:
    c = (codigo or "").strip().zfill(2)
    if c in CNO_SITUACAO_EM_CURSO:
        return "em_curso"
    if c in CNO_SITUACAO_ENCERRADA:
        return "encerrada"
    return "outra"


def _load_fortaleza_cno(
    cno_dir: Path,
    municipio: str = "1389",
    *,
    somente_em_curso: bool | None = None,
    situacao_filtro: Literal["em_curso", "encerrada", "todas"] | None = None,
    incluir_projecao: bool = True,
    cnpj_cnae_por_cnpj: dict[str, str] | None = None,
) -> list[dict]:
    main = cno_dir / "cno.csv"
    if not main.is_file():
        return []

    cnae_idx = _load_cno_cnaes_index(cno_dir)

    obras: list[dict] = []
    with open(main, encoding="latin-1", errors="replace") as f:
        reader = csv.DictReader(f)
        hdr = _map_headers(reader.fieldnames or [])  # pyright: ignore[reportArgumentType]
        for row in reader:
            if _val(row, hdr, "municipio") != municipio:
                continue

            area = _float(_val(row, hdr, "area"))
            cno_id = _val(row, hdr, "cno")
            nome = _val(row, hdr, "nome")
            _note_encoding_field(cno_id, "nome", nome)
            cnpj_resp = _digits(_val(row, hdr, "cnpj"))

            cnae_responsavel = (cnpj_cnae_por_cnpj or {}).get(cnpj_resp) if cnpj_resp else None
            eh_fitness, metodo = _eh_obra_fitness(nome, area, cnae_responsavel)
            if not eh_fitness:
                continue

            situacao_cod = _val(row, hdr, "situacao").zfill(2) if _val(row, hdr, "situacao") else ""
            situacao = _situacao_label(situacao_cod)
            if situacao_filtro == "em_curso" and situacao != "em_curso":
                continue
            if situacao_filtro == "encerrada" and situacao != "encerrada":
                continue
            if somente_em_curso is True and situacao != "em_curso":
                continue
            if somente_em_curso is False and situacao == "em_curso":
                continue

            data_inicio_s = _val(row, hdr, "data_inicio")
            data_situacao_s = _val(row, hdr, "data_situacao")
            data_fim_cadastral = (
                data_situacao_s if situacao == "encerrada" and data_situacao_s else None
            )

            faixa = _inferir_faixa_ticket(nome)
            proj = (
                projecao_demanda_receita_obra(area, faixa)
                if incluir_projecao
                else None
            )
            obras.append(
                {
                    "cno": cno_id,
                    "cnpj_responsavel": cnpj_resp,
                    "cep": _digits(_val(row, hdr, "cep")),
                    "nome_obra": nome,
                    "area_m2": area,
                    "situacao_codigo": situacao_cod or None,
                    "situacao_obra": situacao,
                    "faixa_ticket_inferida": faixa,
                    "faixa_porte_m2": _faixa_porte_m2(area),
                    "logradouro": _val(row, hdr, "logradouro"),
                    "numero": _val(row, hdr, "numero"),
                    "bairro": _val(row, hdr, "bairro"),
                    "bairro_chave": normalizar_bairro(_val(row, hdr, "bairro")),
                    "bairro_label": formatar_bairro_exibicao(_val(row, hdr, "bairro")),
                    "data_inicio": data_inicio_s or None,
                    "data_situacao": data_situacao_s or None,
                    "data_fim_cadastral": data_fim_cadastral,
                    "metodo_classificacao": metodo,
                    "cnaes_obra": cnae_idx.get(cno_id, []),
                    "capacidade_matriculas_estimada": _capacidade_por_m2(area, faixa),
                    "projecao_receita": proj if proj and proj.get("status") == "ok" else None,
                }
            )
    _flush_encoding_replacement_log(f"fitness_municipio:{municipio}")
    return obras


# ── Leitura via Supabase (public.cno_obras_fitness) ────────────────────────────
# Prod lê do banco (minerado do BigQuery basedosdados) em vez do extract local.
# Gate: CNO_SOURCE=supabase. Default (local/teste) = extract CSV. Fallback: se a
# query falhar, cai pro CSV. Ver docs/arquitetura/COMPILADO_FONTES_DADOS.md §7.

_cno_supabase_client: Any = None


def _cno_supabase_enabled() -> bool:
    if (os.environ.get("CNO_SOURCE") or "").strip().lower() != "supabase":
        return False
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    return bool(os.environ.get("SUPABASE_URL") and key)


def _cno_client():
    global _cno_supabase_client
    if _cno_supabase_client is not None:
        return _cno_supabase_client
    from tools.supabase_client import load_create_client

    create_client = load_create_client()
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    _cno_supabase_client = create_client(os.environ["SUPABASE_URL"], key)
    return _cno_supabase_client


def _obra_supabase_to_dict(r: dict, *, incluir_projecao: bool = True) -> dict:
    """Mapeia linha de cno_obras_fitness pro mesmo shape de _load_fortaleza_cno."""
    nome = r.get("nome") or r.get("nome_empresarial") or r.get("nome_responsavel") or ""
    area = float(r.get("area_m2") or 0)
    situacao_cod = (r.get("situacao") or "").strip().zfill(2) if r.get("situacao") else ""
    situacao = _situacao_label(situacao_cod)
    faixa = _inferir_faixa_ticket(nome)
    proj = projecao_demanda_receita_obra(area, faixa) if incluir_projecao else None
    data_situacao_s = r.get("data_situacao")
    return {
        "cno": r.get("id_cno"),
        "cnpj_responsavel": _digits(r.get("ni_responsavel") or ""),
        "cep": _digits(r.get("cep") or ""),
        "nome_obra": nome,
        "area_m2": area,
        "situacao_codigo": situacao_cod or None,
        "situacao_obra": situacao,
        "faixa_ticket_inferida": faixa,
        "faixa_porte_m2": _faixa_porte_m2(area),
        "logradouro": r.get("logradouro"),
        "numero": r.get("numero_logradouro"),
        "bairro": r.get("bairro"),
        "bairro_chave": normalizar_bairro(r.get("bairro") or ""),
        "bairro_label": formatar_bairro_exibicao(r.get("bairro") or ""),
        "data_inicio": r.get("data_inicio") or None,
        "data_situacao": data_situacao_s or None,
        "data_fim_cadastral": (data_situacao_s if situacao == "encerrada" and data_situacao_s else None),
        "metodo_classificacao": r.get("metodo_classificacao"),
        "cnaes_obra": [],
        "capacidade_matriculas_estimada": _capacidade_por_m2(area, faixa),
        "projecao_receita": proj if proj and proj.get("status") == "ok" else None,
    }


def _supabase_obras_fitness_municipio(
    municipio: str,
    *,
    somente_em_curso: bool | None = None,
    situacao_filtro: Literal["em_curso", "encerrada", "todas"] | None = None,
    incluir_projecao: bool = True,
    **_ignored: Any,
) -> list[dict] | None:
    """Obras fitness do município (id_municipio_rf) no Supabase. None em erro → fallback CSV."""
    try:
        res = (
            _cno_client()
            .table("cno_obras_fitness")
            .select("*")
            .or_(f"id_municipio_rf.eq.{municipio},id_municipio.eq.{municipio}")
            .execute()
        )
        linhas = getattr(res, "data", None) or []
    except Exception as e:
        logger.warning("cno leitura Supabase falhou (%s): %s: %s", municipio, type(e).__name__, e)
        return None

    obras: list[dict] = []
    for r in linhas:
        o = _obra_supabase_to_dict(r, incluir_projecao=incluir_projecao)
        sit = o["situacao_obra"]
        if situacao_filtro == "em_curso" and sit != "em_curso":
            continue
        if situacao_filtro == "encerrada" and sit != "encerrada":
            continue
        if somente_em_curso is True and sit != "em_curso":
            continue
        if somente_em_curso is False and sit == "em_curso":
            continue
        obras.append(o)
    return obras


def calcular_benchmark_tempo_obra_cno(
    *,
    cno_dir: str | Path,
    municipio: str | None = None,
    cidade: str = "Fortaleza",
    uf: str = "CE",
) -> dict[str, Any]:
    """
    Benchmark de tempo de obra a partir de registros **encerrados** no CNO.

    - Início: Data de início da obra
    - Fim: Data da situação quando situação = encerrada (cadastral RFB, não previsão)

    Normaliza por m²: dias_por_m2 = (fim − início) / area_m2
    """
    cno_path = Path(cno_dir)
    if municipio is None:
        municipio = _resolve_municipio_codigo_cno(cidade, uf, cno_dir=cno_path)
    if municipio == MUNICIPIO_CNO_INDISPONIVEL:
        return {
            "status": "indisponivel",
            "motivo": "municipio_sem_mapeamento_rfb",
            "cidade": cidade,
            "uf": uf,
            "metricas": {"n": 0},
            "por_porte_m2": {},
        }
    encerradas = _load_obras_fitness_municipio(
        cno_path,
        municipio,
        cidade,
        uf,
        situacao_filtro="encerrada",
        incluir_projecao=False,
    )

    amostra: list[dict[str, Any]] = []
    rejeitadas = {"datas_invalidas": 0, "duracao_fora_faixa": 0, "dias_por_m2_fora_faixa": 0}

    for o in encerradas:
        di = _parse_date_br(o.get("data_inicio") or "")
        df = _parse_date_br(o.get("data_fim_cadastral") or "")
        area = float(o.get("area_m2") or 0)
        if not di or not df or df <= di or area <= 0:
            rejeitadas["datas_invalidas"] += 1
            continue
        dias = (df - di).days
        if dias < _DURACAO_MIN_DIAS or dias > _DURACAO_MAX_DIAS:
            rejeitadas["duracao_fora_faixa"] += 1
            continue
        dias_por_m2 = dias / area
        if dias_por_m2 < _DIAS_POR_M2_MIN or dias_por_m2 > _DIAS_POR_M2_MAX:
            rejeitadas["dias_por_m2_fora_faixa"] += 1
            continue
        amostra.append(
            {
                "cno": o.get("cno"),
                "nome_obra": o.get("nome_obra"),
                "area_m2": area,
                "bairro": o.get("bairro"),
                "data_inicio": o.get("data_inicio"),
                "data_fim_cadastral": o.get("data_fim_cadastral"),
                "duracao_dias": dias,
                "dias_por_m2": round(dias_por_m2, 4),
                "faixa_porte_m2": o.get("faixa_porte_m2"),
            }
        )

    def _agg(rows: list[dict]) -> dict[str, Any]:
        if not rows:
            return {"n": 0}
        dias_list = [r["duracao_dias"] for r in rows]
        dpm2_list = [r["dias_por_m2"] for r in rows]
        return {
            "n": len(rows),
            "duracao_dias_mediana": int(statistics.median(dias_list)),
            "duracao_dias_p25": int(_percentil(dias_list, 0.25) or 0),
            "duracao_dias_p75": int(_percentil(dias_list, 0.75) or 0),
            "dias_por_m2_mediana": round(statistics.median(dpm2_list), 4),
            "dias_por_m2_p25": round(_percentil(dpm2_list, 0.25) or 0, 4),
            "dias_por_m2_p75": round(_percentil(dpm2_list, 0.75) or 0, 4),
        }

    por_porte: dict[str, Any] = {}
    for porte in ("pequena", "media", "grande"):
        sub = [r for r in amostra if r.get("faixa_porte_m2") == porte]
        por_porte[porte] = _agg(sub)

    metricas = _agg(amostra)

    return {
        "status": "ok" if amostra else "amostra_insuficiente",
        "cidade": cidade,
        "uf": uf,
        "fonte": "CNO — obras fitness encerradas (município)",
        "total_encerradas_filtradas": len(encerradas),
        "amostra_valida": len(amostra),
        "rejeitadas": rejeitadas,
        "metricas": metricas,
        "por_porte_m2": por_porte,
        "obras_referencia": sorted(amostra, key=lambda r: -r["area_m2"])[:15],
        "nota_metodologica": (
            "Fim da obra = data da situação cadastral (encerrada), não previsão de término. "
            "dias_por_m2 cruza início e fim para estimar duração em obras em andamento."
        ),
    }


def estimar_previsao_encerramento_obra(
    data_inicio: str,
    area_m2: float,
    benchmark: dict[str, Any],
    *,
    faixa_porte_m2: str | None = None,
) -> dict[str, Any] | None:
    """Previsão de encerramento = início + (dias_por_m2_mediana × m²). Projeção, não dado CNO."""
    if benchmark.get("status") not in ("ok",):
        return None
    di = _parse_date_br(data_inicio)
    if not di or area_m2 <= 0:
        return None

    porte = faixa_porte_m2 or _faixa_porte_m2(area_m2)
    por_porte = benchmark.get("por_porte_m2") or {}
    sub = por_porte.get(porte) or {}
    dias_por_m2 = sub.get("dias_por_m2_mediana")
    base = "por_porte_m2"
    if not dias_por_m2:
        metricas = benchmark.get("metricas") or {}
        dias_por_m2 = metricas.get("dias_por_m2_mediana")
        base = "metricas_gerais"
    if not dias_por_m2:
        return None

    dias_est = max(_DURACAO_MIN_DIAS, int(round(float(dias_por_m2) * area_m2)))
    prev = di + timedelta(days=dias_est)
    return {
        "tipo": "projecao_estimativa",
        "previsao_encerramento_estimada": prev.isoformat(),
        "duracao_obra_dias_estimada": dias_est,
        "dias_por_m2_benchmark": dias_por_m2,
        "benchmark_base": base,
        "faixa_porte_m2": porte,
    }


def _filtrar_obras_por_bairro(
    obras: list[dict],
    bairro_filtro: str | None,
) -> tuple[list[dict], dict[str, Any]]:
    meta: dict[str, Any] = {
        "bairro_filtro": (bairro_filtro or "").strip() or None,
        "bairro_filtro_chave": normalizar_bairro(bairro_filtro or "") or None,
    }
    if not meta["bairro_filtro"]:
        return obras, meta
    filtradas = [o for o in obras if bairro_em_alvo(o.get("bairro") or "", bairro_filtro)]  # pyright: ignore[reportArgumentType]
    meta["total_antes_filtro"] = len(obras)
    meta["total_apos_filtro_bairro"] = len(filtradas)
    return filtradas, meta


def slim_obras_para_relatorio(
    em_curso_block: dict[str, Any],
    *,
    benchmark_tempo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recorte leve para `output_consolidado` / frontend (sem projeção pesada)."""
    if not isinstance(em_curso_block, dict) or em_curso_block.get("status") != "ok":
        return em_curso_block if isinstance(em_curso_block, dict) else {"status": "indisponivel"}

    bench = benchmark_tempo or em_curso_block.get("benchmark_tempo_obra") or {}

    from datetime import date as _date
    _hoje = _date.today().isoformat()

    obras_ui = []
    obras_estale = 0
    for o in em_curso_block.get("obras") or []:
        prev = o.get("previsao_encerramento")
        if not prev and bench.get("status") == "ok":
            prev = estimar_previsao_encerramento_obra(
                o.get("data_inicio") or "",
                float(o.get("area_m2") or 0),
                bench,
                faixa_porte_m2=o.get("faixa_porte_m2"),
            )
        # CNO/RFB marca 'em_curso' por código de situação que o cartório raramente
        # atualiza — obra com previsão de encerramento já no passado é stale (acabou
        # ou parou), não é "concorrência futura em construção". Dropa do relatório.
        _prev_data = (prev or {}).get("previsao_encerramento_estimada")
        if _prev_data and str(_prev_data)[:10] < _hoje:
            obras_estale += 1
            continue
        obras_ui.append(
            {
                "nome_obra": o.get("nome_obra"),
                "area_m2": o.get("area_m2"),
                "bairro": o.get("bairro_label") or formatar_bairro_exibicao(o.get("bairro") or "")
                or None,
                "bairro_chave": o.get("bairro_chave"),
                "data_inicio": o.get("data_inicio") or None,
                "previsao_encerramento_estimada": (
                    (prev or {}).get("previsao_encerramento_estimada")
                ),
                "duracao_obra_dias_estimada": (prev or {}).get("duracao_obra_dias_estimada"),
                "logradouro": o.get("logradouro") or None,
                "numero": o.get("numero") or None,
                "situacao_obra": o.get("situacao_obra"),
                "cno": o.get("cno"),
            }
        )

    bench_slim = None
    if bench.get("status") == "ok":
        bench_slim = {
            "status": "ok",
            "amostra_valida": bench.get("amostra_valida"),
            "metricas": bench.get("metricas"),
            "por_porte_m2": bench.get("por_porte_m2"),
            "nota_metodologica": bench.get("nota_metodologica"),
        }

    return {
        "status": "ok",
        "fonte": em_curso_block.get("fonte"),
        "cidade": em_curso_block.get("cidade"),
        "uf": em_curso_block.get("uf"),
        "filtro": em_curso_block.get("filtro"),
        "total_obras_em_curso": em_curso_block.get("total_obras_em_curso"),
        "filtro_bairro": em_curso_block.get("filtro_bairro"),
        "obras": obras_ui,
        "obras_descartadas_encerramento_passado": obras_estale or None,
        "benchmark_tempo_obra": bench_slim,
        "nota_metodologica": em_curso_block.get("nota_metodologica"),
    }


def listar_obras_fitness_em_curso(
    *,
    cno_dir: str | Path,
    cidade: str = "Fortaleza",
    uf: str = "CE",
    municipio: str | None = None,
    limit: int = 30,
    obras_precarregadas: list[dict] | None = None,
    benchmark_tempo: dict[str, Any] | None = None,
    bairro_filtro: str | None = None,
) -> dict[str, Any]:
    """
    Obras fitness no município com situação em curso (ativa / execução / paralisada).

    Inclui projeção de matrículas e receita mensal estimada (benchmark A4).
    Com `bairro_filtro`, restringe às obras cujo bairro CNO coincide (chave normalizada).
    """
    cno_path = Path(cno_dir)
    if municipio is None:
        municipio = _resolve_municipio_codigo_cno(cidade, uf, cno_dir=cno_path)
    if municipio == MUNICIPIO_CNO_INDISPONIVEL and obras_precarregadas is None:
        return {
            "status": "indisponivel",
            "motivo": "municipio_sem_mapeamento_rfb",
            "cidade": cidade,
            "uf": uf,
            "total_obras_em_curso_municipio": 0,
            "total_obras_em_curso": 0,
            "obras": [],
        }
    if obras_precarregadas is not None:
        obras = [o for o in obras_precarregadas if o.get("situacao_obra") == "em_curso"]
    else:
        obras = _load_obras_fitness_municipio(
            cno_path, municipio, cidade, uf, somente_em_curso=True
        )
    bench = benchmark_tempo
    if bench is None:
        bench = calcular_benchmark_tempo_obra_cno(
            cno_dir=cno_path, municipio=municipio, cidade=cidade, uf=uf
        )

    if bench.get("status") == "ok":
        for o in obras:
            prev = estimar_previsao_encerramento_obra(
                o.get("data_inicio") or "",
                float(o.get("area_m2") or 0),
                bench,
                faixa_porte_m2=o.get("faixa_porte_m2"),
            )
            if prev:
                o["previsao_encerramento"] = prev

    total_municipio = len(obras)
    obras, filtro_meta = _filtrar_obras_por_bairro(obras, bairro_filtro)
    obras.sort(key=lambda o: -o["area_m2"])
    lista = obras[:limit]

    totais = {"obras": len(lista), "area_m2": 0.0, "receita_realista_soma": 0.0}
    for o in lista:
        totais["area_m2"] += o["area_m2"]
        proj = o.get("projecao_receita") or {}
        rec = (proj.get("receita_mensal_estimada") or {}).get("realista") or 0
        totais["receita_realista_soma"] += rec

    return {
        "status": "ok",
        "cidade": cidade,
        "uf": uf,
        "fonte": "CNO — Cadastro Nacional de Obras (RFB)",
        "filtro": "situacao em_curso (códigos 01–04)",
        "total_obras_em_curso_municipio": total_municipio,
        "total_obras_em_curso": len(obras),
        "filtro_bairro": filtro_meta,
        "obras": lista,
        "totais_amostra": {
            "obras_listadas": totais["obras"],
            "area_m2_soma": round(totais["area_m2"], 2),
            "receita_mensal_realista_soma_estimada": round(totais["receita_realista_soma"], 2),
        },
        "benchmark_tempo_obra": bench,
        "nota_metodologica": (
            "Receita = matrículas (m² × matr/m²) × ticket nominal × (1 − inadimplência). "
            "Previsão de encerramento = início + (dias/m² mediano de obras encerradas no CNO). "
            "Parâmetros de prospecção — não são dados fiscais."
        ),
    }


def cruzar_entrantes_obras_cno(
    *,
    cno_dir: str | Path,
    cidade: str = "Fortaleza",
    uf: str = "CE",
    bairro: str = "",
    dias: int = 90,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Cruzamento CNPJ fitness (entrantes 90d) -> CNO no município inteiro.

    Sempre percorre todos os entrantes do município e todo o CNO municipal
    (`_load_cno_obras_municipio`). O parâmetro `bairro` só recorta o resultado
    (não restringe a busca no CNO). Preferir `consultar_municipio_cnpj_cno`.
    """
    cno_path = Path(cno_dir)
    entrantes = listar_entrantes_cnpj_fitness(
        cidade, uf, dias, limit=limit, validar_places=False, enriquecer=False
    )
    if entrantes.get("status") != "ok":
        return entrantes

    municipio = _resolve_municipio_codigo_cno(cidade, uf, cno_dir=cno_path)
    cno_indisponivel = municipio == MUNICIPIO_CNO_INDISPONIVEL
    cnpj_idx = _cnpj_cnae_from_entrantes(entrantes)
    if cno_indisponivel:
        obras_municipio = []
        obras_ftz = []
    else:
        # obras_municipio = TODAS as obras (match endereço/CEP) — só extract local.
        # Em CNO_SOURCE=supabase PULA o parse do cno.csv (~800MB) — hog de latência
        # no A0; degrada p/ [] (tabela Supabase guarda só fitness, servidas em obras_ftz).
        obras_municipio = (
            [] if _cno_supabase_enabled()
            else _load_cno_obras_municipio(cno_path, municipio, area_min=50.0)
        )
        # obras_ftz = obras fitness — roteado pelo chokepoint (Supabase em prod).
        obras_ftz = _load_obras_fitness_municipio(
            cno_path, municipio, cidade, uf, cnpj_cnae_por_cnpj=cnpj_idx
        )

    cruzamentos: list[dict] = []
    stats: dict[str, int] = {
        "cnpj": 0,
        "endereco": 0,
        "nome_obra": 0,
        "cep8_baixa": 0,
        "sem_obra": 0,
        "com_area": 0,
    }

    for e in entrantes.get("entrantes") or []:
        match, metodo, confianca = _match_obra_cno_entrante(e, obras_municipio)

        if metodo == "cnpj_responsavel":
            stats["cnpj"] += 1
        elif metodo in ("endereco_cep_numero", "endereco_cep_logradouro"):
            stats["endereco"] += 1
        elif metodo == "nome_obra_cep8":
            stats["nome_obra"] += 1
        elif metodo == "cep8_multiplas_obras":
            stats["cep8_baixa"] += 1
        elif metodo is None:
            stats["sem_obra"] += 1

        area_m2 = None
        capacidade = None
        projecao = None
        fantasia = e.get("nome_fantasia") or ""
        if match and "area_m2" in match:
            area_m2 = match["area_m2"]
            faixa = match.get("faixa_ticket_inferida") or _inferir_faixa_ticket(
                match.get("nome_obra") or fantasia
            )
            capacidade = _capacidade_por_m2(area_m2, faixa)
            projecao = projecao_demanda_receita_obra(area_m2, faixa)
            stats["com_area"] += 1

        cruzamentos.append(
            {
                "cnpj": e.get("cnpj"),
                "nome_fantasia": fantasia or None,
                "razao_social": e.get("razao_social"),
                "segmento_operacao": e.get("segmento_operacao"),
                "data_abertura": e.get("data_abertura"),
                "cep": e.get("cep"),
                "endereco": e.get("endereco"),
                "bairro": e.get("bairro"),
                "cnae_principal": e.get("cnae_principal"),
                "match_cno": metodo,
                "match_confianca": confianca,
                "area_m2_obra": area_m2,
                "capacidade_matriculas_estimada": capacidade,
                "projecao_receita_estimada": projecao,
                "obra": match,
            }
        )

    bench_tempo = calcular_benchmark_tempo_obra_cno(
        cno_dir=cno_path, cidade=cidade, uf=uf
    )
    obras_fitness_ec_municipio = [
        o for o in obras_ftz if o.get("situacao_obra") == "em_curso"
    ]
    em_curso_municipio = listar_obras_fitness_em_curso(
        cno_dir=cno_path,
        cidade=cidade,
        uf=uf,
        limit=30,
        obras_precarregadas=obras_fitness_ec_municipio,
        benchmark_tempo=bench_tempo,
        bairro_filtro=None,
    )

    recorte_bairro: dict[str, Any] | None = None
    bairro_alvo = (bairro or "").strip()
    if bairro_alvo:
        cruz_bairro = [c for c in cruzamentos if bairro_em_alvo(c.get("bairro") or "", bairro_alvo)]
        obras_bairro, filtro_meta = _filtrar_obras_por_bairro(
            obras_fitness_ec_municipio, bairro_alvo
        )
        em_curso_bairro = listar_obras_fitness_em_curso(
            cno_dir=cno_path,
            cidade=cidade,
            uf=uf,
            limit=30,
            obras_precarregadas=obras_fitness_ec_municipio,
            benchmark_tempo=bench_tempo,
            bairro_filtro=bairro_alvo,
        )
        recorte_bairro = {
            "bairro": bairro_alvo,
            "filtro": filtro_meta,
            "total_entrantes": len(cruz_bairro),
            "cruzamentos": cruz_bairro,
            "cruzamentos_com_obra": [c for c in cruz_bairro if c.get("match_cno")],
            "obras_fitness_keyword_em_curso": em_curso_bairro,
            "obras_fitness_keyword_em_curso_lista": obras_bairro,
        }

    ref_obras = sorted(obras_ftz, key=lambda o: -o["area_m2"])[:12]
    com_match = [c for c in cruzamentos if c.get("match_cno")]

    return {
        "status": "ok",
        "cidade": cidade,
        "uf": uf,
        "dias": dias,
        "municipio_rfb": municipio,
        "obras_cno_status": "indisponivel" if cno_indisponivel else "ok",
        "fonte_entrantes": "cnpj_fitness_estabelecimentos (Supabase)",
        "fonte_obras": "CNO — Cadastro Nacional de Obras (RFB)",
        "total_entrantes_consultados": len(entrantes.get("entrantes") or []),
        "total_entrantes_cruzados": len(cruzamentos),
        "total_entrantes": len(cruzamentos),
        "obras_cno_municipio": len(obras_municipio),
        "obras_fitness_filtradas_municipio": len(obras_ftz),
        "obras_fitness_em_curso_municipio": em_curso_municipio,
        "obras_fitness_em_curso": em_curso_municipio,
        "obras_fitness_em_curso_lista_municipio": obras_fitness_ec_municipio,
        "recorte_bairro": recorte_bairro,
        "benchmark_tempo_obra_cno": bench_tempo,
        "obras_fitness_referencia": ref_obras,
        "resumo_match": stats,
        "cruzamentos": cruzamentos,
        "cruzamentos_com_obra": com_match,
        "nota_metodologica": (
            "Fluxo CNPJ->CNO: entrantes fitness 90d primeiro; busca em todo o CNO "
            "municipal (obra pode ter nome de SPE/construtora). Área m² só com match "
            "confiável. Matrículas/receita = projeção A4, não faturamento CNPJ."
        ),
    }


def resolve_cno_data_dir(explicit: str | Path | None = None) -> Path:
    """Resolve pasta do extract CNO (env → fallbacks)."""
    import os

    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    for key in ("CNO_DATA_DIR", "CNO_DATA_DIR_HOST"):
        val = (os.getenv(key) or "").strip()
        if val:
            candidates.append(Path(val))
    candidates.extend(
        [
            Path(r"C:\Users\marce\Downloads\cno_extract"),
            _ROOT / "data" / "cno",
        ]
    )
    seen: set[str] = set()
    for p in candidates:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        if (p / "cno.csv").is_file():
            return p
    tried = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"cno.csv não encontrado. Tentado: {tried}")


def consultar_municipio_cnpj_cno(
    *,
    cidade: str,
    uf: str,
    cno_dir: str | Path,
    dias: int = 90,
    limit: int = 200,
    bairro: str | None = None,
    bairros: list[str] | None = None,
) -> dict[str, Any]:
    """
    Pesquisa municipal CNPJ fitness (entrantes) -> CNO.

    Ordem obrigatória:
    1. Município: todos entrantes Supabase + match em todo CNO municipal
    2. Bairro(s): recorte dos cruzamentos e das obras fitness keyword (CNO)

    Nunca restringe a varredura CNO ao bairro — evita perder obras fora do polo.
    """
    cruz = cruzar_entrantes_obras_cno(
        cno_dir=cno_dir,
        cidade=cidade,
        uf=uf,
        bairro="",
        dias=dias,
        limit=limit,
    )
    if cruz.get("status") != "ok":
        return cruz

    todos: list[dict] = list(cruz.get("cruzamentos") or [])
    alvos: list[str] = []
    if bairros:
        alvos = [b.strip() for b in bairros if b and b.strip()]
    elif bairro and bairro.strip():
        alvos = [bairro.strip()]

    def _slice_bairro(items: list[dict], alvo: str) -> list[dict]:
        return [x for x in items if bairro_em_alvo(x.get("bairro") or "", alvo)]

    com_obra = [c for c in todos if c.get("match_cno")]
    obras_ec_mun: list[dict] = list(cruz.get("obras_fitness_em_curso_lista_municipio") or [])
    cno_kw_mun = cruz.get("obras_fitness_em_curso_municipio") or cruz.get("obras_fitness_em_curso")

    out: dict[str, Any] = {
        k: v
        for k, v in cruz.items()
        if k
        not in (
            "cruzamentos",
            "cruzamentos_com_obra",
            "total_entrantes",
            "obras_fitness_em_curso",
            "obras_fitness_em_curso_municipio",
            "obras_fitness_em_curso_lista_municipio",
            "recorte_bairro",
        )
    }
    out.update(
        {
            "fluxo": "municipio_cnpj_cno -> recorte_bairro_opcional",
            "escopo_primario": "municipio",
            "escopo": "municipio",
            "bairro_filtro": alvos[0] if len(alvos) == 1 else None,
            "bairros_filtro": alvos or None,
            "entrantes_municipio": {
                "total": len(todos),
                "com_match_cno": len(com_obra),
                "sem_match_cno": len(todos) - len(com_obra),
            },
            "cruzamentos_municipio": todos,
            "cruzamentos_com_obra_municipio": com_obra,
            "cno_fitness_keyword_municipio": {
                "total_em_curso": (cno_kw_mun or {}).get("total_obras_em_curso_municipio"),
                "total_em_curso_listadas": (cno_kw_mun or {}).get("total_obras_em_curso"),
                "obras": (cno_kw_mun or {}).get("obras") or [],
                "nota": "Filtro keyword CNO no município; complementa cruzamento CNPJ->CNO",
            },
        }
    )

    def _bloco_bairro(alvo: str, filtrados: list[dict]) -> dict[str, Any]:
        com = [c for c in filtrados if c.get("match_cno")]
        obras_bairro, filtro_meta = _filtrar_obras_por_bairro(obras_ec_mun, alvo)
        return {
            "total_entrantes": len(filtrados),
            "com_match_cno": len(com),
            "sem_match_cno": len(filtrados) - len(com),
            "cruzamentos": filtrados,
            "cruzamentos_com_obra": com,
            "filtro_bairro": filtro_meta,
            "cno_fitness_keyword_em_curso": {
                "total_em_curso_bairro": len(obras_bairro),
                "obras": obras_bairro[:30],
                "nota": "Recorte municipal; obras fora do bairro permanecem em cno_fitness_keyword_municipio",
            },
        }

    if alvos:
        out["escopo"] = "bairros" if len(alvos) > 1 else "bairro"
        out["escopo_secundario"] = out["escopo"]
        por_bairro: dict[str, Any] = {}
        for alvo in alvos:
            filtrados = _slice_bairro(todos, alvo)
            por_bairro[alvo] = _bloco_bairro(alvo, filtrados)
        out["por_bairro"] = por_bairro
        if len(alvos) == 1:
            out["cruzamentos"] = por_bairro[alvos[0]]["cruzamentos"]
            out["cruzamentos_com_obra"] = por_bairro[alvos[0]]["cruzamentos_com_obra"]
        else:
            out["cruzamentos"] = todos
            out["cruzamentos_com_obra"] = com_obra
    else:
        out["cruzamentos"] = todos
        out["cruzamentos_com_obra"] = com_obra

    out["total_entrantes"] = len(out["cruzamentos"])
    return out


# ── Agregação CNO por bairro (bairros alternativos / polo) ─────────────────

_AREA_MIN_EDIFICACAO = param("cno_area_edificacao_min")
_AREA_MAX_EDIFICACAO = param("cno_area_edificacao_max")


def _load_cno_areas_index(cno_dir: Path) -> dict[str, list[dict]]:
    """Índice CNO → linhas de cno_areas.csv (destinação / tipo obra)."""
    areas_path = cno_dir / "cno_areas.csv"
    by_cno: dict[str, list[dict]] = {}
    if not areas_path.is_file():
        return by_cno
    with open(areas_path, encoding="latin-1", errors="replace") as f:
        for row in csv.DictReader(f):
            cno_id = (row.get("CNO") or "").strip()
            if not cno_id:
                continue
            by_cno.setdefault(cno_id, []).append(
                {
                    "destinacao": (row.get("Destinação") or row.get("Destinacao") or "").strip(),
                    "categoria": (row.get("Categoria") or "").strip(),
                    "tipo_obra": (row.get("Tipo de obra") or "").strip(),
                }
            )
    return by_cno


def _classificar_tipo_edificacao_cno(nome: str, areas: list[dict]) -> str:
    """
    Classifica obra em curso para agregação por bairro.

    Retorna: fitness | comercial | residencial | misto | outros
    """
    nome_l = (nome or "").lower()
    if _match_keywords_fitness(nome) and not _match_exclusao(nome):
        return "fitness"

    destinos = " ".join(
        (a.get("destinacao") or "").lower() for a in (areas or [])
    )
    texto = f"{destinos} {nome_l}"

    if "misto" in texto:
        return "misto"
    if "comerc" in texto or "galpao" in texto or "loja" in texto or "sala comercial" in texto:
        return "comercial"
    if "resid" in texto or "habitacional" in texto or "apartamento" in texto:
        return "residencial"
    if "industr" in texto:
        return "outros"
    return "outros"


def carregar_contagem_obras_em_curso_por_bairro(
    *,
    cno_dir: str | Path,
    cidade: str,
    uf: str = "CE",
    municipio: str | None = None,
) -> dict[str, Any]:
    """
    Conta obras **em curso** no município agrupadas por bairro (chave normalizada).

    Usa cno.csv + cno_areas.csv (destinação comercial/residencial).
    Independente do filtro fitness — inclui edificações comerciais e residenciais.
    """
    cno_path = Path(cno_dir)
    main = cno_path / "cno.csv"
    if not main.is_file():
        return {"status": "nao_configurado", "motivo": "cno.csv ausente", "por_bairro": {}}

    mun = municipio or _resolve_municipio_codigo_cno(cidade, uf, cno_dir=cno_path)
    if mun == MUNICIPIO_CNO_INDISPONIVEL:
        return {
            "status": "sem_mapeamento",
            "motivo": "municipio_sem_mapeamento_rfb",
            "cidade": cidade,
            "uf": uf,
            "por_bairro": {},
        }
    areas_idx = _load_cno_areas_index(cno_path)
    por_bairro: dict[str, dict[str, int]] = {}

    with open(main, encoding="latin-1", errors="replace") as f:
        reader = csv.DictReader(f)
        hdr = _map_headers(reader.fieldnames or [])  # pyright: ignore[reportArgumentType]
        for row in reader:
            if _val(row, hdr, "municipio") != mun:
                continue
            situacao = _situacao_label(_val(row, hdr, "situacao").zfill(2))
            if situacao != "em_curso":
                continue
            area = _float(_val(row, hdr, "area"))
            if area < _AREA_MIN_EDIFICACAO or area > _AREA_MAX_EDIFICACAO:
                continue

            cno_id = _val(row, hdr, "cno")
            nome = _val(row, hdr, "nome")
            bairro_raw = _val(row, hdr, "bairro")
            bairro_chave = normalizar_bairro(bairro_raw)
            if not bairro_chave:
                continue

            tipo = _classificar_tipo_edificacao_cno(nome, areas_idx.get(cno_id, []))
            bucket = por_bairro.setdefault(
                bairro_chave,
                {
                    "total": 0,
                    "comercial": 0,
                    "residencial": 0,
                    "fitness": 0,
                    "misto": 0,
                    "outros": 0,
                    "bairro_label": formatar_bairro_exibicao(bairro_raw),  # pyright: ignore[reportArgumentType]
                },
            )
            bucket["total"] += 1
            bucket[tipo] = bucket.get(tipo, 0) + 1

    return {
        "status": "ok",
        "cidade": cidade,
        "uf": uf,
        "municipio_codigo": mun,
        "fonte": "CNO — obras em curso (situação 01–04)",
        "por_bairro": por_bairro,
        "total_obras_municipio": sum(b.get("total", 0) for b in por_bairro.values()),
    }


def cno_snapshot_para_bairro_alternativo(
    partes_chave: list[str],
    indice_por_bairro: dict[str, dict],
) -> dict[str, Any]:
    """
    Soma contagens CNO para um bairro alternativo (simples ou composto).

    `partes_chave`: chaves normalizadas (ex.: maraponga, montese).
    """
    partes = [p for p in partes_chave if p]
    if not partes or not indice_por_bairro:
        return {
            "disponivel": False,
            "comercial_em_curso": 0,
            "residencial_em_curso": 0,
            "fitness_em_curso": 0,
            "misto_em_curso": 0,
            "outros_em_curso": 0,
            "total_em_curso": 0,
        }

    acc = {
        "comercial": 0,
        "residencial": 0,
        "fitness": 0,
        "misto": 0,
        "outros": 0,
        "total": 0,
    }
    matched_keys: list[str] = []

    for bairro_chave, counts in indice_por_bairro.items():
        if not bairro_chave:
            continue
        bate = bairro_chave in partes
        if not bate:
            for p in partes:
                if len(p) >= 4 and (p in bairro_chave or bairro_chave in p):
                    bate = True
                    break
        if not bate:
            continue
        matched_keys.append(bairro_chave)
        for k in ("comercial", "residencial", "fitness", "misto", "outros", "total"):
            acc[k] += int(counts.get(k, 0) or 0)

    return {
        "disponivel": True,
        "comercial_em_curso": acc["comercial"],
        "residencial_em_curso": acc["residencial"],
        "fitness_em_curso": acc["fitness"],
        "misto_em_curso": acc["misto"],
        "outros_em_curso": acc["outros"],
        "total_em_curso": acc["total"],
        "bairros_cno_matched": matched_keys[:5],
        "fonte": "CNO RFB — situação em curso",
    }
