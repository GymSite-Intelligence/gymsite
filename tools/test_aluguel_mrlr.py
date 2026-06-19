"""Aluguel MRLR determinístico (#audit divergência): padrão da renda + degrada limpo."""
from tools.aluguel_mrlr import _padrao_de_renda, aluguel_deterministico


def test_padrao_de_renda():
    assert _padrao_de_renda(0.99) == 3   # top renda → padrão alto
    assert _padrao_de_renda(0.5) == 2    # meio → normal
    assert _padrao_de_renda(0.1) == 1    # base → baixo
    assert _padrao_de_renda(None) == 2   # sem dado → normal


def test_degrada_sem_supabase(monkeypatch):
    monkeypatch.setattr("tools.aluguel_mrlr._sb", lambda: None)
    r = aluguel_deterministico(area_m2=1000, cidade="X", bairro="Y")
    assert r["status"] == "indisponivel"


def test_degrada_area_zero():
    r = aluguel_deterministico(area_m2=0, cidade="X", bairro="Y")
    assert r["status"] == "indisponivel"
