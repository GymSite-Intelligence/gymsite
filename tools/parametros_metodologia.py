"""
Parâmetros de metodologia — REGRA DE OURO: zero hardcode.

Todo fator de cálculo do enriquecimento (ocupação, penetração, market share,
ticket, janelas) é um registro {valor, fonte, data_coleta, metodo, unidade},
recalibrável via tabela Supabase `parametros_metodologia` (override), com default
SÓ como fallback rotulado. Toda métrica carrega a fonte → exibida no relatório.

Ver feedback memory regra-ouro-zero-hardcode-metodologia + PLANO_ENRIQUECIMENTO §1.0.
"""
from __future__ import annotations

import os
from typing import Any

# Defaults documentados (fallback rotulado — NUNCA verdade silenciosa).
# Cada um: valor, fonte, data_coleta, metodo, unidade.
_DEFAULTS: dict[str, dict[str, Any]] = {
    # Ocupação por tipologia (moradores por unidade). IBGE média domiciliar + ajuste tipologia.
    "ocupacao_studio":      {"valor": 1.5, "fonte": "IBGE PNAD + ajuste tipologia studio", "data_coleta": "2026-06-14", "metodo": "media_domiciliar_ajustada", "unidade": "moradores/unidade"},
    "ocupacao_1_2_dorm":    {"valor": 2.2, "fonte": "IBGE PNAD + ajuste 1-2 dorm", "data_coleta": "2026-06-14", "metodo": "media_domiciliar_ajustada", "unidade": "moradores/unidade"},
    "ocupacao_3_mais_dorm": {"valor": 3.0, "fonte": "IBGE PNAD + ajuste 3+ dorm", "data_coleta": "2026-06-14", "metodo": "media_domiciliar_ajustada", "unidade": "moradores/unidade"},
    "ocupacao_default":     {"valor": 2.8, "fonte": "fallback_IBGE_media_domiciliar_BR", "data_coleta": "2026-06-14", "metodo": "media_nacional", "unidade": "moradores/unidade"},
    # m²/unidade — proxy quando não há contagem exata de unidades (refino A4 sobrescreve).
    "m2_por_unidade":       {"valor": 75.0, "fonte": "fallback_proxy_unidade_media+area_comum", "data_coleta": "2026-06-14", "metodo": "proxy_area_construida", "unidade": "m2/unidade"},
    # Penetração fitness (% da população que frequenta academia). ACAD/Panorama Fitness.
    "penetracao_geral":     {"valor": 0.045, "fonte": "ACAD/Panorama Fitness Brasil", "data_coleta": "2026-06-14", "metodo": "penetracao_mercado", "unidade": "fração"},
    "penetracao_bairro_ab": {"valor": 0.10, "fonte": "ACAD (bairro alta renda A/B)", "data_coleta": "2026-06-14", "metodo": "penetracao_mercado_segmentada", "unidade": "fração"},
    # Market share capturável no raio — default conservador; A4/anéis sobrescreve.
    "market_share_default": {"valor": 0.15, "fonte": "fallback_conservador (A4/anéis recalibra)", "data_coleta": "2026-06-14", "metodo": "quota_raio_estimada", "unidade": "fração"},
    # Inadimplência média (recorrência). Benchmark setorial canal 2.
    "inadimplencia_default": {"valor": 0.06, "fonte": "fallback_ACAD_com_recorrencia", "data_coleta": "2026-06-14", "metodo": "benchmark_setorial", "unidade": "fração"},
    # Janelas temporais (CNO → entrega → compra equipamento).
    "meses_entrega":        {"valor": 30, "fonte": "fallback_mediana_obra_24_36m (recalibrar CNO encerradas)", "data_coleta": "2026-06-14", "metodo": "mediana_tempo_obra", "unidade": "meses"},
    "janela_compra_equipamento_meses": {"valor": 4, "fonte": "fallback_3_6m_antes_entrega", "data_coleta": "2026-06-14", "metodo": "lead_time_compra", "unidade": "meses"},
    # Anéis competitivos (Apêndice D) — pesos por anel + raio de fronteira.
    "anel_peso_no_bairro":  {"valor": 1.0, "fonte": "Motor v2 Apêndice D", "data_coleta": "2026-06-14", "metodo": "peso_anel", "unidade": "fator"},
    "anel_peso_fronteira":  {"valor": 0.5, "fonte": "Motor v2 Apêndice D", "data_coleta": "2026-06-14", "metodo": "peso_anel", "unidade": "fator"},
    "anel_peso_regional":   {"valor": 0.2, "fonte": "Motor v2 Apêndice D", "data_coleta": "2026-06-14", "metodo": "peso_anel", "unidade": "fator"},
    "raio_fronteira_km":    {"valor": 2.0, "fonte": "Motor v2 Apêndice D (≤2km da borda)", "data_coleta": "2026-06-14", "metodo": "raio_anel", "unidade": "km"},
    # Porte de academia por nº de avaliações (Places) — recalibrável.
    "porte_pequena_max_avaliacoes": {"valor": 150, "fonte": "fallback_heuristica_places", "data_coleta": "2026-06-14", "metodo": "limiar_porte", "unidade": "avaliacoes"},
    "porte_media_max_avaliacoes":   {"valor": 600, "fonte": "fallback_heuristica_places", "data_coleta": "2026-06-14", "metodo": "limiar_porte", "unidade": "avaliacoes"},
}

_OVERRIDE_CACHE: dict[str, dict[str, Any]] | None = None


def _carregar_overrides() -> dict[str, dict[str, Any]]:
    """Override recalibrável da tabela Supabase parametros_metodologia (best-effort)."""
    global _OVERRIDE_CACHE
    if _OVERRIDE_CACHE is not None:
        return _OVERRIDE_CACHE
    _OVERRIDE_CACHE = {}
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not (os.environ.get("SUPABASE_URL") and key):
        return _OVERRIDE_CACHE
    try:
        from tools.supabase_client import load_create_client

        cli = load_create_client()(os.environ["SUPABASE_URL"], key)
        res = cli.table("parametros_metodologia").select("*").execute()
        for row in getattr(res, "data", None) or []:
            nome = row.get("nome")
            if nome and row.get("valor") is not None:
                _OVERRIDE_CACHE[nome] = row
    except Exception as e:
        print(f"[parametros] override Supabase indisponível: {type(e).__name__}: {e}")
    return _OVERRIDE_CACHE


def param_meta(nome: str) -> dict[str, Any]:
    """Registro completo do parâmetro (valor + fonte + metodo) — para exibir no relatório."""
    override = _carregar_overrides().get(nome)
    base = _DEFAULTS.get(nome)
    if override:
        rec = {**(base or {}), **override}
        rec.setdefault("fonte", "supabase_override")
        return rec
    if base is None:
        raise KeyError(f"parâmetro de metodologia desconhecido: {nome!r}")
    return dict(base)


def param(nome: str) -> float:
    """Valor numérico do parâmetro (override Supabase > default rotulado)."""
    return float(param_meta(nome)["valor"])


def ocupacao_por_tipologia(tipologia: str | None) -> str:
    """Mapeia tipologia (do lançamento) → chave de parâmetro de ocupação."""
    t = (tipologia or "").lower()
    if "studio" in t or "stúdio" in t or "kit" in t:
        return "ocupacao_studio"
    if "3" in t or "4" in t or "alto padr" in t:
        return "ocupacao_3_mais_dorm"
    if "1 " in t or "2 " in t or "1-2" in t or "dorm" in t:
        return "ocupacao_1_2_dorm"
    return "ocupacao_default"
