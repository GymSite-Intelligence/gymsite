"""Extrator real idade×sexo por BAIRRO: agrega setores mais próximos do centróide até a
pop-alvo, do espelho censo_setor_idade_sexo. Pirâmide real (sem viés do rateio %município)."""
from unittest.mock import MagicMock, patch

import tools.perfil_sexo_idade_tools as t


def _mock_sb(setores):
    res = MagicMock(); res.data = setores
    tbl = MagicMock()
    tbl.select.return_value = tbl
    tbl.eq.return_value = tbl
    tbl.execute.return_value = res
    sb = MagicMock(); sb.table.return_value = tbl
    return sb


def _setor(lat, lng, pess, h2539, m2539, h60, m60):
    return {"lat": lat, "lng": lng, "pessoas": pess, "h_total": h2539 + h60, "m_total": m2539 + m60,
            "h_15_24": 0, "m_15_24": 0, "h_25_39": h2539, "m_25_39": m2539,
            "h_40_59": 0, "m_40_59": 0, "h_60_mais": h60, "m_60_mais": m60}


def test_none_safe():
    assert t.perfil_sexo_idade_bairro(None, None, None, None) is None
    assert t.perfil_sexo_idade_bairro("2304400", -3.7, -38.4, None) is None
    assert t.perfil_sexo_idade_bairro("abc", -3.7, -38.4, 1000) is None


def test_agrega_setores_proximos_ate_pop():
    # 3 setores: 2 perto do centróide, 1 longe. pop_alvo=200 → pega os 2 perto.
    setores = [
        _setor(-3.741, -38.487, 120, 30, 34, 10, 16),   # perto
        _setor(-3.742, -38.488, 100, 20, 26, 8, 14),     # perto
        _setor(-3.900, -38.700, 500, 200, 200, 100, 100),  # longe (não entra)
    ]
    with patch("db.supabase_writer._get_client", return_value=_mock_sb(setores)):
        p = t.perfil_sexo_idade_bairro("2304400", -3.7415, -38.4875, 200)
    assert p is not None
    assert p["n_setores"] == 2                    # só os 2 próximos
    assert p["granularidade"].startswith("bairro")
    # 25-39 = (30+20)H / (34+26)M = 50/60 → 45.5/54.5
    assert p["pct_homens"] == 45.5 and p["pct_mulheres"] == 54.5
    # 60+ presente no segmento (idade real, não rateio)
    assert p["segmentos"]["60+"]["total"] == (10 + 16 + 8 + 14)


def test_sem_setores_retorna_none():
    with patch("db.supabase_writer._get_client", return_value=_mock_sb([])):
        assert t.perfil_sexo_idade_bairro("2304400", -3.7, -38.4, 1000) is None
