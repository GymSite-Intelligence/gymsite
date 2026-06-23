"""
Nível de confiança por dado — mapa DETERMINÍSTICO que alimenta os selos do PDF
(spec docs/A9_CONFIDENCE_BADGES_SPEC.md, contrato docs/A9_DATA_CONTRACT.md).

Sem citar fonte real: a confiança vem da PROCEDÊNCIA do número, derivada da
`categoria` do `parametros_metodologia` (param_meta) + sinais de tier:

  categoria 'benchmark'  (ACAD/Sebrae setorial)        -> ESTIMATIVA
  categoria 'calibracao' (limiar/peso metodologia)     -> ESTIMATIVA
  categoria 'aberto'     (premissa/fallback)           -> PROJECAO
  sem param (contagem/observação direta: nº conc.,     -> MEDIDO
             população do censo, rating, aluguel tier-1)

Métrica composta = MENOR confiança das entradas (regra do badge spec §8.2).
"""
from __future__ import annotations

from enum import Enum


class NivelConfianca(str, Enum):
    MEDIDO = "medido"          # observado direto (alta confiança)
    ESTIMATIVA = "estimativa"  # benchmark setorial / calibração (média)
    PROJECAO = "projecao"      # premissa aberta / fallback (baixa)


# Ordem de confiança (índice maior = menor confiança) — usada na agregação.
_ORDEM = (NivelConfianca.MEDIDO, NivelConfianca.ESTIMATIVA, NivelConfianca.PROJECAO)

_CATEGORIA_NIVEL = {
    "benchmark": NivelConfianca.ESTIMATIVA,
    "calibracao": NivelConfianca.ESTIMATIVA,
    "aberto": NivelConfianca.PROJECAO,
}


def nivel_por_categoria(categoria: str | None) -> NivelConfianca:
    """Categoria do param_meta → nível do selo. None/desconhecida = MEDIDO
    (dado observado direto, não derivado de parâmetro de metodologia)."""
    if not categoria:
        return NivelConfianca.MEDIDO
    return _CATEGORIA_NIVEL.get(str(categoria).strip().lower(), NivelConfianca.MEDIDO)


def nivel_por_tier_aluguel(tier) -> NivelConfianca:
    """Aluguel: tier 1 (portais reais medidos) = MEDIDO; tier 2/3 (benchmark/
    grounding) = ESTIMATIVA. tier ausente = PROJECAO (sem lastro)."""
    t = str(tier).strip() if tier is not None else ""
    if t == "1":
        return NivelConfianca.MEDIDO
    if t in ("2", "3"):
        return NivelConfianca.ESTIMATIVA
    return NivelConfianca.PROJECAO


def agregar_nivel(*niveis: NivelConfianca | None) -> NivelConfianca:
    """Selo de métrica composta = MENOR confiança das entradas. Vazio = MEDIDO."""
    presentes = [n for n in niveis if n]
    if not presentes:
        return NivelConfianca.MEDIDO
    return max(presentes, key=_ORDEM.index)


# Rótulo curto exibido no selo (UPPER) — fixo por nível (badge spec §3).
ROTULO = {
    NivelConfianca.MEDIDO: "DADO MEDIDO",
    NivelConfianca.ESTIMATIVA: "ESTIMATIVA",
    NivelConfianca.PROJECAO: "PROJEÇÃO",
}
