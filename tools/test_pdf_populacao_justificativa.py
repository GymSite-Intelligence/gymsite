"""Regressão do PDF (bug 4b211a02): (a) célula População vazia quando o JSON traz a
população como string/float formatado; (b) selo INVIAVEL sem motivo. Valida _coerce_int
e a renderização de população, domicílios e justificativa no HTML do PDF."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf.html_builder import _coerce_int, gerar_html
from pdf.test_render_campos_v3 import _modelo_com_v3


def test_coerce_int_formatos():
    assert _coerce_int(60165) == 60165
    assert _coerce_int(60165.0) == 60165
    assert _coerce_int("60165") == 60165
    assert _coerce_int("60165.0") == 60165
    assert _coerce_int("60.165") == 60165
    assert _coerce_int("22.645,00") == 22645
    assert _coerce_int("1.234.567") == 1234567
    assert _coerce_int(None) is None
    assert _coerce_int("") is None
    assert _coerce_int("bairro") is None


def test_populacao_e_domicilios_renderizam():
    model = _modelo_com_v3()
    model.metadata["demografia_bairro"] = {
        "renda_media": 4953,
        "populacao": "60.165",
        "domicilios": 22645.0,
        "censo_n_setores": 105,
    }
    html = gerar_html(model)
    assert "60.165 hab" in html
    assert "105 setores (raio do centróide)" in html
    assert "22.645" in html


def test_justificativa_do_selo_renderiza():
    model = _modelo_com_v3()
    model.cenarios[0].justificativa = "Payback 172m inviável"
    html = gerar_html(model)
    assert "Payback 172m inviável" in html


def test_sem_justificativa_nao_quebra():
    model = _modelo_com_v3()
    model.cenarios[0].justificativa = None
    html = gerar_html(model)
    assert html
