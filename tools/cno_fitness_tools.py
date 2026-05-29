"""
Cruzamento CNO (Cadastro Nacional de Obras) x entrantes CNPJ fitness.

Área (m²) vem do CNO quando há match confiável — alimenta benchmark m²/aluno do A4.
Sem match: não estimar área (sem inventar).
"""
from __future__ import annotations

import csv
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

# Faixa plausível para unidade fitness comercial (obra)
_AREA_MIN_M2 = 80.0
_AREA_MAX_M2 = 8_000.0

# Duração obra (encerradas): filtros de plausibilidade
_DURACAO_MIN_DIAS = 60
_DURACAO_MAX_DIAS = 1_200
_DIAS_POR_M2_MIN = 0.04
_DIAS_POR_M2_MAX = 4.0

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
)


def _resolve_municipio_codigo_cno(cidade: str, uf: str = "CE") -> str:
    """Código município na tabela RFB/CNO (ex.: Fortaleza = 1389)."""
    try:
        from tools.ibge_tools import buscar_municipio
        from tools.rfb_cnpj_fitness_loader import IBGE_TO_RFB_MUNICIPIO

        mun = buscar_municipio(cidade, uf)
        if mun and mun.get("codigo"):
            mapped = IBGE_TO_RFB_MUNICIPIO.get(str(mun["codigo"]))
            if mapped:
                return mapped
    except Exception:
        pass
    return "1389"


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


def _nome_score(obra_nome: str, fantasia: str) -> int:
    o = (obra_nome or "").lower()
    f = (fantasia or "").lower()
    if not f or not o:
        return 0
    tokens = [t for t in re.split(r"\W+", f) if len(t) >= 4]
    return sum(1 for t in tokens if t in o)


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
) -> list[dict]:
    main = cno_dir / "cno.csv"
    if not main.is_file():
        return []

    obras: list[dict] = []
    with open(main, encoding="latin-1", errors="replace") as f:
        reader = csv.DictReader(f)
        hdr = _map_headers(reader.fieldnames or [])
        for row in reader:
            if _val(row, hdr, "municipio") != municipio:
                continue
            area = _float(_val(row, hdr, "area"))
            if area < _AREA_MIN_M2 or area > _AREA_MAX_M2:
                continue
            nome = _val(row, hdr, "nome")
            nome_u = nome.upper()
            if not any(k.upper() in nome_u for k in _KEYWORDS_OBRA_FITNESS):
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
                    "cno": _val(row, hdr, "cno"),
                    "cnpj_responsavel": _digits(_val(row, hdr, "cnpj")),
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
                    "capacidade_matriculas_estimada": _capacidade_por_m2(area, faixa),
                    "projecao_receita": proj if proj and proj.get("status") == "ok" else None,
                }
            )
    return obras


def calcular_benchmark_tempo_obra_cno(
    *,
    cno_dir: str | Path,
    municipio: str | None = None,
    cidade: str = "Fortaleza",
    uf: str = "CE",
) -> dict[str, Any]:
    if municipio is None:
        municipio = _resolve_municipio_codigo_cno(cidade, uf)
    """
    Benchmark de tempo de obra a partir de registros **encerrados** no CNO.

    - Início: Data de início da obra
    - Fim: Data da situação quando situação = encerrada (cadastral RFB, não previsão)

    Normaliza por m²: dias_por_m2 = (fim − início) / area_m2
    """
    cno_path = Path(cno_dir)
    encerradas = _load_fortaleza_cno(
        cno_path,
        municipio,
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
    filtradas = [o for o in obras if bairro_em_alvo(o.get("bairro") or "", bairro_filtro)]
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

    obras_ui = []
    for o in em_curso_block.get("obras") or []:
        prev = o.get("previsao_encerramento")
        if not prev and bench.get("status") == "ok":
            prev = estimar_previsao_encerramento_obra(
                o.get("data_inicio") or "",
                float(o.get("area_m2") or 0),
                bench,
                faixa_porte_m2=o.get("faixa_porte_m2"),
            )
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
    if municipio is None:
        municipio = _resolve_municipio_codigo_cno(cidade, uf)
    """
    Obras fitness no município com situação em curso (ativa / execução / paralisada).

    Inclui projeção de matrículas e receita mensal estimada (benchmark A4).
    Com `bairro_filtro`, restringe às obras cujo bairro CNO coincide (chave normalizada).
    """
    cno_path = Path(cno_dir)
    if obras_precarregadas is not None:
        obras = [o for o in obras_precarregadas if o.get("situacao_obra") == "em_curso"]
    else:
        obras = _load_fortaleza_cno(cno_path, municipio, somente_em_curso=True)
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
  Cruzamento por amostragem (máx. `limit` entrantes).

    Níveis de match:
    - `cnpj_responsavel`: CNPJ da obra = CNPJ do estabelecimento (raro)
    - `nome_obra`: tokens do nome fantasia na descrição da obra + mesmo CEP-8
    - `cep8_proximo`: mesmo CEP-8 + área plausível (confiança baixa)

    Retorna apenas fatos; sem narrativa interpretativa.
    """
    cno_path = Path(cno_dir)
    entrantes = listar_entrantes_cnpj_fitness(cidade, uf, dias, limit=limit)
    if entrantes.get("status") != "ok":
        return entrantes

    municipio = _resolve_municipio_codigo_cno(cidade, uf)
    obras_ftz = _load_fortaleza_cno(cno_path, municipio)
    by_cnpj = {o["cnpj_responsavel"]: o for o in obras_ftz if len(o["cnpj_responsavel"]) == 14}

    cruzamentos: list[dict] = []
    stats = {"cnpj": 0, "nome_obra": 0, "cep8_baixa": 0, "sem_obra": 0, "com_area": 0}

    for e in entrantes.get("entrantes") or []:
        cnpj = _digits(e.get("cnpj", ""))
        cep8 = _digits(e.get("cep", ""))[:8]
        fantasia = e.get("nome_fantasia") or ""

        match: dict | None = None
        metodo = None
        confianca = None

        if cnpj and cnpj in by_cnpj:
            match = by_cnpj[cnpj]
            metodo = "cnpj_responsavel"
            confianca = "alta"
            stats["cnpj"] += 1
        else:
            candidatos = [
                o
                for o in obras_ftz
                if cep8 and o.get("cep", "").startswith(cep8[:8])
            ]
            scored = sorted(
                ((o, _nome_score(o["nome_obra"], fantasia)) for o in candidatos),
                key=lambda x: (-x[1], x[0]["area_m2"]),
            )
            if scored and scored[0][1] >= 1:
                match = scored[0][0]
                metodo = "nome_obra_cep8"
                confianca = "media"
                stats["nome_obra"] += 1
            elif candidatos:
                # mesmo CEP mas sem nome — só reportar faixa, confiança baixa
                areas = [o["area_m2"] for o in candidatos]
                match = {
                    "area_m2_min": min(areas),
                    "area_m2_max": max(areas),
                    "obras_no_cep": len(candidatos),
                    "nota": "várias obras no CEP; sem match por nome",
                }
                metodo = "cep8_multiplas_obras"
                confianca = "baixa"
                stats["cep8_baixa"] += 1
            else:
                stats["sem_obra"] += 1

        area_m2 = None
        capacidade = None
        projecao = None
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
                "segmento_operacao": e.get("segmento_operacao"),
                "data_abertura": e.get("data_abertura"),
                "cep": e.get("cep"),
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
    em_curso = listar_obras_fitness_em_curso(
        cno_dir=cno_path,
        cidade=cidade,
        uf=uf,
        limit=20,
        obras_precarregadas=obras_ftz,
        benchmark_tempo=bench_tempo,
        bairro_filtro=bairro or None,
    )

    # Obras fitness no município (referência — não implica vínculo com cada entrant)
    ref_obras = sorted(obras_ftz, key=lambda o: -o["area_m2"])[:12]

    return {
        "status": "ok",
        "cidade": cidade,
        "uf": uf,
        "fonte_obras": "CNO — Cadastro Nacional de Obras (RFB)",
        "obras_fitness_filtradas_municipio": len(obras_ftz),
        "obras_fitness_em_curso": em_curso,
        "benchmark_tempo_obra_cno": bench_tempo,
        "obras_fitness_referencia": ref_obras,
        "total_entrantes": len(cruzamentos),
        "resumo_match": stats,
        "cruzamentos": cruzamentos,
        "nota_metodologica": (
            "Área m² só quando match CNO confiável. Matrículas e receita mensal "
            "são projeções (A4): m² × matr/m² × ticket × (1 − inadimplência). "
            "CNPJ/CNO não trazem faturamento declarado."
        ),
    }


# ── Agregação CNO por bairro (bairros alternativos / polo) ─────────────────

_AREA_MIN_EDIFICACAO = 80.0
_AREA_MAX_EDIFICACAO = 50_000.0


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
    nome_u = (nome or "").upper()
    if any(k.upper() in nome_u for k in _KEYWORDS_OBRA_FITNESS):
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

    mun = municipio or _resolve_municipio_codigo_cno(cidade, uf)
    areas_idx = _load_cno_areas_index(cno_path)
    por_bairro: dict[str, dict[str, int]] = {}

    with open(main, encoding="latin-1", errors="replace") as f:
        reader = csv.DictReader(f)
        hdr = _map_headers(reader.fieldnames or [])
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
                    "bairro_label": formatar_bairro_exibicao(bairro_raw),
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
