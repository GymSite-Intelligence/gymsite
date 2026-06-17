"""Classificação residencial das obras CNO da demanda futura: o padrão dominante do CNO
é SPE de incorporação ('EMPREENDIMENTOS IMOBILIARIOS', plural) — antes só pegava o
singular e subnotificava a demanda (parecia 'sem sentido')."""
from tools.cno_bigquery_loader import _KW_COMERCIAL, _KW_RESIDENCIAL


def _eh_residencial(nome: str) -> bool:
    n = nome.lower()
    if any(k in n for k in _KW_RESIDENCIAL):
        return True
    if any(k in n for k in _KW_COMERCIAL):
        return False
    return False  # sem sinal → conservador (não-residencial)


def test_empreendimentos_imobiliarios_plural():
    # bug corrigido: plural não casava
    assert _eh_residencial("SPE COCO 01 EMPREENDIMENTOS IMOBILIARIOS S/A") is True
    assert _eh_residencial("COLMEIA LIKE EMPREENDIMENTOS IMOBILIARIOS SPE LTDA") is True


def test_singular_segue_residencial():
    assert _eh_residencial("BS RUBI EMPREENDIMENTO IMOBILIARIO SPE LTDA") is True


def test_residence_ingles_e_reserva():
    assert _eh_residencial("VICTORIA PARK RESIDENCE EMPREENDIMENTOS IMOBILIARIOS") is True
    assert _eh_residencial("RESERVA VILA DO SOL") is True


def test_spe_so_residencial_com_imobiliario():
    # 'spe' sozinho é conservador (também é infra/energia); só vira residencial com sinal real
    assert _eh_residencial("SPE EN2 LTDA") is False
    assert _eh_residencial("SPE EN2 EMPREENDIMENTO IMOBILIARIO LTDA") is True


def test_comercial_e_generico_ficam_fora():
    # concessionária, construtora-HQ e LTDA genérico não viram morador (conservador)
    assert _eh_residencial("CAOA FORTALEZA") is False
    assert _eh_residencial("RODRIGO FURTADO CRUZ LTDA") is False
    assert _eh_residencial("GALPAO LOGISTICO X") is False
