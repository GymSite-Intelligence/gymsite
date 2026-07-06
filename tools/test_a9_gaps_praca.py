"""Regressão do bug ERRC (Cocó 4b211a02): com 'analisados a fundo: 1', especializados
mapeados na praça (Krav Maga, Eikō, S3) ficavam fora da base de penetração e artes
marciais/personal viravam 'oportunidade de CRIAR'. Valida: (a) keywords novas do
detector; (b) base = praça inteira com dedupe; (c) gap só quando ninguém anuncia."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.a9_positioning_strategist import (
    _concorrentes_para_oferta,
    _gaps_reais,
)
from tools.competitor_offer_mapper import _detectar_modalidades


def _state(detalhados=None, analisadas=None, independentes=None):
    return {"inteligencia_competitiva": {
        "concorrentes_detalhados": detalhados or [],
        "academias_analisadas": analisadas or [],
        "top_independentes": independentes or [],
    }}


def test_keywords_novas_do_detector():
    assert "lutas" in _detectar_modalidades("Eikō Artes Marciais")
    assert "lutas" in _detectar_modalidades("Centro de Krav Maga FSAKM - Ceará")
    assert "personal" in _detectar_modalidades("S3 - Treinamento Personalizado")


def test_base_uniao_com_dedupe():
    st = _state(
        detalhados=[{"nome": "Academia Smart Fit - Papicu"}],
        analisadas=[{"nome": "Academia Smart Fit - Papicu"}, {"nome": "TBOX"}],
        independentes=[{"nome": "Eikō Artes Marciais"}],
    )
    nomes = [c["nome"] for c in _concorrentes_para_oferta(st)]
    assert len(nomes) == 3
    assert nomes.count("Academia Smart Fit - Papicu") == 1


def test_especializado_mapeado_mata_o_falso_gap():
    st = _state(
        detalhados=[{
            "nome": "Academia Smart Fit - Papicu",
            "planos_precos": [{"plano": "Econômico", "inclui": ["Musculação"]}],
        }],
        analisadas=[
            {"nome": "Centro de Krav Maga FSAKM - Ceará - Unid. Cocó"},
            {"nome": "S3 - Treinamento Personalizado"},
            {"nome": "Academia VS Club - cocó/ Musculação, natação, hidroginástica"},
        ],
    )
    gaps = _gaps_reais(st)
    assert gaps is not None
    assert "Artes marciais" not in gaps
    assert "Personal (PT)" not in gaps
    assert "Natação/Hidro" not in gaps
    assert "Musculação" not in gaps


def test_gap_verdadeiro_permanece():
    st = _state(detalhados=[{"nome": "Academia Genérica", "planos_precos": [
        {"plano": "Basico", "inclui": ["Musculação"]}]}])
    gaps = _gaps_reais(st)
    assert gaps is not None
    assert "Aulas/espaço kids" in gaps
    assert "Nutrição integrada" in gaps


def test_sem_concorrentes_retorna_none():
    assert _gaps_reais(_state()) is None
