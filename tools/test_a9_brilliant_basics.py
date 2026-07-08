"""ERRC 'Brilliant Basics' (auditoria Gemini 05/07): dores medidas × público
predominante viram diretrizes determinísticas nas 4 dimensões, cada uma citando
a origem do dado (regra do carimbo)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.a9_positioning_strategist import _dores_da_praca, _publico_dominante


def test_dores_extraidas_do_state():
    state = {"inteligencia_competitiva": {"dores_dominantes": [
        {"categoria": "atendimento_ruim", "mencoes": 4},
        {"categoria": "contrato abusivo", "mencoes": 2},
        {"dor": "ruido_alto"},
        "climatizacao",
    ]}}
    dores = _dores_da_praca(state)
    assert "atendimento_ruim" in dores
    assert "contrato_abusivo" in dores
    assert "ruido_alto" in dores
    assert "climatizacao" in dores


def test_dores_vazio_nao_quebra():
    assert _dores_da_praca({}) == set()
    assert _dores_da_praca({"inteligencia_competitiva": {}}) == set()


def test_publico_dominante_maduro_coco():
    state = {"demografia_bairro": {"perfil_idade_sexo_bairro": {"segmentos": {
        "15-24": {"total": 7162, "pct_mulheres": 52.0},
        "25-39": {"total": 14696, "pct_mulheres": 53.0},
        "40-59": {"total": 16638, "pct_mulheres": 56.0},
        "60+": {"total": 11637, "pct_mulheres": 61.0},
    }}}}
    assert _publico_dominante(state) == ("40-59", 56)


def test_publico_sem_dados_retorna_none():
    assert _publico_dominante({}) is None
    assert _publico_dominante({"demografia_bairro": {}}) is None
