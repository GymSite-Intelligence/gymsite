"""Task #40 (run 7456705e): ERRC mandou "Criar Personal (PT) — nenhum concorrente
anuncia" com o Parque Esportes anunciando Personal no quadro da MESMA página.
Causa: o caminho template do A9 calculava a penetração só dos concorrentes
DETALHADOS, ignorando a oferta minerada do state (a fonte que a página exibe).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.a9_positioning_strategist import (
    _SERVICOS_CATALOGO,
    _gaps_reais,
    _penetracao_oferta_unificada,
)


def _state_do_run_7456705e():
    # Reprodução fiel: só VS Club no detalhado (gate); Parque Esportes apenas
    # na oferta minerada do state, com as 11 modalidades gravadas no banco.
    return {
        "oferta_concorrentes": {"oferta_concorrentes": {
            "Academia VS Club - cocó/ Musculação, natação, hidroginástica":
                {"modalidades": ["estetica"]},
            "Parque Esportes": {"modalidades": [
                "area_kids", "crossfit", "danca", "estetica", "funcional",
                "musculacao", "personal", "pilates", "recovery", "spinning", "yoga",
            ]},
        }},
    }


_CONCS_DETALHADOS = [{"nome": "Academia VS Club - cocó/ Musculação, natação, hidroginástica",
                      "planos_precos": [], "servicos_oferecidos": []}]


def test_personal_nao_e_gap_quando_minerado_fora_do_detalhado():
    pen, n = _penetracao_oferta_unificada(_state_do_run_7456705e(), _CONCS_DETALHADOS)
    universo = sorted(set(_SERVICOS_CATALOGO.values()))
    gaps = [s for s in universo if pen.get(s, 0) == 0]
    assert "Personal (PT)" not in gaps
    assert "Artes marciais" in gaps          # esse ninguém anuncia mesmo
    assert n == 2                             # Parque conta na base, mesmo fora do gate


def test_gaps_reais_tambem_exclui_personal():
    assert "Personal (PT)" not in (_gaps_reais(_state_do_run_7456705e()) or [])


def test_sem_oferta_minerada_nao_quebra():
    pen, n = _penetracao_oferta_unificada({}, _CONCS_DETALHADOS)
    assert n == 1
