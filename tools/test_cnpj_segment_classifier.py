"""Testes rápidos do classificador de segmento CNPJ."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.cnpj_segment_classifier import classificar_segmento


def test_crossfit():
    assert classificar_segmento("CrossFit Aldeota Box").segmento == "crossfit_box"


def test_pilates():
    assert classificar_segmento("Studio Pilates Meireles").segmento == "studio_pilates"


def test_academia_typo():
    assert classificar_segmento("ACADENIA GENESE").segmento == "academia"


def test_danca():
    assert (
        classificar_segmento("ACADEMIA DE DANCA VERA PASSOS").segmento
        == "studio_bem_estar"
    )


def test_fisio_excluida():
    c = classificar_segmento("CLINICA DE FISIOTERAPIA SILVA")
    assert c.segmento == "saude_clinica"
    assert not c.incluir_no_parque


def test_sem_outro():
    c = classificar_segmento("ALPHA7 PERFORMANCE")
    assert c.segmento != "outro"


def test_vazio_academia_baixa():
    c = classificar_segmento("")
    assert c.segmento == "academia"
    assert c.confianca == "baixa"


if __name__ == "__main__":
    test_crossfit()
    test_pilates()
    test_academia_typo()
    test_danca()
    test_fisio_excluida()
    test_sem_outro()
    test_vazio_academia_baixa()
    print("ok")
