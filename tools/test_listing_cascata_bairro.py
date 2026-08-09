"""Testes determinísticos para listing_cascata.py:
  - extrair_bairro_anuncio: extração de bairro do título OLX
  - filtrar_por_bairro: filtra candidatos pelo bairro alvo (sem rede real)

Todos os casos de filtrar_por_bairro usam monkeypatch para
nominatim_geocode, evitando qualquer chamada HTTP.
"""
import pytest
from tools.listing_cascata import extrair_bairro_anuncio, filtrar_por_bairro


# ── extrair_bairro_anuncio ─────────────────────────────────────────────────

def test_extrair_bairro_formato_olx_tipico():
    """Título padrão OLX 'Tipo - Bairro, Cidade - UF ...' → retorna bairro."""
    bairro = extrair_bairro_anuncio("Apartamento à venda - Meireles, Fortaleza - CE 123")
    assert bairro == "Meireles"


def test_extrair_bairro_com_nome_composto_sem_abreviacao():
    """Bairro com espaço sem abreviações é extraído normalmente."""
    bairro = extrair_bairro_anuncio("Galpao comercial - Luciano Cavalcante, Fortaleza")
    assert bairro is not None
    assert "Cavalcante" in bairro or "Luciano" in bairro


def test_extrair_bairro_abreviacao_ponto_capturado():
    """Bairro com abreviação 'Eng.' AGORA é capturado (regex inclui '.'). Pega a classe
    do vazamento Eng. Luciano Cavalcante num relatório de Cocó."""
    bairro = extrair_bairro_anuncio("Galpão comercial - Eng. Luciano Cavalcante, Fortaleza")
    assert bairro is not None
    assert "Luciano Cavalcante" in bairro
    assert not bairro.endswith(".")


def test_extrair_bairro_titulo_sem_padrao_retorna_none():
    """Título sem separador ' - ' seguido de vírgula → retorna None."""
    bairro = extrair_bairro_anuncio("Imóvel disponível para locação em Fortaleza")
    assert bairro is None


def test_extrair_bairro_nao_captura_tipo_imovel():
    """Capturas óbvias de tipo ('Apartamento', 'Sala') NÃO são retornadas."""
    # O regex captura antes da vírgula — mas se capturar "Apartamento" é descartado
    bairro = extrair_bairro_anuncio("Apartamento - Apartamento, Fortaleza - CE")
    # 'Apartamento' deve ser filtrado; pode retornar None
    assert bairro != "Apartamento"


def test_extrair_bairro_titulo_vazio_retorna_none():
    bairro = extrair_bairro_anuncio("")
    assert bairro is None


def test_extrair_bairro_sem_virgula_retorna_none():
    """Sem vírgula após o bairro, o padrão não casa."""
    bairro = extrair_bairro_anuncio("Galpão - Cocó")
    assert bairro is None


# ── filtrar_por_bairro ─────────────────────────────────────────────────────

def _make_candidato(titulo: str, snippet: str = "", endereco: str | None = None) -> dict:
    return {
        "titulo": titulo,
        "snippet": snippet,
        "endereco": endereco,
        "area_m2": 300,
        "preco": 5000.0,
        "fonte": "SearchAPI_OLX",
        "url": "https://ce.olx.com.br/imoveis/comercial/123",
        "latitude": None,
        "longitude": None,
    }


def _geocode_fake_coco(consulta: str) -> dict | None:
    """Retorna coordenadas fixas de Cocó independente da consulta."""
    return {
        "lat": -3.7380,
        "lon": -38.4946,
        "display_name": "Cocó, Fortaleza, CE",
        "address": {
            "suburb": "Cocó",
            "city": "Fortaleza",
        },
    }


def _geocode_fake_meireles(consulta: str) -> dict | None:
    """Simula geocode de um endereço no Meireles — bairro DIFERENTE do alvo."""
    return {
        "lat": -3.7256,
        "lon": -38.5075,
        "display_name": "Meireles, Fortaleza, CE",
        "address": {
            "suburb": "Meireles",
            "city": "Fortaleza",
        },
    }


def _geocode_none(_consulta: str) -> None:
    """Simula falha de geocode (sem resposta)."""
    return None


def test_filtrar_candidato_no_bairro_alvo_passa(monkeypatch):
    """Candidato com bairro alvo no título e geocode confirmando → mantido."""
    # nominatim_geocode é importado DENTRO de filtrar_por_bairro com `from` —
    # o patch deve ser no módulo de origem, não em listing_cascata.
    monkeypatch.setattr(
        "tools.nominatim_geocoder.nominatim_geocode",
        _geocode_fake_coco,
    )
    monkeypatch.setattr(
        "tools.parametros_metodologia.param",
        lambda _k: 2.0,
    )

    cand = _make_candidato("Galpao comercial - Coco, Fortaleza - CE")
    resultado = filtrar_por_bairro([cand], "Fortaleza", "Coco", "CE")
    assert len(resultado) == 1
    assert resultado[0]["titulo"] == cand["titulo"]


def test_filtrar_candidato_bairro_diferente_e_dropado(monkeypatch):
    """Candidato cujo título OLX tem bairro != alvo → dropado antes do geocode."""
    geocode_chamado = {"n": 0}

    def _geocode_rastreado(consulta: str):
        geocode_chamado["n"] += 1
        return _geocode_fake_coco(consulta)

    monkeypatch.setattr(
        "tools.nominatim_geocoder.nominatim_geocode",
        _geocode_rastreado,
    )
    monkeypatch.setattr(
        "tools.parametros_metodologia.param",
        lambda _k: 2.0,
    )

    # Candidato com bairro "Meireles" no título numa busca por "Coco"
    cand = _make_candidato("Sala comercial - Meireles, Fortaleza - CE")
    resultado = filtrar_por_bairro([cand], "Fortaleza", "Coco", "CE")

    assert len(resultado) == 0
    assert cand.get("descarte_motivo") is not None
    assert "Meireles" in cand["descarte_motivo"]


def test_filtrar_candidato_geocode_bairro_errado_dropado(monkeypatch):
    """Candidato sem bairro no título, mas geocode retorna suburb != alvo → dropado."""
    call_count = {"n": 0}

    def _geocode_sequencial(consulta: str):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # 1a chamada = centroide do bairro alvo (Coco)
            return _geocode_fake_coco(consulta)
        # demais = endereco do candidato (Meireles)
        return _geocode_fake_meireles(consulta)

    monkeypatch.setattr(
        "tools.nominatim_geocoder.nominatim_geocode",
        _geocode_sequencial,
    )
    monkeypatch.setattr(
        "tools.parametros_metodologia.param",
        lambda _k: 2.0,
    )

    # Sem bairro no titulo -> passa fase 1, vai ao geocode
    cand = _make_candidato("Galpao amplo para alugar, otima localizacao")
    resultado = filtrar_por_bairro([cand], "Fortaleza", "Coco", "CE")

    assert len(resultado) == 0
    assert cand.get("descarte_motivo") is not None


def test_filtrar_sem_endereco_nem_bairro_nao_geocoda_no_centroide(monkeypatch):
    chamadas = {"n": 0}

    def _geocode(consulta: str):
        chamadas["n"] += 1
        return _geocode_fake_coco(consulta)

    monkeypatch.setattr(
        "tools.nominatim_geocoder.nominatim_geocode",
        _geocode,
    )
    monkeypatch.setattr(
        "tools.parametros_metodologia.param",
        lambda _k: 2.0,
    )
    candidate = _make_candidato("Imóvel comercial amplo")

    result = filtrar_por_bairro([candidate], "Fortaleza", "Coco", "CE")

    assert result == []
    assert chamadas["n"] == 1
    assert "endereço" in candidate["descarte_motivo"]


def test_filtrar_candidato_sem_endereco_e_geocode_falha_dropado(monkeypatch):
    """Quando geocode retorna None, candidato e mantido (benefit of doubt)."""
    call_count = {"n": 0}

    def _geocode_sequencial(consulta: str):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # centroide do bairro alvo
            return _geocode_fake_coco(consulta)
        # candidato sem geocode
        return None

    monkeypatch.setattr(
        "tools.nominatim_geocoder.nominatim_geocode",
        _geocode_sequencial,
    )
    monkeypatch.setattr(
        "tools.parametros_metodologia.param",
        lambda _k: 2.0,
    )

    cand = _make_candidato("Imovel comercial disponivel")
    resultado = filtrar_por_bairro([cand], "Fortaleza", "Coco", "CE")

    assert resultado == []
    assert cand.get("descarte_motivo")


def test_filtrar_lista_vazia_retorna_vazia(monkeypatch):
    """Lista vazia de candidatos → retorna vazia sem erros."""
    monkeypatch.setattr(
        "tools.nominatim_geocoder.nominatim_geocode",
        _geocode_fake_coco,
    )
    monkeypatch.setattr(
        "tools.parametros_metodologia.param",
        lambda _k: 2.0,
    )
    resultado = filtrar_por_bairro([], "Fortaleza", "Coco", "CE")
    assert resultado == []


def test_filtrar_bairro_vazio_retorna_todos(monkeypatch):
    """Quando bairro alvo e vazio string, retorna todos sem filtrar."""
    monkeypatch.setattr(
        "tools.nominatim_geocoder.nominatim_geocode",
        _geocode_none,
    )
    monkeypatch.setattr(
        "tools.parametros_metodologia.param",
        lambda _k: 2.0,
    )
    cands = [
        _make_candidato("Sala comercial - Meireles, Fortaleza - CE"),
        _make_candidato("Galpao - Coco, Fortaleza"),
    ]
    resultado = filtrar_por_bairro(cands, "Fortaleza", "", "CE")
    assert len(resultado) == 2
