"""Arquiteto P0 — COE municipal (João Pessoa / São Paulo) vs estimativa genérica."""
from __future__ import annotations

from tools.coe_sanitarios import calcular_sanitarios_municipio, municipios_cobertos


def test_municipios_seedados():
    nomes = {(m["municipio"], m["uf"]) for m in municipios_cobertos()}
    assert ("João Pessoa", "PB") in nomes
    assert ("São Paulo", "SP") in nomes


def test_jp_com_lotacao_pede_area_treino():
    """Caso do incidente: '200 alunos em João Pessoa' NÃO pode virar 10×50/50 oficial."""
    r = calcular_sanitarios_municipio("João Pessoa", "PB", lotacao=200)
    assert r["status"] == "precisa_area_treino"
    assert r["tipo"] == "coe_municipal"
    assert "367" in (r.get("citacao") or {}).get("base", "") + (r.get("aviso") or "")
    # não devolve cota simétrica como se fosse COE
    assert r.get("bacias_por_genero") is None
    assert r.get("bacias_total") is None
    # mas oferece a lente de planejamento pelo pico
    pico = r["estimativa_por_pico"]
    assert pico["tipo"] == "estimativa_nao_oficial"
    assert pico["papel"] == "planejamento_por_pico"
    assert pico["bacias_total"] == 10
    assert pico["bacias_por_genero"] == 5
    assert "LENTE_PICO_PLANEJAMENTO" in r["regras_aplicadas"]


def test_jp_area_mais_pico_traz_duas_lentes():
    r = calcular_sanitarios_municipio(
        "João Pessoa", "PB", lotacao=200, area_treino_m2=300,
    )
    assert r["status"] == "ok"
    assert r["bacias_femininas"] == 3  # COE
    assert r["estimativa_por_pico"]["bacias_total"] == 10  # planejamento


def test_municipio_nao_coberto_ainda_oferece_pico():
    r = calcular_sanitarios_municipio("Campina Grande", "PB", lotacao=200)
    assert r["status"] == "municipio_nao_coberto"
    assert r["estimativa_por_pico"]["bacias_total"] == 10


def test_jp_alias_jampa():
    r = calcular_sanitarios_municipio("Jampa", "PB", area_treino_m2=100)
    assert r["status"] == "ok"
    assert r["bacias_femininas"] == 1
    assert r["chuveiros_masculinos"] == 3


def test_jp_espectadores_paragrafo_unico():
    r = calcular_sanitarios_municipio("João Pessoa", "PB", espectadores=200)
    assert r["status"] == "ok"
    assert r["modo"] == "publico_espectadores"
    assert r["bacias_total"] == 2
    assert r["lavatorios_total"] == 4


def test_sp_lotacao_200_oficial():
    r = calcular_sanitarios_municipio("São Paulo", "SP", lotacao=200)
    assert r["status"] == "ok"
    assert r["bacias_femininas"] == 5
    assert r["bacias_masculinas"] == 5
    assert r["chuveiros_femininos"] == 5
    assert "16.642/2017" in r["citacao"]["fonte"]


def test_jp_por_area_treino_art_367():
    # 300 m² → 3 kits/sexo: 3 vasos, 9 chuveiros, 6 lavatórios; mictórios só M
    r = calcular_sanitarios_municipio("João Pessoa", uf="PB", area_treino_m2=300)
    assert r["status"] == "ok"
    assert r["bacias_femininas"] == 3
    assert r["bacias_masculinas"] == 3
    assert r["chuveiros_femininos"] == 9
    assert r["chuveiros_masculinos"] == 9
    assert r["lavatorios_femininos"] == 6
    assert r["mictorios_masculinos"] == 6
    assert r["assimetrico"] is True
    assert "Lei Municipal nº 1.347/1971" in r["citacao"]["fonte"]
    assert r["vestiario_m2_total_min"] == 30.0
    assert "estimativa_por_pico" not in r  # sem lotação, sem lente de pico


def test_wire_arquiteto_menciona_tool():
    from pathlib import Path

    agent = Path("agents_site/agent.py").read_text(encoding="utf-8")
    assert "calcular_sanitarios_municipio" in agent
    ce = Path("services/consultor/consultor_engine.py").read_text(encoding="utf-8")
    assert 'name="calcular_sanitarios_municipio"' in ce
    assert 'nome == "calcular_sanitarios_municipio"' in ce
