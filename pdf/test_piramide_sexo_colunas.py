"""Pirâmide idade×sexo: colunas Mulheres/Homens em quantidade (hab)."""
from pdf.html_builder import _piramide


def test_piramide_colunas_mulheres_homens_absolutos():
    demo = {
        "perfil_idade_sexo_bairro": {
            "n_setores": 105,
            "segmentos": {
                "25-39": {"total": 18420, "pct_mulheres": 53, "pct_homens": 47},
                "40-59": {"total": 12100, "pct_mulheres": 52, "pct_homens": 48},
            },
        }
    }
    out = _piramide(demo)
    assert out is not None
    row = out["piramide"][0]
    assert row["faixa"] == "25-39"
    assert row["total"] == "18.420"
    assert row["mulheres"] == "9.763"  # round(18420 * 0.53)
    assert row["homens"] == "8.657"  # 18420 - 9763
    assert row["pct_m"] == 53
    assert row["pct_h"] == 47
