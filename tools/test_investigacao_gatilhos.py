"""Testes unitários — gatilhos de investigação (sem API)."""
from tools.deep_research_tool import (
    _extrair_json_investigacao,
    _investigacao_id,
    marcar_gatilhos_investigacao,
)
from tools.investigacao_context import (
    build_contexto_investigacao,
    inferir_tipo_imovel_candidato,
)


def test_marcar_listing_dispara_prioridade_1():
    candidatos = [
        {
            "qualidade_sinal": "direto-listing",
            "endereco": "Rua X, 100",
            "listing_url": "https://ce.olx.com.br/imovel-123",
        }
    ]
    out = marcar_gatilhos_investigacao(candidatos)
    inv = out[0]["investigacao"]
    assert inv["disparar"] is True
    assert inv["prioridade"] == 1


def test_marcar_fechado_dispara_prioridade_2():
    candidatos = [
        {
            "qualidade_sinal": "indireto-heuristico",
            "endereco": "Av. Y, 50",
            "business_status": "CLOSED_PERMANENTLY",
            "motivo": "Loja — investigar",
            "score_geoscout": 5,
        }
    ]
    out = marcar_gatilhos_investigacao(candidatos)
    assert out[0]["investigacao"]["disparar"] is True
    assert out[0]["investigacao"]["prioridade"] == 2


def test_marcar_sem_endereco_nao_dispara():
    candidatos = [{"qualidade_sinal": "indireto-heuristico", "motivo": "investigar"}]
    out = marcar_gatilhos_investigacao(candidatos)
    assert out[0]["investigacao"]["disparar"] is False


def test_extrair_json_investigacao():
    texto = 'Resumo\n```json\n{"status_operacao": "vago", "confianca": "media"}\n```'
    parsed = _extrair_json_investigacao(texto)
    assert parsed["status_operacao"] == "vago"


def test_investigacao_id_estavel():
    c = {"listing_id": "3032295652", "endereco": "Centro, Fortaleza"}
    assert _investigacao_id(c) == _investigacao_id(c)


def test_contexto_input_params_meireles():
    ctx = build_contexto_investigacao(
        {
            "cidade": "Fortaleza",
            "bairro": "Meireles",
            "uf": "CE",
            "area_m2_min": 800,
            "area_m2_max": 1500,
            "tamanho_preset": "m",
            "tipo_negocio": "academia",
        }
    )
    assert ctx["area_m2_min"] == 800
    assert ctx["faixa_porte_preset"] == "media"
    assert ctx["projecao_preset_referencia"]["status"] == "ok"


def test_inferir_galpao():
    t = inferir_tipo_imovel_candidato({"nome": "Galpão comercial 1200m2 OLX"})
    assert t["tipo_imovel_codigo_onr"] == 31


if __name__ == "__main__":
    test_marcar_listing_dispara_prioridade_1()
    test_marcar_fechado_dispara_prioridade_2()
    test_marcar_sem_endereco_nao_dispara()
    test_extrair_json_investigacao()
    test_investigacao_id_estavel()
    test_contexto_input_params_meireles()
    test_inferir_galpao()
    print("ok")
