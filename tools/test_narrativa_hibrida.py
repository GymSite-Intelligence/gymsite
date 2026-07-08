"""Task #20 (relatório híbrido): narrativa executiva determinística fechando cada
seção do PDF — mesmos números das tabelas, com carimbo de base/fonte, zero LLM."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf.html_builder import gerar_html
from pdf.test_render_campos_v3 import _modelo_com_v3


def test_narrativa_demografia_e_financeira():
    model = _modelo_com_v3()
    model.metadata["demografia_bairro"] = {
        "renda_media": 4953, "populacao": 60165, "domicilios": 22645,
        "censo_n_setores": 105,
    }
    html = gerar_html(model)
    assert "Leitura executiva" in html
    assert "60.165 hab" in html
    assert "IBGE Censo 2022 por setor censitário" in html
    # financeira: o fixture tem cenário Premium INVIAVEL → narrativa cita reprovação
    assert "cenários reprovaram" in html or "Nenhum cenário atingiu" in html
    assert "validar em due diligence" in html


def test_narrativa_demanda():
    model = _modelo_com_v3()
    model.metadata["demanda_futura"] = {
        "status": "ok", "provavel_residencial_n": 2,
        "captura_total_est": 34, "receita_total_mensal_est": 5978,
        "moradores_total_est": 2292,
        "obras": [{"provavel_residencial": True, "empreendimento": "Mood",
                   "area_privativa_media": 66.0, "unidades_est": 245,
                   "unidades_fonte": "lancamento_exato", "entrega": "2027-12"}],
        "radar_pre_lancamentos": [{"empreendimento": "Aurora", "unidades_est": 120}],
    }
    html = gerar_html(model)
    assert "registro CNO no horizonte T+24" in html
    assert "pré-lançamento(s) sem CNO" in html


def test_sem_dados_sem_narrativa_quebrada():
    model = _modelo_com_v3()
    html = gerar_html(model)
    assert "população não disponível" not in html  # sem demografia → sem narrativa dela
    assert html  # renderiza sem exceção
