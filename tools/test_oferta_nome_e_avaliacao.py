"""Task #25 — leitura de fonte redefiniu o escopo: o caminho comodidade→catálogo
JÁ existia (texto integral do Wellhub entra no blob e passa pelo detector). Os
furos reais eram: (a) o NOME do concorrente fora do blob — "Academia VS Club -
cocó/ Musculação, natação, hidroginástica" mapeou só ["estetica"] no run
df496c19; (b) sinônimos de avaliação restritos (sem InBody/composição corporal).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_nome_do_vs_club_declara_musculacao_e_piscina():
    from tools.competitor_offer_mapper import _detectar_modalidades

    mods = _detectar_modalidades(
        "Academia VS Club - cocó/ Musculação, natação, hidroginástica")
    assert "musculacao" in mods
    assert "piscina" in mods  # natação/hidroginástica são sinônimos de piscina


def test_sinonimos_wellhub_de_avaliacao_fisica():
    from tools.competitor_offer_mapper import _detectar_modalidades

    assert "avaliacao" in _detectar_modalidades("Comodidades: InBody, armários")
    assert "avaliacao" in _detectar_modalidades("análise de composição corporal inclusa")
    assert "avaliacao" in _detectar_modalidades("Bioimpedância e dobras cutâneas")


def test_nome_com_numero_nao_vira_preco():
    from tools.competitor_offer_mapper import _detectar_precos

    assert _detectar_precos("Academia 300 unidade cocó") == []


def test_nome_semeia_o_blob_de_analise():
    # Fonte da verdade: a primeira entrada de textos_pra_analise é o nome.
    import inspect

    from tools.competitor_offer_mapper import mapear_oferta_concorrente

    src = inspect.getsource(mapear_oferta_concorrente)
    assert "textos_pra_analise: list[str] = [nome or \"\"]" in src
