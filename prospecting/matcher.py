"""
Matcher — cruza CNPJ fitness entrantes com obras CNO.

Reusa a lógica consagrada de tools.cno_fitness_tools.cruzar_entrantes_obras_cno
e normaliza o resultado em objetos planos para persistência.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.cno_fitness_tools import _digits
from tools.cno_fitness_tools import cruzar_entrantes_obras_cno


def match_opportunities(
    *,
    cidade: str,
    uf: str = "CE",
    dias: int = 90,
    limit: int = 500,
    cno_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Executa o cruzamento CNPJ × CNO e retorna uma lista flat de oportunidades
    normalizadas, prontas para enriquecimento e persistência.

    Campos de saída (dict):
      - cnpj, razao_social, nome_fantasia, segmento_operacao
      - data_inicio_atividade, situacao_cadastral, cep, endereco_cnpj
      - cno, nome_obra, situacao_obra, area_total_m2
      - data_inicio_obra, data_situacao_obra, endereco_cno
      - score_match, motivo_match, match_metodo, match_confianca
    """
    if cno_dir is None:
        from prospecting.config import Config

        cno_dir = Config.resolve_cno_dir()

    if cno_dir is None:
        raise RuntimeError(
            "CNO_DATA_DIR não configurado. "
            "Defina a variável de ambiente CNO_DATA_DIR."
        )

    raw = cruzar_entrantes_obras_cno(
        cno_dir=cno_dir,
        cidade=cidade,
        uf=uf,
        dias=dias,
        limit=limit,
    )

    if raw.get("status") != "ok":
        raise RuntimeError(f"Falha no cruzamento: {raw.get('erro') or raw}")

    oportunidades: list[dict[str, Any]] = []

    for item in raw.get("cruzamentos") or []:
        obra = item.get("obra") or {}
        metodo = item.get("match_cno")
        confianca = item.get("match_confianca")

        # Score numérico baseado na confiança do match existente
        score, motivo = _calcular_score(metodo, confianca, item, obra)

        opp: dict[str, Any] = {
            "cnpj": _digits(item.get("cnpj")),
            "razao_social": item.get("razao_social") or item.get("nome_fantasia"),
            "nome_fantasia": item.get("nome_fantasia"),
            "segmento_operacao": item.get("segmento_operacao"),
            "data_inicio_atividade": item.get("data_abertura"),
            "situacao_cadastral": item.get("situacao_cadastral"),
            "cep": _digits(item.get("cep")),
            "endereco_cnpj": {
                "logradouro": item.get("logradouro"),
                "numero": item.get("numero"),
                "bairro": item.get("bairro"),
                "cidade": cidade,
                "uf": uf,
            },
            "cno": obra.get("cno") if isinstance(obra, dict) else None,
            "nome_obra": obra.get("nome_obra") if isinstance(obra, dict) else None,
            "situacao_obra": obra.get("situacao_obra") if isinstance(obra, dict) else None,
            "area_total_m2": obra.get("area_m2") if isinstance(obra, dict) else None,
            "data_inicio_obra": obra.get("data_inicio") if isinstance(obra, dict) else None,
            "data_situacao_obra": obra.get("data_situacao") if isinstance(obra, dict) else None,
            "endereco_cno": {
                "logradouro": obra.get("logradouro") if isinstance(obra, dict) else None,
                "numero": obra.get("numero") if isinstance(obra, dict) else None,
                "bairro": obra.get("bairro") if isinstance(obra, dict) else None,
                "cidade": cidade,
                "uf": uf,
            },
            "score_match": score,
            "motivo_match": motivo,
            "match_metodo": metodo,
            "match_confianca": confianca,
            "projecao_receita": item.get("projecao_receita_estimada"),
            "capacidade_matriculas": item.get("capacidade_matriculas_estimada"),
        }
        oportunidades.append(opp)

    return oportunidades


def _calcular_score(
    metodo: str | None,
    confianca: str | None,
    item: dict,
    obra: dict | None,
) -> tuple[float, str]:
    """Converte método+confiança em score numérico 0.0–1.0 e descrição."""
    if metodo == "cnpj_responsavel":
        return 0.95, "CNPJ responsável da obra idêntico ao CNPJ do estabelecimento"
    if metodo == "nome_obra_cep8":
        return 0.75, "Nome da obra coincide com fantasia no mesmo CEP"
    if metodo == "cep8_multiplas_obras":
        return 0.35, "Várias obras no mesmo CEP sem match por nome"
    return 0.0, "Sem match CNO"
