"""
Kits de equipamentos — totais por (modelo, tamanho) pré-calculados do
dataset TS (frontend/src/data/kits/). Source-of-truth pros detalhes UI
fica no frontend; backend usa só os totais pra cascata financeira.

Como regenerar:
    cd frontend && node scripts/exportar-kits-totais.mjs > ../tools/kits_totais.json

Valor `mediana_real` é a média da faixa (estimado_min, estimado_max) após
desconto de volume típico. Usado como `equipamentos_override` no A4.

Função `kit_para_modelo_financeiro` mapeia modelo low|mid|premium pra
tamanho do kit:
  - low → tamanho 1 abaixo (mais econômico)
  - mid → tamanho selecionado (caso-base)
  - premium → tamanho 1 acima (mais robusto)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

ModeloFinanceiro = Literal["low", "mid", "premium"]
TamanhoCodigo = Literal["pp", "p", "m", "g", "gg"]

_KITS_JSON_PATH = Path(__file__).parent / "kits_totais.json"

# Carrega 1× no import — JSON pequeno (~2KB)
try:
    _KITS_TOTAIS = json.loads(_KITS_JSON_PATH.read_text(encoding="utf-8"))
except FileNotFoundError:
    # Em testes/CI o JSON pode não existir — fallback gracioso
    _KITS_TOTAIS = {}

_ORDEM_TAMANHOS: list[TamanhoCodigo] = ["pp", "p", "m", "g", "gg"]


def get_kit_total(modelo: str, tamanho: str) -> float | None:
    """Retorna a mediana_real do kit pra (modelo, tamanho) ou None se ausente."""
    kit = _KITS_TOTAIS.get(modelo, {}).get(tamanho)
    if not kit:
        return None
    return float(kit.get("mediana_real") or 0.0)


def tamanho_para_modelo_financeiro(
    tamanho_base: str, modelo_financeiro: ModeloFinanceiro
) -> str:
    """
    Low → tamanho-1 (clamp em PP).
    Mid → tamanho selecionado.
    Premium → tamanho+1 (clamp em GG).
    """
    if tamanho_base not in _ORDEM_TAMANHOS:
        return tamanho_base
    # pyrefly: ignore [bad-argument-type]
    idx = _ORDEM_TAMANHOS.index(tamanho_base)
    if modelo_financeiro == "low":
        return _ORDEM_TAMANHOS[max(0, idx - 1)]
    if modelo_financeiro == "premium":
        return _ORDEM_TAMANHOS[min(len(_ORDEM_TAMANHOS) - 1, idx + 1)]
    return tamanho_base


def kit_para_modelo_financeiro(
    modelo_negocio: str,
    tamanho_base: str,
    modelo_financeiro: ModeloFinanceiro,
) -> float | None:
    """
    Atalho: retorna o total do kit pro modelo financeiro escolhido.

    Exemplo (tamanho_base=m, academia):
        low → total do kit P   (R$ ~400k)
        mid → total do kit M   (R$ ~600k)
        premium → total do kit G (R$ ~1.8M)
    """
    tamanho_efetivo = tamanho_para_modelo_financeiro(tamanho_base, modelo_financeiro)
    return get_kit_total(modelo_negocio, tamanho_efetivo)


def kit_totais_por_cenario(
    modelo_negocio: str,
    tamanho_base: str,
) -> dict[str, float | None]:
    """
    Retorna dict { 'low': X, 'mid': Y, 'premium': Z } com mediana_real
    do kit pra cada cenário financeiro. Usado pelo A4 macro pra passar
    como equipamentos_override em cada chamada de _calcular_capex_detalhado.
    """
    return {
        "low": kit_para_modelo_financeiro(modelo_negocio, tamanho_base, "low"),
        "mid": kit_para_modelo_financeiro(modelo_negocio, tamanho_base, "mid"),
        "premium": kit_para_modelo_financeiro(modelo_negocio, tamanho_base, "premium"),
    }
