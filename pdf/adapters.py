"""
Adapta o payload flat do GET /api/relatorios/{id} para RelatorioPdfModel.

Espelha a lógica de `adaptBackendToDetail` no frontend, sem depender de React.
"""

from __future__ import annotations

import re
from typing import Any

from pdf.models import (
    BairroAltPdf,
    CandidatoPdf,
    CenarioPdf,
    CompetidorPdf,
    MarketContextPdf,
    RelatorioPdfModel,
    ScoreDim,
)
from pdf.theme import MODELO_LABEL

_NUM_RE = re.compile(r"[^\d.,\-]")


def _num(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if v == v else None  # NaN guard
    s = str(v).strip()
    if not s:
        return None
    s = _NUM_RE.sub("", s).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _int(v: Any) -> int | None:
    n = _num(v)
    if n is None:
        return None
    return int(round(n))


def extract_resumo_from_markdown(markdown: str | None) -> str | None:
    if not markdown or not str(markdown).strip():
        return None
    m = re.search(
        r"##\s*🎯\s*Resumo Executivo\s*\n([\s\S]*?)\n---",
        str(markdown),
        re.IGNORECASE,
    )
    text = (m.group(1) if m else "").strip()
    return text or None


def _map_cenario_row(row: dict[str, Any]) -> CenarioPdf:
    modelo = str(row.get("modelo") or "")
    obra = _num(row.get("capex_obra_adaptacao")) or 0.0
    projeto = _num(row.get("capex_projeto_arquitetonico")) or 0.0
    alvara = _num(row.get("capex_alvara_e_taxas")) or 0.0
    return CenarioPdf(
        modelo=modelo,
        label=MODELO_LABEL.get(modelo, modelo),
        ticket_medio=_num(row.get("ticket_medio")),
        receita_mensal=_num(row.get("receita_mensal")),
        lucro_mensal=_num(row.get("lucro_mensal_estimado")),
        margem_pct=_num(row.get("margem_percentual")),
        payback_meses=_int(row.get("payback_meses")),
        investimento_total=_num(row.get("investimento_total")),
        capex_total=_num(row.get("capex_total")),
        capex_obra=obra + projeto + alvara,
        capex_equipamentos=_num(row.get("capex_equipamentos")),
        capex_contingencia=_num(row.get("capex_contingencia_valor")),
        viabilidade=str(row.get("viabilidade") or "") or None,
        matriculas_realista=_int(row.get("matriculas_realista") or row.get("alunos_projetados")),
    )


def _map_candidato(row: dict[str, Any], pos: int) -> CandidatoPdf:
    polos = row.get("polos_geradores")
    if isinstance(polos, list):
        polos_txt = "; ".join(str(p) for p in polos[:3])
    else:
        polos_txt = ""
    motivo = str(row.get("motivo") or "")
    if polos_txt:
        motivo = f"{motivo} · Polos: {polos_txt}" if motivo else f"Polos: {polos_txt}"
    return CandidatoPdf(
        posicao=pos,
        nome=str(row.get("nome") or "—"),
        endereco=str(row.get("endereco") or "—"),
        area_m2=_num(row.get("area_estimada_m2")),
        score_geoscout=_num(row.get("score_geoscout")),
        score_ancoragem=_num(row.get("score_ancoragem")),
        motivo=motivo[:500],
    )


def _map_competidor(row: dict[str, Any]) -> CompetidorPdf:
    rating = _num(row.get("rating_oficial") or row.get("rating_geral"))
    return CompetidorPdf(
        nome=str(row.get("nome") or "—"),
        rating=rating,
        num_avaliacoes=_int(row.get("num_avaliacoes")),
        bairro=str(row.get("bairro_concorrente") or "") or None,
        tem_24h=bool(row.get("tem_24h")) if row.get("tem_24h") is not None else None,
    )


def _map_market(mc: dict[str, Any] | None) -> MarketContextPdf | None:
    if not mc:
        return None
    redes = mc.get("principais_redes_concorrentes")
    insights = mc.get("insights_estrategicos")
    return MarketContextPdf(
        ticket_mercado=str(mc.get("ticket_medio_mercado") or "") or None,
        aluguel_m2=str(mc.get("aluguel_medio_m2") or "") or None,
        renda=str(mc.get("renda_media_bairro") or "") or None,
        tendencia=str(mc.get("tendencia_mercado") or "") or None,
        redes=[str(r) for r in redes] if isinstance(redes, list) else [],
        insights=[str(i) for i in insights[:5]] if isinstance(insights, list) else [],
        parque_ativo=_int(
            mc.get("parque_ativo_total") or mc.get("academias_ativas_cidade_cnpj"),
        ),
        novos_cnpj_90d=_int(mc.get("novos_cnpj_fitness_90d")),
    )


def relatorio_from_api_payload(payload: dict[str, Any]) -> RelatorioPdfModel:
    """Converte resposta de GET /api/relatorios/{id} em modelo PDF."""
    header = payload.get("header") or {}
    inp = payload.get("input_canonico") or {}
    out = payload.get("output_consolidado") or {}
    candidatos_raw = payload.get("candidatos") or []
    competidores_raw = payload.get("competidores") or []
    cenarios_raw = payload.get("cenarios") or []
    bairros_raw = payload.get("bairros_alternativos") or []

    scores = [
        ScoreDim("Demográfico", _num(out.get("score_demografico"))),
        ScoreDim("Competitivo", _num(out.get("score_concorrencia"))),
        ScoreDim("Viabilidade", _num(out.get("score_viabilidade"))),
    ]

    resumo = out.get("resumo_executivo")
    if not resumo:
        resumo = extract_resumo_from_markdown(header.get("markdown_completo"))

    mc_raw = out.get("market_context")
    if isinstance(mc_raw, str):
        import json

        try:
            mc_raw = json.loads(mc_raw)
        except json.JSONDecodeError:
            mc_raw = None

    entrantes = out.get("entrantes_cnpj_90d")
    entrantes_total = None
    if isinstance(entrantes, dict):
        entrantes_total = _int(entrantes.get("total"))

    contato = out.get("contato_decisor")
    script = None
    if isinstance(contato, dict):
        script = str(contato.get("script_abordagem") or "") or None

    alertas = out.get("alertas") or out.get("alertas_financeiros") or []
    if not isinstance(alertas, list):
        alertas = []

    cenarios = [_map_cenario_row(c) for c in cenarios_raw if isinstance(c, dict)]
    order = {"low": 0, "mid": 1, "premium": 2}
    cenarios.sort(key=lambda c: order.get(c.modelo, 9))

    candidatos = [
        _map_candidato(c, i + 1)
        for i, c in enumerate(candidatos_raw[:3])
        if isinstance(c, dict)
    ]

    competidores = [
        _map_competidor(c) for c in competidores_raw[:12] if isinstance(c, dict)
    ]

    bairros = []
    for b in bairros_raw:
        if not isinstance(b, dict):
            continue
        bairros.append(
            BairroAltPdf(
                bairro=str(b.get("bairro") or ""),
                motivo=str(b.get("motivo") or "")[:300],
                concorrentes=_int(b.get("concorrentes_no_bairro")),
                prioridade=str(b.get("prioridade") or b.get("prioridade_ajustada") or "") or None,
            ),
        )

    data_exec = (
        str(header.get("data_execucao") or header.get("created_at") or "")[:10]
    )

    return RelatorioPdfModel(
        relatorio_id=str(payload.get("id") or ""),
        data_execucao=data_exec,
        cidade=str(inp.get("cidade") or out.get("cidade") or "—"),
        bairro=str(inp.get("bairro") or out.get("bairro") or "—"),
        uf=str(inp.get("uf") or "")[:2] or None,
        tipo_negocio=str(inp.get("tipo_negocio") or "academia"),
        area_m2_min=_int(inp.get("area_m2_min")) or 0,
        area_m2_max=_int(inp.get("area_m2_max")) or 0,
        publico_alvo=str(inp.get("publico_alvo") or "") or None,
        veredito=str(out.get("veredito") or "") or None,
        score_bairro=_num(out.get("score_bairro")),
        score_top1=_num(out.get("score_top1_candidato")),
        scores=scores,
        nivel_saturacao=str(out.get("nivel_saturacao") or "") or None,
        total_concorrentes=_int(out.get("total_concorrentes_analisados")),
        total_raio=_int(out.get("total_encontrados_raio")),
        resumo_executivo=str(resumo) if resumo else None,
        posicionamento=str(out.get("posicionamento_recomendado") or "") or None,
        market=_map_market(mc_raw if isinstance(mc_raw, dict) else None),
        candidatos=candidatos,
        cenarios=cenarios,
        modelo_recomendado=str(out.get("modelo_recomendado") or "") or None,
        aluguel_mensal=_num(out.get("aluguel_mensal")),
        aluguel_mediana_m2=_num(out.get("aluguel_mediana_m2")),
        competidores=competidores,
        bairros_alternativos=bairros,
        alertas=[str(a) for a in alertas if a],
        entrantes_cnpj_total=entrantes_total,
        script_abordagem=script,
        metadata={
            "schema_version": header.get("schema_version"),
            "status": header.get("status"),
        },
    )


def relatorio_from_nested_json(data: dict[str, Any]) -> RelatorioPdfModel:
    """Aceita JSON canônico aninhado (mocks / export A6)."""
    fake = {
        "id": data.get("id"),
        "header": {
            "data_execucao": data.get("data_execucao"),
            "markdown_completo": None,
        },
        "input_canonico": data.get("input_canonico"),
        "output_consolidado": _flatten_output(data.get("output_consolidado") or {}),
        "candidatos": (data.get("output_consolidado") or {}).get("top_3_candidatos") or [],
        "competidores": (data.get("output_consolidado") or {}).get("competitors_set") or [],
        "cenarios": _nested_cenarios_to_rows(
            (data.get("output_consolidado") or {}).get("viabilidade_3_cenarios"),
        ),
        "bairros_alternativos": (data.get("output_consolidado") or {}).get(
            "bairros_alternativos",
        )
        or [],
    }
    return relatorio_from_api_payload(fake)


def _flatten_output(out: dict[str, Any]) -> dict[str, Any]:
    scores = out.get("scores_regionais") or {}
    flat = dict(out)
    if isinstance(scores, dict):
        flat.setdefault("score_demografico", scores.get("demografico"))
        flat.setdefault("score_concorrencia", scores.get("competitivo") or scores.get("concorrencia"))
        flat.setdefault("score_viabilidade", scores.get("viabilidade"))
    flat.setdefault("aluguel_mediana_m2", out.get("aluguel_mediana_m2_observado"))
    return flat


def _nested_cenarios_to_rows(
    cenarios: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(cenarios, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in ("low", "mid", "premium"):
        c = cenarios.get(key)
        if not isinstance(c, dict):
            continue
        capex = c.get("capex_detalhado") or {}
        row = {
            "modelo": key,
            "ticket_medio": c.get("ticket_medio"),
            "receita_mensal": c.get("receita_mensal"),
            "lucro_mensal_estimado": c.get("lucro_mensal_estimado"),
            "margem_percentual": c.get("margem_percentual"),
            "payback_meses": c.get("payback_meses"),
            "investimento_total": c.get("investimento_total"),
            "capex_total": c.get("capex_total") or capex.get("total"),
            "capex_equipamentos": capex.get("equipamentos"),
            "capex_obra_adaptacao": capex.get("obra_adaptacao"),
            "capex_projeto_arquitetonico": capex.get("projeto_arquitetonico"),
            "capex_alvara_e_taxas": capex.get("alvara_e_taxas"),
            "capex_contingencia_valor": capex.get("contingencia_valor"),
            "viabilidade": c.get("viabilidade"),
            "matriculas_realista": (c.get("matriculas") or {}).get("realista", {}).get("valor")
            if isinstance(c.get("matriculas"), dict)
            else c.get("alunos_projetados"),
            "alunos_projetados": c.get("alunos_projetados"),
        }
        rows.append(row)
    return rows
