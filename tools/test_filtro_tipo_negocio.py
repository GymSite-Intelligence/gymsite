"""Filtro de relevância por tipo_negocio do form: a categoria do Google é autoritativa.
'academia' (genérico) tira especialidades (CrossFit/Artes Marciais/Pilates); alvos
especializados mantêm só quem bate a especialidade; 'outro' não filtra."""
from tools.competitor_tools import _tipo_relevante

_REK = {"nome": "Complexo REK CrossFit", "tipos": ["Academia de crossfit", "gym"]}
_EIKO = {"nome": "Eiko Artes Marciais", "tipos": ["Artes marciais"]}
_VS = {"nome": "Academia VS Club - Musculacao, natacao", "tipos": ["Academia", "gym"]}
_SMART = {"nome": "Smart Fit", "tipos": ["Academia", "gym"]}
_PILATES = {"nome": "Studio Pilates Zen", "tipos": ["Estudio de pilates"]}


def test_academia_tira_especialidades():
    assert _tipo_relevante(_REK, "academia") is False      # crossfit box fora
    assert _tipo_relevante(_EIKO, "academia") is False      # luta fora
    assert _tipo_relevante(_PILATES, "academia") is False   # pilates fora
    assert _tipo_relevante(_VS, "academia") is True         # musculação (c/ piscina) fica
    assert _tipo_relevante(_SMART, "academia") is True


def test_academia_com_piscina_nao_e_dropada_por_natacao():
    # 'natacao' no NOME não tira (academia com piscina); só categoria especializada tira
    c = {"nome": "Academia X com natacao", "tipos": ["Academia"]}
    assert _tipo_relevante(c, "academia") is True


def test_crossfit_box_mantem_so_crossfit():
    assert _tipo_relevante(_REK, "crossfit_box") is True
    assert _tipo_relevante(_VS, "crossfit_box") is False
    assert _tipo_relevante(_EIKO, "crossfit_box") is False


def test_studio_pilates_mantem_so_pilates():
    assert _tipo_relevante(_PILATES, "studio_pilates") is True
    assert _tipo_relevante(_VS, "studio_pilates") is False
    assert _tipo_relevante(_REK, "studio_pilates") is False


def test_outro_nao_filtra():
    for c in (_REK, _EIKO, _VS, _SMART, _PILATES):
        assert _tipo_relevante(c, "outro") is True
