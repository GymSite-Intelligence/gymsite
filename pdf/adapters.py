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


def _faixa_horas(horas: list[int]) -> str:
    """['17','18','19'] contíguas → '17h–19h'; senão lista as horas."""
    if not horas:
        return "—"
    hs = sorted(horas)
    if hs[-1] - hs[0] == len(hs) - 1:
        return f"{hs[0]:02d}h–{hs[-1]:02d}h"
    return ", ".join(f"{h:02d}h" for h in hs)


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
        justificativa=str(row.get("justificativa") or "") or None,
        matriculas_realista=_int(row.get("matriculas_realista") or row.get("alunos_projetados")),
        # V3 (A4) — tributos & ocupação; frações ficam como float cru (formatadas no builder).
        tributos_mensal=_num(row.get("tributos_mensal")),
        aliquota_tributos=_num(row.get("aliquota_tributos")),
        anexo_simples=str(row.get("anexo_simples")) if row.get("anexo_simples") is not None else None,
        fator_r=_num(row.get("fator_r")),
        folha_pct_efetivo=_num(row.get("folha_pct_efetivo")),
        ocupacao_pct=_num(row.get("ocupacao_pct")),
        teto_ocupacao=_num(row.get("teto_ocupacao")),
        ticket_piso_ocupacao=_num(row.get("ticket_piso_ocupacao")),
        ocupacao_estoura=(bool(row.get("ocupacao_estoura")) if row.get("ocupacao_estoura") is not None else None),
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
        tipo_imovel_codigo_onr=_int(row.get("tipo_imovel_codigo_onr")),
        tipo_imovel_label=str(row.get("tipo_imovel_label")) if row.get("tipo_imovel_label") is not None else None,
        modalidade=str(row.get("modalidade")) if row.get("modalidade") is not None else None,
        cartorio=row.get("cartorio") if isinstance(row.get("cartorio"), dict) else None,
        # R1 — Street View: coordenadas + URL relativa do proxy (ja vem do pipeline)
        lat=_num(row.get("lat")),
        lng=_num(row.get("lng")),
        street_view_url=str(row.get("street_view_url")) if row.get("street_view_url") is not None else None,
    )


def _map_competidor(row: dict[str, Any]) -> CompetidorPdf:
    rating = _num(row.get("rating_oficial") or row.get("rating_geral"))
    om = row.get("oferta_mapeada") if isinstance(row.get("oferta_mapeada"), dict) else {}
    return CompetidorPdf(
        nome=str(row.get("nome") or "—"),
        rating=rating,
        num_avaliacoes=_int(row.get("num_avaliacoes")),
        bairro=str(row.get("bairro_concorrente") or "") or None,
        tem_24h=bool(row.get("tem_24h")) if row.get("tem_24h") is not None else None,
        planos_precos=row.get("planos_precos") if isinstance(row.get("planos_precos"), list) else None,
        tier_agregador=om.get("tier_agregador") if isinstance(om.get("tier_agregador"), dict) else None,
        rating_agregador=om.get("rating_agregador") if isinstance(om.get("rating_agregador"), dict) else None,
        oferta_modalidades=om.get("modalidades") if isinstance(om.get("modalidades"), list) else None,
        oferta_comodidades=om.get("comodidades") if isinstance(om.get("comodidades"), list) else None,
        oferta_fontes=om.get("fontes") if isinstance(om.get("fontes"), list) else None,
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
    entrantes_bairro = None
    entrantes_bairro_nome = None
    if isinstance(entrantes, dict):
        entrantes_total = _int(entrantes.get("total"))
        if entrantes.get("total_bairro") is not None:
            entrantes_bairro = _int(entrantes.get("total_bairro"))
        entrantes_bairro_nome = str(entrantes.get("bairro_alvo") or "") or None

    contato = out.get("contato_decisor")
    script = None
    if isinstance(contato, dict):
        script = str(contato.get("script_abordagem") or "") or None

    alertas = out.get("alertas") or out.get("alertas_financeiros") or []
    if not isinstance(alertas, list):
        alertas = []

    # Janela de demanda agregada — curva típica de lotação dos concorrentes por hora.
    # Shape competidor.horarios_pico = {dia: {"HH": ocupacao_pct}}.
    # 3 correções (antes somava cru tudo num balde → enviesado):
    #   1. DIAS ÚTEIS só (seg-sex) — fim de semana (pico tarde) borra o bimodal da semana
    #   2. NORMALIZA por concorrente (0-100 pelo pico dele) — Smart Fit grande não domina
    #   3. MÉDIA entre concorrentes (não soma) + N mínimo com dados — 1 ficha não enverga
    _DIAS_UTEIS = {"segunda", "terca", "quarta", "quinta", "sexta"}
    _por_hora_norm: dict[int, list[float]] = {}
    _n_com_dados = 0
    for c in competidores_raw:
        if not isinstance(c, dict):
            continue
        hp = c.get("horarios_pico")
        if not isinstance(hp, dict):
            continue
        # média por hora deste concorrente nos dias úteis
        medias_c: dict[int, float] = {}
        acc_c: dict[int, list[float]] = {}
        for _dia, horas in hp.items():
            if _dia not in _DIAS_UTEIS or not isinstance(horas, dict):
                continue
            for hh, val in horas.items():
                try:
                    acc_c.setdefault(int(hh), []).append(float(val))
                except (TypeError, ValueError):
                    continue
        medias_c = {h: sum(vs) / len(vs) for h, vs in acc_c.items() if vs}
        pico_c = max(medias_c.values()) if medias_c else 0.0
        if pico_c <= 0:
            continue
        for h, m in medias_c.items():
            _por_hora_norm.setdefault(h, []).append(100.0 * m / pico_c)
        _n_com_dados += 1

    from tools.parametros_metodologia import param_int

    _min_conc = param_int("janela_demanda_min_concorrentes")
    pico_horas: dict[int, float] = {}
    if _n_com_dados >= _min_conc:
        pico_horas = {h: sum(vs) / len(vs) for h, vs in _por_hora_norm.items() if vs}
    pico_top = None
    if pico_horas:
        tot = sum(pico_horas.values()) or 1.0
        ordenado = sorted(pico_horas.items(), key=lambda kv: kv[1], reverse=True)
        topn = ordenado[:3]
        pico_top = {
            "horas": [f"{h:02d}h" for h, _ in topn],
            "faixa": _faixa_horas([h for h, _ in topn]),
            "barras": [
                {"hora": f"{h:02d}h", "pct": round(100 * v / max(pico_horas.values()))}
                for h, v in sorted(pico_horas.items())
                if h >= 5
            ],
            "concentracao_pct": round(100 * sum(v for _, v in topn) / tot),
        }

    # Panorama competitivo SINTETIZADO (não há coluna): saturação + rating + total.
    panorama = None
    rating_medio = _num(out.get("rating_medio_concorrentes"))
    nivel_sat = str(out.get("nivel_saturacao") or "") or None
    tot_conc = _int(out.get("total_concorrentes_analisados"))
    if nivel_sat or rating_medio or tot_conc:
        panorama = {
            "saturacao": nivel_sat,
            "rating_medio": rating_medio,
            "total": tot_conc,
            "raio": _int(out.get("total_encontrados_raio")),
        }

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
        posicionamento_estrategico=(
            out.get("posicionamento_estrategico")
            if isinstance(out.get("posicionamento_estrategico"), dict)
            else None
        ),
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
        entrantes_cnpj_bairro=entrantes_bairro,
        entrantes_cnpj_bairro_nome=entrantes_bairro_nome,
        script_abordagem=script,
        metadata={
            "schema_version": header.get("schema_version"),
            "status": header.get("status"),
            # p/ o builder WeasyPrint (HTML): demanda futura datada + perfil idade×sexo.
            "demanda_futura": out.get("demanda_futura") if isinstance(out.get("demanda_futura"), dict) else None,
            "demografia_bairro": out.get("demografia_bairro") if isinstance(out.get("demografia_bairro"), dict) else None,
            # Blocos ricos pra paridade com a UI (só renderizam se presentes).
            "aneis_competitivos": out.get("aneis_competitivos") if isinstance(out.get("aneis_competitivos"), dict) else None,
            "cobertura_redes_a0": out.get("cobertura_redes_a0") if isinstance(out.get("cobertura_redes_a0"), dict) else None,
            "obras_cno_em_curso": out.get("obras_cno_em_curso") if isinstance(out.get("obras_cno_em_curso"), dict) else None,
            "entrantes_cnpj_90d": out.get("entrantes_cnpj_90d") if isinstance(out.get("entrantes_cnpj_90d"), dict) else None,
            "panorama": panorama,
            "pico": pico_top,
            "zoneamento": out.get("zoneamento") if isinstance(out.get("zoneamento"), dict) else None,
            "dores_consolidadas": _agg_dores_consolidadas(competidores_raw),
            "veredito_oceano": (out.get("posicionamento_estrategico") or {}).get("veredito_posicionamento")
            if isinstance(out.get("posicionamento_estrategico"), dict) else None,
        },
    )


def _agg_dores_consolidadas(competidores_raw: list) -> list | None:
    """Consolida dores dos reviews por CATEGORIA (taxonomia) — sem texto literal:
    categoria + nº de menções + academias (com contagem por academia). Espelha
    analisar_gap_competitivo (categorias_dor + categorias_por_academia)."""
    cats: dict[str, int] = {}
    cat_acad: dict[str, dict[str, int]] = {}
    for c in (competidores_raw or []):
        if not isinstance(c, dict):
            continue
        nome = str(c.get("nome") or "—")
        for r in (c.get("reviews") or []):
            if not isinstance(r, dict):
                continue
            cat = (r.get("categoria_dor") or "").strip()
            if not cat or cat.lower() in ("outra", "outras", ""):
                continue
            cats[cat] = cats.get(cat, 0) + 1
            cat_acad.setdefault(cat, {})
            cat_acad[cat][nome] = cat_acad[cat].get(nome, 0) + 1
    if not cats:
        return None
    rows = []
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1])[:8]:
        acads = sorted(cat_acad[cat].items(), key=lambda x: -x[1])
        rows.append({
            "categoria": cat, "mencoes": cnt,
            "academias": [{"nome": a, "vezes": v} for a, v in acads[:5]],
        })
    return rows


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
