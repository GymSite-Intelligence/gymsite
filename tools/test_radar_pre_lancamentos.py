"""Task #12: radar de pré-lançamentos (venda sem CNO). Regras validadas: dedupe
contra o CNO, gate do bairro na página, fora_dos_totais SEMPRE, e a demanda_futura
não soma o radar nos totais."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.lancamento_fetcher import radar_pre_lancamentos

_PAGINA_NOVA = (
    "<html><body>Breve lançamento no Cocó, Fortaleza: Residencial Aurora do Parque, "
    "torre única com 120 unidades, apartamentos de 58 m² a 75 m², 2 e 3 quartos. "
    "A partir de R$ 489.000,00. Previsão de conclusão 2028. Lazer com piscina e academia. "
    + "Localização privilegiada ao lado do Parque do Cocó. " * 12 + "</body></html>"
)
_PAGINA_JA_NO_CNO = (
    "<html><body>Mood Parque do Cocó — 245 unidades de 55 m² à 77 m² no Cocó, Fortaleza. "
    + "Um novo jeito de morar. " * 30 + "</body></html>"
)


def _buscar(q):
    return [
        {"url": "https://portal/aurora", "titulo": "Residencial Aurora do Parque - Cocó"},
        {"url": "https://portal/mood", "titulo": "Mood Parque do Cocó - lançamento"},
    ]


def _fetch(url):
    return _PAGINA_NOVA if "aurora" in url else _PAGINA_JA_NO_CNO


def test_radar_descobre_e_deduplica_cno():
    obras_cno = [{"nome": "SPE X", "empreendimento": "Mood Parque do Cocó",
                  "logradouro": "Av Y"}]
    radar = radar_pre_lancamentos("Cocó", "Fortaleza", obras_cno=obras_cno,
                                  _buscar_fn=_buscar, _fetch_fn=_fetch)
    nomes = [r["empreendimento"] for r in radar]
    assert any("Aurora" in n for n in nomes)
    assert not any("Mood" in n for n in nomes)  # já está no CNO → fora do radar
    item = radar[0]
    assert item["fora_dos_totais"] is True
    assert item["unidades_est"] == 120
    assert item["preco_base"]["min"] == 489000.0
    assert "não soma demanda" in item["motivo"]


def test_radar_gate_bairro():
    radar = radar_pre_lancamentos("Meireles", "Fortaleza", obras_cno=[],
                                  _buscar_fn=_buscar, _fetch_fn=_fetch)
    assert radar == []  # páginas citam Cocó, não Meireles


def test_radar_fail_soft():
    assert radar_pre_lancamentos("", "Fortaleza") == []
    assert radar_pre_lancamentos("Cocó", "Fortaleza",
                                 _buscar_fn=lambda q: (_ for _ in ()).throw(RuntimeError),
                                 _fetch_fn=_fetch) == []
