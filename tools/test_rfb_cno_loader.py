"""Testes do loader CNO fresco (RFB bulk) — parse + classificação, sem rede."""
from __future__ import annotations

from tools.rfb_cno_loader import _sniff_delim, classificar

# Header CNO (RFB, latin-1, ';'). Nomes batem com cno_fitness_tools._map_headers.
# ASCII como _map_headers (cno_fitness_tools) casa no extract real.
_HEADER = ("CNO;CEP;Nome;Area total;Codigo do municipio;CNPJ responsavel;"
           "Logradouro;Numero do logradouro;Bairro;Data de inicio;Situacao;Data da situacao")

_ROWS = [
    # fitness por keyword (área na faixa, em curso)
    "1;60160000;ACADEMIA SMART FIT MEIRELES;800;1389;11111111000111;Av X;100;Meireles;2025-01-01;01;",
    # grande porte residencial (área>2000, em curso, não-fitness, não-comercial)
    "2;60170000;EDIFICIO RESIDENCIAL AURORA;6000;1389;22222222000122;Rua Y;200;Aldeota;2025-03-01;02;",
    # comercial óbvio (excluído do grande porte)
    "3;60175000;GALPAO LOGISTICO NORDESTE;7000;1389;33333333000133;Rod Z;0;Distrito;2025-02-01;01;",
    # pequena (fora da faixa grande porte e sem keyword fitness)
    "4;60180000;CASA DA FAMILIA SILVA;120;1389;;Rua W;50;Centro;2024-01-01;01;",
    # encerrada grande porte (não em_curso → fora do grande porte)
    "5;60181000;CONDOMINIO PARQUE VERDE;5000;1389;44444444000144;Av K;10;Cocó;2018-01-01;15;2021-01-01",
]


def _escrever_cno(tmp_path):
    d = tmp_path / "cno_extract"
    d.mkdir()
    (d / "cno.csv").write_text("\n".join([_HEADER, *_ROWS]), encoding="latin-1")
    return d


def test_sniff_delim():
    assert _sniff_delim("a;b;c") == ";"
    assert _sniff_delim("a,b,c") == ","


def test_classifica_fitness_e_grande_porte(tmp_path):
    d = _escrever_cno(tmp_path)
    res = classificar(d)
    ids_fit = {r["id_cno"] for r in res["fitness"]}
    ids_gp = {r["id_cno"] for r in res["grande_porte"]}
    assert ids_fit == {"1"}                 # só a academia
    assert ids_gp == {"2"}                  # só o residencial em curso na faixa
    assert "3" not in ids_gp                # galpão comercial excluído
    assert "4" not in ids_gp                # pequena fora da faixa
    assert "5" not in ids_gp                # encerrada (não em_curso)


def test_grande_porte_mapeia_campos(tmp_path):
    d = _escrever_cno(tmp_path)
    gp = {r["id_cno"]: r for r in classificar(d)["grande_porte"]}["2"]
    assert gp["area_m2"] == 6000.0
    assert gp["id_municipio_rf"] == "1389"
    assert gp["em_curso"] is True
    assert gp["bairro"] == "Aldeota"
    assert gp["fonte"] == "dadosabertos.rfb.gov.br/CNO"


def test_fitness_carrega_metodo(tmp_path):
    d = _escrever_cno(tmp_path)
    fit = classificar(d)["fitness"][0]
    assert fit["metodo_classificacao"] == "keyword"
    assert fit["id_cno"] == "1"
