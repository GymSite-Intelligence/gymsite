"""
Enricher — enriquece oportunidades com dados do GymSite existentes.

Reusa:
- tools.apollo_enrichment (contato / decision-maker)
- tools.cnpj_segment_classifier (segmento_operacao)
- tools.cnpj_fitness_tools (nome de exibição)
"""
from __future__ import annotations

from typing import Any

from tools.cnpj_fitness_tools import nome_exibicao_cnpj


def enrich_opportunity(opp: dict[str, Any]) -> dict[str, Any]:
    """
    Enriquece uma oportunidade com contato, nome limpo e prioridade.
    Modifica o dict in-place e retorna-o.
    """
    # Nome de exibição limpo
    nome_exib, fantasia_limpa, inferido_de = nome_exibicao_cnpj(
        opp.get("nome_fantasia"), opp.get("razao_social")
    )
    opp["nome_exibicao"] = nome_exib
    opp["nome_fantasia_limpo"] = fantasia_limpa
    opp["nome_inferido_de"] = inferido_de

    # Contato (Apollo / RFB) — best-effort
    contato = _buscar_contato(opp.get("cnpj"), opp.get("razao_social"), opp.get("nome_fantasia"))
    opp["contato_cnpj"] = contato

    # Prioridade baseada em score + área
    opp["prioridade"] = _calcular_prioridade(opp)

    return opp


def _buscar_contato(
    cnpj: str | None,
    razao_social: str | None,
    nome_fantasia: str | None,
) -> dict[str, Any]:
    """
    Tenta enriquecer contato via Apollo ou dados RFB locais.
    Retorna dict padronizado; nunca falha.
    """
    contato: dict[str, Any] = {
        "telefone": None,
        "email": None,
        "whatsapp_link": None,
        "decision_maker": None,
        "cargo": None,
        "fonte": None,
    }

    # 1. Apollo enrichment (best-effort)
    try:
        from tools.apollo_enrichment import enriquecer_empresa_com_apollo

        if cnpj:
            apollo = enriquecer_empresa_com_apollo(cnpj)
            if apollo and apollo.get("status") == "ok":
                pessoas = apollo.get("pessoas") or []
                if pessoas:
                    top = pessoas[0]
                    contato["decision_maker"] = top.get("nome")
                    contato["cargo"] = top.get("cargo")
                    contato["email"] = top.get("email")
                    contato["telefone"] = top.get("telefone")
                    contato["fonte"] = "apollo"
    except Exception:
        pass

    # 2. Fallback: WhatsApp link pelo CNPJ (se telefone existir)
    telefone = contato.get("telefone")
    if telefone:
        digits = "".join(filter(str.isdigit, str(telefone)))
        if len(digits) >= 10:
            contato["whatsapp_link"] = f"https://wa.me/55{digits}"

    return contato


def _calcular_prioridade(opp: dict[str, Any]) -> str:
    """Define prioridade com base em regras de negócio."""
    score = opp.get("score_match") or 0.0
    area = opp.get("area_total_m2") or 0.0
    situacao = opp.get("situacao_obra") or ""

    if score >= 0.9 and area >= 500 and situacao == "em_curso":
        return "critica"
    if score >= 0.75 and area >= 300:
        return "alta"
    if score >= 0.5:
        return "media"
    return "baixa"
