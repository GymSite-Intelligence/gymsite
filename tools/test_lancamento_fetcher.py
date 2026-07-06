"""Task #11 (SPEC_REFINO_LANCAMENTO_DETERMINISTICO): refino determinístico da
Janela de Entrada. Fixtures inspiradas nas páginas reais auditadas (Like/apto.vc,
Sensia/MRV, BS Rubi/expoimovel). Valida: parser, gate por endereço, integração
(todas as obras refinadas; grounding só como fallback) e aderência v2 por preço."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf.html_builder import _aderencia_modelo
from tools.lancamento_fetcher import (
    _pagina_casa_obra,
    parse_pagina_lancamento,
    refinar_lancamento_deterministico,
)

_FIXTURE_LIKE = (
    "Like Residencial - Cocó, Fortaleza | Apto. Empreendimento da Colmeia na Rua "
    "Vilebaldo Aguiar, torre única com 88 unidades, apartamentos de 54 m² a 61 m² "
    "com 2 quartos. Previsão de entrega dezembro de 2026. Lazer completo com espaço "
    "fitness, piscina e coworking. A partir de R$ 519.000,00."
)


def test_parser_pagina_like():
    out = parse_pagina_lancamento(_FIXTURE_LIKE)
    assert out["unidades_exatas"] == 88
    assert out["areas_plantas"] == [54.0, 61.0]
    assert out["preco_base"]["min"] == 519000.0
    assert out["preco_base"]["fonte"] == "pagina_lancamento"
    assert out["previsao_entrega"] == "2026"
    assert out["amenidade_fitness"] is True
    assert out["tipologia"] == "residencial"


def test_parser_nao_inventa():
    out = parse_pagina_lancamento("Página institucional da construtora, sem ficha técnica.")
    assert "unidades_exatas" not in out
    assert "preco_base" not in out


def test_gate_por_endereco():
    obra = {"logradouro": "Rua Vilebaldo Aguiar", "cep": "60192105"}
    assert _pagina_casa_obra(_FIXTURE_LIKE, obra)
    assert not _pagina_casa_obra("Lançamento em outra rua qualquer da cidade", obra)
    assert _pagina_casa_obra("Empreendimento no CEP 60192-105, Fortaleza", obra)


def test_refino_completo_com_mocks():
    obra = {"nome": "SPE COLMEIA LIKE LTDA", "logradouro": "Rua Vilebaldo Aguiar",
            "numero_logradouro": "100", "bairro": "Cocó", "cidade": "Fortaleza"}
    out = refinar_lancamento_deterministico(
        obra,
        _buscar_fn=lambda o: [{"url": "https://apto.vc/like", "titulo": "Like Residencial - Cocó | Apto"}],
        _fetch_fn=lambda url: "<html><body>" + _FIXTURE_LIKE + " Sobre a Colmeia: "
        + "construtora com 45 anos de mercado em Fortaleza. " * 8 + "</body></html>",
    )
    assert out is not None
    assert out["unidades_exatas"] == 88
    assert out["confianca"] == "alta"
    assert out["metodo_match"] == "endereco_na_pagina"
    assert out["fonte_url"] == "https://apto.vc/like"
    assert out["empreendimento"].startswith("Like Residencial")


def test_refino_sem_match_retorna_none():
    obra = {"logradouro": "Av Inexistente", "bairro": "X", "cidade": "Y"}
    out = refinar_lancamento_deterministico(
        obra,
        _buscar_fn=lambda o: [{"url": "https://z", "titulo": "t"}],
        _fetch_fn=lambda url: "<html>" + "página que não cita o endereço da obra. " * 20 + "</html>",
    )
    assert out is None


def test_aderencia_v2_preco_rebaixa_e_confirma():
    assert _aderencia_modelo(191, 3_807_213) == ("BAIXA", "no")   # BS Rubi: preço decide
    assert _aderencia_modelo(110, 2_000_000) == ("BAIXA", "no")   # planta média, preço alto
    assert _aderencia_modelo(110, 450_000) == ("ALTA", "ok")      # planta média, preço popular
    assert _aderencia_modelo(54, 416_990) == ("ALTA", "ok")       # Sensia
    assert _aderencia_modelo(110, None) == ("MÉDIA", "mid")       # sem preço = régua antiga
    assert _aderencia_modelo(None, 400_000) == ("ALTA", "ok")     # só preço, popular
    assert _aderencia_modelo(None, None) == (None, None)
