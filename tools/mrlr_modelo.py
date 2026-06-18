"""Modelo de Regressão Linear de Locação (MRLR) — IBAPE-GO.

Estima o aluguel comercial (R$/m²/mês) por uma EQUAÇÃO ÚNICA (estudo IBAPE-GO, R²=0,8633),
substituindo a amostragem instável de portais (que variava por run). Metodologia é UMA —
sem adaptação: coeficientes fixos do estudo; só os 6 inputs mudam por local.

    Valor Unitário = [ b0 + b1·ln(Área) + b2·ln(Padrão) + b3·Local + b4·ln(Porte)
                       + b5·(1/PIB) + b6·Fator Econômico ] ²

Coeficientes e escalas são DADO (catalogos_metodologia: mrlr_coef, mrlr_escala) — não
inline. Inputs: Área (anúncio), Padrão (quartil de preço), Local (zoneamento),
Porte/PIB/Fator (IBGE).
"""
from __future__ import annotations

import math
from typing import Any


def _coef() -> dict[str, float]:
    from tools.catalogos import catalogo_num

    return catalogo_num("mrlr_coef")


def _escala() -> dict[str, float]:
    from tools.catalogos import catalogo_num

    return catalogo_num("mrlr_escala")


def porte_de_populacao(pop: float | None) -> int:
    """População do município (IBGE) → porte 1–4 (escala do catálogo)."""
    e = _escala()
    p = float(pop or 0)
    if p < 30_000:
        return int(e.get("porte_ate30k", 1))
    if p < 50_000:
        return int(e.get("porte_30a50k", 2))
    if p < 100_000:
        return int(e.get("porte_50a100k", 3))
    return int(e.get("porte_acima100k", 4))


def fator_de_pib_per_capita(pib_pc: float | None) -> int:
    """PIB per capita (IBGE) → fator econômico 1 (<50k) ou 2 (≥50k)."""
    return 2 if float(pib_pc or 0) >= 50_000 else 1


def local_de_zona(zona_sigla: str | None) -> int:
    """Zona (zoneamento) → fator Local: ZEDUS/ZOC/uso geral=2 (alto fluxo), ZEIS/ZEA=1."""
    e = _escala()
    s = (zona_sigla or "").upper()
    if s.startswith(("ZEIS", "ZEA")):
        return int(e.get("local_zeis_zea", 1))
    return int(e.get("local_zedus_zoc", 2))


def padrao_de_preco(preco: float | None, p25: float | None, p75: float | None) -> int:
    """Preço do anúncio vs quartis do mercado → padrão construtivo 1/2/3."""
    e = _escala()
    if preco is None or p25 is None or p75 is None:
        return int(e.get("padrao_normal", 2))
    if preco < p25:
        return int(e.get("padrao_baixo", 1))
    if preco > p75:
        return int(e.get("padrao_alto", 3))
    return int(e.get("padrao_normal", 2))


def valor_unitario_mrlr(area_m2: float, padrao: int, local: int,
                        porte: int, pib: float, fator: int) -> float | None:
    """Equação IBAPE-GO → Valor Unitário (R$/m²/mês). None se input inválido."""
    c = _coef()
    if not c or area_m2 <= 0 or padrao <= 0 or porte <= 0 or pib <= 0:
        return None
    base = (
        c["intercepto"]
        + c["ln_area"] * math.log(area_m2)
        + c["ln_padrao"] * math.log(padrao)
        + c["local"] * local
        + c["ln_porte"] * math.log(porte)
        + c["inv_pib"] * (1.0 / pib)
        + c["fator_economico"] * fator
    )
    if base <= 0:
        return None
    return round(base ** 2, 2)


def estimar_aluguel_mrlr(area_m2: float, *, zona_sigla: str | None,
                         populacao_municipio: float, pib_municipio: float,
                         pib_per_capita: float, preco_anuncio: float | None = None,
                         preco_p25: float | None = None, preco_p75: float | None = None
                         ) -> dict[str, Any]:
    """Aluguel comercial do imóvel via MRLR. Retorna valor unitário (R$/m²) + total +
    os 6 inputs auditáveis. status=ok|indisponivel."""
    porte = porte_de_populacao(populacao_municipio)
    fator = fator_de_pib_per_capita(pib_per_capita)
    local = local_de_zona(zona_sigla)
    padrao = padrao_de_preco(preco_anuncio, preco_p25, preco_p75)
    vu = valor_unitario_mrlr(area_m2, padrao, local, porte, pib_municipio, fator)
    if vu is None:
        return {"status": "indisponivel", "motivo": "inputs insuficientes (área/PIB/porte)"}
    return {
        "status": "ok",
        "valor_unitario_m2": vu,
        "aluguel_total": round(vu * area_m2, 2),
        "inputs": {"area_m2": area_m2, "padrao": padrao, "local": local,
                   "porte": porte, "pib": pib_municipio, "fator_economico": fator},
        "fonte": "MRLR IBAPE-GO (R²=0,8633) — equação única, coeficientes catalogos_metodologia",
        "metodo": "Valor Unitário = [b0 + b1·ln(Área) + b2·ln(Padrão) + b3·Local + b4·ln(Porte) + b5/PIB + b6·Fator]²",
    }
