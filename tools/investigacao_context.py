"""
Contexto de relatório para investigação web de imóveis (A1).

Alinha input_params do formulário com faixas de porte do CNO e projeção A4/CNO
(financial_tools.projecao_demanda_receita_obra) — sem chamar API de cartório ONR.
"""
from __future__ import annotations

import re
from typing import Any

from tools.cno_fitness_tools import _faixa_porte_m2
from tools.financial_tools import projecao_demanda_receita_obra

# API Indicador Real (ONR) — tipoImovel (referência; integração cartório é outro fluxo)
TIPOS_IMOVEL_ONR: dict[int, str] = {
    64: "Casa",
    65: "Apto",
    15: "Loja",
    17: "Sala",
    71: "Terreno/Fração",
    31: "Galpão",
    33: "Prédio Comercial",
    35: "Prédio Residencial",
    69: "Fazenda/Sítio/Chácara",
    89: "Outros",
}

# Tipos que o scraper OLX/ImovelWeb e o A1 priorizam para academia
TIPOS_IMOVEL_ALVO_ACADEMIA: list[dict[str, Any]] = [
    {
        "codigo_onr": 31,
        "label": "Galpão",
        "nota": "Pé-direito alto, vão livre — comum em listings 'galpão/deposito'",
    },
    {
        "codigo_onr": 33,
        "label": "Prédio Comercial",
        "nota": "Edifício inteiro ou bloco — área grande",
    },
    {
        "codigo_onr": 15,
        "label": "Loja",
        "nota": "Ponto de rua / shopping",
    },
    {
        "codigo_onr": 17,
        "label": "Sala",
        "nota": "Sala comercial em edifício",
    },
]

# Área de referência por preset (kits academia — frontend/src/data/kits/academia.ts)
PRESET_AREA_REF_M2: dict[str, int] = {
    "pp": 300,
    "p": 600,
    "m": 1000,
    "g": 2000,
    "gg": 4000,
}

# Preset Smart Fit → faixa ticket A4/CNO (mesma lógica de densidade matr/m²)
PRESET_PARA_FAIXA_TICKET: dict[str, str] = {
    "pp": "low",
    "p": "low",
    "m": "mid",
    "g": "premium",
    "gg": "premium",
}

_KEYWORDS_TIPO: list[tuple[str, str, int]] = [
    (r"galp[aã]o|deposito|depósito|armaz[eé]m", "Galpão", 31),
    (r"pr[eé]dio|edif[ií]cio\s+inteiro", "Prédio Comercial", 33),
    (r"loja|ponto\s+comercial|box", "Loja", 15),
    (r"sala\s+comercial", "Sala", 17),
    (r"terreno|lote", "Terreno/Fração", 71),
]


def build_contexto_investigacao(input_params: dict | None) -> dict[str, Any]:
    """Monta contexto forte a partir de input_params do relatório (api.py → A1)."""
    p = input_params or {}
    cidade = (p.get("cidade") or "").strip()
    bairro = (p.get("bairro") or "").strip()
    uf = (p.get("uf") or "").strip()
    tipo_negocio = (p.get("tipo_negocio") or "academia").strip()
    preset = (p.get("tamanho_preset") or "m").strip().lower()
    area_min = int(p.get("area_m2_min") or 500)
    area_max = int(p.get("area_m2_max") or 5000)
    genero = (p.get("genero_alvo") or p.get("publico_alvo") or "misto").strip()

    area_ref = PRESET_AREA_REF_M2.get(preset, PRESET_AREA_REF_M2["m"])
    faixa_ticket = PRESET_PARA_FAIXA_TICKET.get(preset, "mid")
    projecao_ref = projecao_demanda_receita_obra(float(area_ref), faixa_ticket)

    return {
        "cidade": cidade,
        "bairro": bairro,
        "uf": uf,
        "tipo_negocio": tipo_negocio,
        "tamanho_preset": preset,
        "area_m2_min": area_min,
        "area_m2_max": area_max,
        "area_referencia_preset_m2": area_ref,
        "genero_alvo": genero,
        "faixa_ticket": faixa_ticket,
        "tipos_imovel_onr_prioritarios": TIPOS_IMOVEL_ALVO_ACADEMIA,
        "projecao_preset_referencia": projecao_ref,
        "faixa_porte_preset": _faixa_porte_m2(float(area_ref)),
    }


def inferir_tipo_imovel_candidato(candidato: dict) -> dict[str, Any]:
    """Heurística título/tipos → tipo ONR + label (listings não trazem código ONR)."""
    texto = " ".join(
        [
            str(candidato.get("nome") or ""),
            str(candidato.get("title") or ""),
            str(candidato.get("motivo") or ""),
            " ".join(candidato.get("tipos") or []),
        ]
    ).lower()

    for pattern, label, codigo in _KEYWORDS_TIPO:
        if re.search(pattern, texto, re.I):
            return {
                "tipo_imovel_label": label,
                "tipo_imovel_codigo_onr": codigo,
                "inferido_de": "titulo_ou_tipos",
            }

    if candidato.get("qualidade_sinal") == "direto-listing":
        return {
            "tipo_imovel_label": "Comercial (listing)",
            "tipo_imovel_codigo_onr": None,
            "inferido_de": "listing_sem_keyword",
        }
    return {
        "tipo_imovel_label": "Estabelecimento / âncora",
        "tipo_imovel_codigo_onr": None,
        "inferido_de": "places_ancora",
    }


def projecao_para_area_candidato(
    area_m2: float,
    contexto: dict[str, Any],
) -> dict[str, Any]:
    """Mesmo cross-process CNO: faixa porte m² + projecao_demanda_receita_obra."""
    if area_m2 <= 0:
        return {"status": "sem_area"}
    faixa_ticket = contexto.get("faixa_ticket") or "mid"
    porte = _faixa_porte_m2(area_m2)
    proj = projecao_demanda_receita_obra(area_m2, faixa_ticket)
    return {
        "faixa_porte_m2": porte,
        "projecao": proj,
    }


def formatar_bloco_contexto_prompt(
    contexto: dict[str, Any],
    candidato: dict,
) -> str:
    """Texto injetado no prompt de investigação (macro + micro)."""
    tipo_inf = inferir_tipo_imovel_candidato(candidato)
    area_cand = float(
        candidato.get("area_m2")
        or candidato.get("area_estimada_m2")
        or candidato.get("area")
        or 0
    )
    proj_cand = (
        projecao_para_area_candidato(area_cand, contexto)
        if area_cand > 0
        else None
    )

    tipos_lines = "\n".join(
        f"  - {t['label']} (ONR {t['codigo_onr']}): {t['nota']}"
        for t in contexto.get("tipos_imovel_onr_prioritarios") or []
    )

    proj_ref = contexto.get("projecao_preset_referencia") or {}
    mat_ref = (proj_ref.get("matriculas") or {}).get("realista") or {}
    rec_ref = (proj_ref.get("receita_mensal_estimada") or {}).get("realista")

    lines = [
        "## Contexto do relatório (investidor)",
        f"- **Prospecção:** {contexto.get('tipo_negocio')} | preset **{contexto.get('tamanho_preset')}** "
        f"(~{contexto.get('area_referencia_preset_m2')} m² referência de kit)",
        f"- **Faixa de busca de imóveis:** {contexto.get('area_m2_min')}–{contexto.get('area_m2_max')} m²",
        f"- **Local alvo:** {contexto.get('bairro') or '—'}, {contexto.get('cidade')}, {contexto.get('uf') or '—'}",
        f"- **Público:** {contexto.get('genero_alvo')}",
        "",
        "## Tipos de imóvel relevantes (ONR / mercado)",
        "A API de cartório ONR classifica `tipoImovel` por código; nossos listings não trazem o código, "
        "mas a busca prioriza:",
        tipos_lines,
        "",
        f"## Candidato atual — tipo inferido",
        f"- **{tipo_inf.get('tipo_imovel_label')}**"
        + (
            f" (código ONR {tipo_inf.get('tipo_imovel_codigo_onr')})"
            if tipo_inf.get("tipo_imovel_codigo_onr")
            else ""
        ),
        f"- Inferência: {tipo_inf.get('inferido_de')}",
    ]

    if proj_cand and proj_cand.get("projecao", {}).get("status") == "ok":
        p = proj_cand["projecao"]
        mat = (p.get("matriculas") or {}).get("realista") or {}
        rec = (p.get("receita_mensal_estimada") or {}).get("realista")
        lines.extend(
            [
                "",
                "## Benchmark operacional (mesma lógica CNO/A4 — só referência)",
                f"- Área do candidato: **{area_cand:.0f} m²** → porte **{proj_cand.get('faixa_porte_m2')}**",
                f"- Matrículas realistas (estimativa): **{mat.get('valor', '—')}** "
                f"({mat.get('matr_por_m2', '—')} matr/m²)",
                f"- Receita mensal estimada (estimativa): **R$ {rec:,.0f}**" if rec else "",
                "- Não confundir com faturamento do negócio que opera no endereço hoje.",
            ]
        )
    elif proj_ref.get("status") == "ok":
        lines.extend(
            [
                "",
                "## Benchmark preset (referência do tamanho escolhido no formulário)",
                f"- Preset {contexto.get('tamanho_preset')}: ~{mat_ref.get('valor', '—')} matrículas realistas, "
                f"receita ~R$ {rec_ref:,.0f}/mês" if rec_ref else "",
            ]
        )

    lines.extend(
        [
            "",
            "## Foco da investigação",
            "Confirmar **quem opera no endereço hoje** e se o ponto é compatível com "
            f"{contexto.get('tipo_negocio')} (~{contexto.get('area_m2_min')}–{contexto.get('area_m2_max')} m², "
            f"pé-direito/vão livre se galpão ou prédio).",
        ]
    )
    return "\n".join(line for line in lines if line is not None)
