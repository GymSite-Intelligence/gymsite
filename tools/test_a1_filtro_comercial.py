"""RN-A1-09..11: filtro comercial de candidatos."""

from tools.a1_listing_pipeline import filtrar_candidatos_comerciais


def test_remove_venda_por_modalidade():
    cands = [
        {"nome": "Ponto comercial 900m2", "modalidade": "locacao", "area_m2": 900},
        {"nome": "Sala comercial", "modalidade": "venda", "area_m2": 950},
    ]
    out, stats = filtrar_candidatos_comerciais(cands, 800, 1200)
    assert len(out) == 1
    assert stats["venda"] == 1


def test_remove_venda_por_nome():
    cands = [
        {"nome": "Apartamento à venda 3 quartos", "modalidade": "locacao", "area_m2": 900},
        {"nome": "Loja comercial 1000 m2", "modalidade": "locacao", "area_m2": 1000},
    ]
    out, stats = filtrar_candidatos_comerciais(cands, 800, 1200)
    assert len(out) == 1
    assert "Loja" in out[0]["nome"]
    assert stats["venda"] >= 1 or stats["residencial"] >= 1


def test_remove_residencial():
    cands = [
        {"nome": "Apartamento residencial amplo", "modalidade": "locacao", "area_m2": 900},
        {"nome": "Galpão comercial", "modalidade": "locacao", "area_m2": 1000},
    ]
    out, stats = filtrar_candidatos_comerciais(cands, 800, 1200)
    assert len(out) == 1
    assert stats["residencial"] == 1


def test_remove_area_fora_faixa():
    cands = [
        {"nome": "Loja pequena", "modalidade": "locacao", "area_m2": 5},
        {"nome": "Galpão ok", "modalidade": "locacao", "area_m2": 1000},
        {"nome": "Shopping enorme", "modalidade": "locacao", "area_m2": 9000},
    ]
    out, stats = filtrar_candidatos_comerciais(cands, 800, 1200)
    assert len(out) == 1
    assert out[0]["area_m2"] == 1000
    assert stats["area"] == 2


def test_todos_removidos_stats():
    cands = [
        {"nome": "Casa à venda", "modalidade": "venda", "area_m2": 50},
    ]
    out, stats = filtrar_candidatos_comerciais(cands, 800, 1200)
    assert out == []
    assert stats["total"] == 1
