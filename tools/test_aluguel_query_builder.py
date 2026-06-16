"""Query builder do tier-1b de aluguel: bairro-específico PRIMEIRO (snippets c/
preço+área), depois cidade-inteira. Sem bairro = comportamento antigo (só cidade)."""
from tools.aluguel_municipio_portais import _build_queries_aluguel


def test_sem_bairro_so_cidade():
    qs = [q for q, _ in _build_queries_aluguel("Fortaleza")]
    assert all("Fortaleza" in q for q in qs)
    assert all(q.endswith("Fortaleza") for q in qs)  # nada de bairro pendurado
    # 4 portais x 3 termos
    assert len(qs) == 12


def test_bairro_vem_primeiro():
    qs = [q for q, _ in _build_queries_aluguel("Fortaleza", "Cocó")]
    # primeira metade carrega o bairro; o cap=8 corta dentro dela -> 100% bairro
    primeira = qs[:12]
    assert all("Cocó Fortaleza" in q for q in primeira)
    # depois, a rodada cidade-inteira (sem bairro)
    segunda = qs[12:]
    assert all("Cocó" not in q for q in segunda)
    assert len(qs) == 24


def test_dentro_do_cap_8_tudo_bairro():
    qs = [q for q, _ in _build_queries_aluguel("Fortaleza", "Aldeota")][:8]
    assert all("Aldeota Fortaleza" in q for q in qs)
