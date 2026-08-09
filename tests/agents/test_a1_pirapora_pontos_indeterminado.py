"""A1 macro @ Pirapora-MG / Centro — evidência de deprecação.

`analisar_pontos_comerciais_completo` devolve POIs âncora (supermercado etc.)
com sinal heurístico, área estimada e, em praças menores, contaminação fora
da cidade. Não é ponto comercial decidível p/ relatório.

Roda (rede + SEARCHAPI; geocode Google pode negar → Nominatim):

  pytest tests/agents/test_a1_pirapora_pontos_indeterminado.py -q -m integration
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

_CIDADE = "Pirapora"
_UF = "MG"
_BAIRRO = "Centro"


def _searchapi_ok() -> bool:
    return bool((os.getenv("SEARCHAPI_KEY") or "").strip())


pytestmark = [
    pytest.mark.skipif(
        not _searchapi_ok(),
        reason="SEARCHAPI_KEY ausente — macro A1 precisa Maps via SearchAPI",
    ),
    pytest.mark.integration,
]


class _Shim:
    state: dict = {}


@pytest.fixture(scope="module")
def resultado_pirapora_centro():
    """Macro com assinatura correta (shim, bairro, cidade, uf)."""
    # Billing Google Geocoding pode estar OFF localmente — Nominatim cobre.
    os.environ.setdefault("MAPS_FALLBACK_ENABLED", "1")
    from tools.anchoring_tools import analisar_pontos_comerciais_completo

    out = analisar_pontos_comerciais_completo(_Shim(), _BAIRRO, _CIDADE, _UF)
    if not isinstance(out, dict):
        pytest.skip(f"macro retornou não-dict: {type(out)}")
    if out.get("erro") and not (out.get("candidatos") or []):
        pytest.skip(f"macro sem candidatos: {out.get('erro')}")
    return out


def _candidatos(r: dict) -> list[dict]:
    cands = r.get("candidatos") or []
    assert isinstance(cands, list)
    return [c for c in cands if isinstance(c, dict)]


def _fora_pirapora(c: dict) -> bool:
    end = (c.get("endereco") or "").lower()
    # endereço vazio = não dá pra validar praça → conta como indeterminado
    if not end.strip():
        return True
    return "pirapora" not in end


def test_pirapora_maioria_sinal_indireto_heuristico(resultado_pirapora_centro):
    """≥90% candidatos = indireto-heuristico → não é oferta decidível."""
    cands = _candidatos(resultado_pirapora_centro)
    assert cands, "macro vazia — sem material p/ auditar"
    indiretos = [
        c for c in cands if (c.get("qualidade_sinal") or "") == "indireto-heuristico"
    ]
    frac = len(indiretos) / len(cands)
    assert frac >= 0.9, (
        f"esperado ≥90% indireto-heuristico em Pirapora (got {frac:.0%} = "
        f"{len(indiretos)}/{len(cands)}) — se caiu, reavaliar deprecação"
    )


def test_pirapora_contaminação_fora_da_cidade(resultado_pirapora_centro):
    """Maps text-search mistura praças (ex.: Diadema-SP no Top de Pirapora)."""
    cands = _candidatos(resultado_pirapora_centro)
    assert cands
    fora = [c for c in cands if _fora_pirapora(c)]
    assert fora, (
        "esperado ≥1 candidato fora de Pirapora (contaminação / endereço vazio). "
        "Se sumiu, geografia do SearchAPI mudou — revisar fixture."
    )
    # carimbo legível no failure message se alguém inverter o assert
    nomes = [(c.get("nome"), (c.get("endereco") or "")[:70]) for c in fora[:5]]
    assert len(fora) >= 1, nomes


def test_pirapora_area_estimada_heuristica_nao_medida(resultado_pirapora_centro):
    """Área vem de tipo POI (_estimar_area_por_tipo), não de medição/listing."""
    cands = _candidatos(resultado_pirapora_centro)
    com_area = [c for c in cands if c.get("area_estimada_m2")]
    assert com_area, "sem area_estimada_m2 — shape da macro mudou"
    # típico: vários 600 m² (supermercado) — alucinação de área
    areas = [int(c["area_estimada_m2"]) for c in com_area]
    mais_comum = max(set(areas), key=areas.count)
    repetidos = areas.count(mais_comum)
    assert repetidos >= max(2, len(com_area) // 2), (
        f"área deveria repetir heurística (ex. 600); got {areas[:10]}"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DEPRECADO: barra de qualidade p/ ponto decidível. Macro atual falha "
        "em Pirapora (indireto + fora-cidade). Remover xfail só após substituto."
    ),
)
def test_pirapora_barra_ponto_decidivel(resultado_pirapora_centro):
    """Contrato futuro: maioria na cidade + sinal direto (listing/medido)."""
    cands = _candidatos(resultado_pirapora_centro)
    assert len(cands) >= 1
    fora = [c for c in cands if _fora_pirapora(c)]
    assert not fora, f"fora de Pirapora: {[(c.get('nome'), c.get('endereco')) for c in fora[:3]]}"
    indiretos = [
        c for c in cands if (c.get("qualidade_sinal") or "") == "indireto-heuristico"
    ]
    assert len(indiretos) / len(cands) < 0.5
