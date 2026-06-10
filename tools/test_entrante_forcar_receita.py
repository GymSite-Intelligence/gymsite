"""Enriquecimento manual força busca Receita mesmo com e-mail PJ já preenchido."""
from unittest.mock import patch

from tools.cnpj_enrichment import enriquecer_entrante_unico


@patch("tools.cnpj_enrichment.fetch_cartao_cnpj")
def test_manual_forcar_receita_chama_receita(mock_fetch):
    mock_fetch.return_value = {
        "status": "ok",
        "fonte": "receitaws",
        "razao_social": "DREAM LIFE LTDA",
        "nome_fantasia": "DREAMLIFE CT",
        "email": "pj@example.com",
        "telefone": "85999999999",
        "qsa": [{"nome": "João", "qualificacao": "49-Socio-Administrador"}],
        "socio_administrador": {
            "nome": "João",
            "qualificacao": "49-Socio-Administrador",
            "email_direto": "joao@example.com",
            "linkedin_url": "https://linkedin.com/in/joao",
        },
    }
    ent = {
        "cnpj": "66649755000120",
        "razao_social": None,
        "email_empresa": "DREAMLIFECROSS2021@GMAIL.COM",
        "telefone_empresa": "8596600952",
    }
    out, meta = enriquecer_entrante_unico(ent, forcar_receita=True, usar_apollo=False)
    mock_fetch.assert_called_once()
    assert meta["receita_chamadas"] == 1
    assert out.get("razao_social") == "DREAM LIFE LTDA"
    assert out.get("email_socio_administrador") == "joao@example.com"
