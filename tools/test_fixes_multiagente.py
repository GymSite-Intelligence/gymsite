"""Fixes do cross-audit multiagente:
1. filtro concorrente autoritativo (bairro por nome/endereço — não bairro_concorrente
   corrompido; tipo off-type fora).
2. renderer determinístico da demanda futura (markdown, só residencial real).
(gancho = espelho Supabase, testado ao vivo; rede, fora do unit.)"""
from tools.competitor_tools import filtrar_concorrentes_bairro_tipo


_CONCS = [
    {"nome": "Academia Smart Fit - Papicu", "endereco": "Av Z - Papicu, Fortaleza", "tipos": ["Academia", "gym"]},
    {"nome": "Eiko Artes Marciais", "endereco": "R X - Coco", "tipos": ["Artes marciais"]},
    {"nome": "Academia VS Club - coco/ Musculacao", "endereco": "R Y - Coco", "tipos": ["Academia", "gym"]},
    {"nome": "Complexo REK CrossFit", "endereco": "R W - Coco", "tipos": ["Academia de crossfit", "gym"]},
    {"nome": "Parque Esportes", "endereco": "Lojas - Coco", "tipos": ["Academia", "gym"]},
    {"nome": "Selfit Academia", "endereco": "R V - Meireles", "tipos": ["Academia", "gym"]},
]


def test_filtro_dropa_vizinho_e_offtype():
    out = filtrar_concorrentes_bairro_tipo(_CONCS, bairro="Cocó", tipo_negocio="academia")
    nomes = [c["nome"] for c in out]
    assert "Academia VS Club - coco/ Musculacao" in nomes
    assert "Parque Esportes" in nomes
    # vizinhos (Papicu/Meireles) e off-type (crossfit/luta) fora
    assert not any("Papicu" in n for n in nomes)
    assert not any("Selfit" in n for n in nomes)
    assert not any("REK" in n for n in nomes)
    assert not any("Artes Marciais" in n for n in nomes)


def test_filtro_nao_confia_bairro_concorrente_corrompido():
    # Smart Fit com bairro_concorrente='Cocó' MENTIROSO (é Papicu) → ainda dropa pelo nome/endereço
    concs = [
        {"nome": "Smart Fit - Papicu", "endereco": "Av - Papicu", "bairro_concorrente": "Cocó", "tipos": ["Academia", "gym"]},
        {"nome": "VS Club", "endereco": "R - Cocó", "tipos": ["Academia", "gym"]},
        {"nome": "Parque", "endereco": "R - Cocó", "tipos": ["Academia", "gym"]},
    ]
    out = filtrar_concorrentes_bairro_tipo(concs, bairro="Cocó", tipo_negocio="academia")
    assert not any("Papicu" in c["nome"] for c in out)


def test_filtro_salvaguarda_zero_no_bairro():
    # se NINGUÉM casa o bairro → mantém todos (esparso > vazio)
    concs = [{"nome": "X", "endereco": "Papicu", "tipos": ["Academia"]},
             {"nome": "Y", "endereco": "Aldeota", "tipos": ["Academia"]}]
    out = filtrar_concorrentes_bairro_tipo(concs, bairro="Cocó", tipo_negocio="academia")
    assert len(out) == 2


def test_demanda_renderer():
    from agents.a6_report_consolidator import _renderizar_md_demanda_futura
    df = {"status": "ok", "provavel_residencial_n": 6, "moradores_total_est": 2879,
          "captura_total_est": 43, "receita_total_mensal_est": 6048,
          "obras": [{"provavel_residencial": True, "construtora": "SPE COCO 01", "bairro": "Coco",
                     "unidades_est": 320, "moradores_est": 938, "entrega": "2028-02"},
                    {"provavel_residencial": False, "construtora": "CAOA"}]}
    s = _renderizar_md_demanda_futura(df)
    assert "Demanda Futura" in s and "2.879" in s
    assert "SPE COCO 01" in s and "CAOA" not in s          # só residencial na tabela
    assert _renderizar_md_demanda_futura({"status": "ok", "provavel_residencial_n": 0}) == ""
    assert _renderizar_md_demanda_futura({"status": "sem_dados"}) == ""
