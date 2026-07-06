"""Task #10 (auditoria Gemini): coluna de aderência ao modelo na tabela de
empreendimentos T+24 — classificação determinística pela planta média."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf.html_builder import _aderencia_modelo, gerar_html
from pdf.test_render_campos_v3 import _modelo_com_v3


def test_classificacao_por_planta():
    assert _aderencia_modelo(54) == ("ALTA", "ok")       # Sensia/Like (compacto)
    assert _aderencia_modelo(66.0) == ("ALTA", "ok")     # Mood
    assert _aderencia_modelo(110) == ("MÉDIA", "mid")
    assert _aderencia_modelo(191) == ("BAIXA", "no")     # BS Rubi (ultra-premium)
    assert _aderencia_modelo(228) == ("BAIXA", "no")     # Casa Monã
    assert _aderencia_modelo(None) == (None, None)
    assert _aderencia_modelo("—") == (None, None)
    assert _aderencia_modelo(0) == (None, None)


def test_coluna_renderiza_no_pdf():
    model = _modelo_com_v3()
    model.metadata["demanda_futura"] = {
        "status": "ok", "provavel_residencial_n": 2,
        "captura_total_est": 34, "receita_total_mensal_est": 5978,
        "moradores_total_est": 2292,
        "obras": [
            {"provavel_residencial": True, "empreendimento": "Mood Parque do Cocó",
             "area_privativa_media": 66.0, "unidades_est": 245,
             "unidades_fonte": "lancamento_exato", "entrega": "2027-12"},
            {"provavel_residencial": True, "empreendimento": "BS Rubi",
             "area_privativa_media": 191.0, "unidades_est": 66,
             "unidades_fonte": "lancamento_exato", "entrega": "2028-05"},
        ],
    }
    html = gerar_html(model)
    assert "Aderência" in html
    assert "ALTA" in html and "BAIXA" in html
    assert "alvo primário" in html  # nota de metodologia com a régua explícita
