# tools/test_matriz_demo_saturacao.py
from tools.matriz_demo_saturacao import (
    classificar_tier_concorrente,
    contar_mix,
    matriz_demo_saturacao,
)


def test_smart_fit_is_low():
    assert classificar_tier_concorrente({"nome": "Smart Fit Cocó"}) == "low"


def test_bodytech_is_premium():
    assert classificar_tier_concorrente({"nome": "Bodytech Aldeota"}) == "premium"


def test_ticket_mid_band():
    assert classificar_tier_concorrente({"nome": "Academia X", "ticket_medio": 189}) == "mid"


def test_contar_mix():
    cs = [
        {"nome": "Smart Fit"},
        {"nome": "Bodytech"},
        {"nome": "Bodytech 2"},
        {"nome": "Local", "ticket_medio": 180},
    ]
    m = contar_mix(cs)
    assert m["low"] == 1 and m["premium"] == 2 and m["mid"] == 1


def test_oceano_azul_alta_renda_sem_premium():
    r = matriz_demo_saturacao(
        populacao=50000, renda_percentil=0.9,
        concorrentes=[{"nome": "Smart Fit", "rating": 3.5}],
        fonte_espacial="poligono_ibge_bairro",
    )
    assert r["quadrante"] == "Oceano Azul"
    assert "premium" in r["modelo_sugerido"].lower() or "mid" in r["modelo_sugerido"].lower()


def test_armadilha_dois_premium():
    r = matriz_demo_saturacao(
        populacao=50000, renda_percentil=0.9,
        concorrentes=[{"nome": "Bodytech"}, {"nome": "Bio Ritmo"}, {"nome": "Smart Fit"}],
        fonte_espacial="poligono_ibge_bairro",
    )
    assert r["quadrante"] == "Armadilha de Renda"
    assert "premium" not in r["modelo_sugerido"].lower() or "nicho" in r["modelo_sugerido"].lower()


def test_n_per_10k():
    r = matriz_demo_saturacao(
        populacao=10000, renda_pc=2000,
        concorrentes=[{"nome": "A"}, {"nome": "B"}],
    )
    assert r["n_per_10k"] == 2.0


def test_baixas_24m_forca_deserto():
    r = matriz_demo_saturacao(
        populacao=50000, renda_pc=2000,
        concorrentes=[{"nome": "Local X"}],
        baixas_24m=4,
    )
    assert r["quadrante"] == "Deserto Viável"
    assert r["red_flag_rotatividade"] is True


def test_rede_ancora_com_um_premium_vira_armadilha():
    r = matriz_demo_saturacao(
        populacao=50000, renda_percentil=0.9,
        concorrentes=[{"nome": "Bodytech"}],
        rede_ancora=True,
    )
    assert r["quadrante"] == "Armadilha de Renda"
