"""Regressão do portão CNAE da família fitness (joio vs trigo).

Decisão (validada com dado RFB/CE): a fonte da verdade do que É academia é a
ATIVIDADE registrada (cnae_principal ∈ grupo 931), não o nome. Sem o portão,
~33-36% do parque era joio — fisioterapia/hotel/salão/varejo com nome "fit"
caíam em academia pelo default. O nome só separa o TIPO DENTRO da família.

Família travada: 9311500/501, 9313100, 9319101/2/3/199.
FORA por decisão de produto: 9312300 (clubes), 8591100 (ensino esportivo).

Offline — função pura.
"""
from tools.cnpj_segment_classifier import classificar_segmento


def _seg(nome, cnae_principal, cnaes_sec=None):
    c = classificar_segmento(nome, cnae_principal, cnaes_sec)
    return c.segmento, c.incluir_no_parque


# ── PORTÃO: CNAE principal fora de 931 = joio, mesmo com nome "fit" ────────────

def test_fisioterapia_com_nome_fit_vira_joio():
    # 8650004 (fisioterapia): nome de academia NÃO resgata
    seg, incl = _seg("CENTRO INTEGRADO DE ESPECIALIDADES - ACADEMIA", "8650004")
    assert seg == "fora_familia" and incl is False


def test_hotel_salao_varejo_viram_joio():
    for cnae in ("5510801", "9602502", "4763602", "8230001"):
        seg, incl = _seg("Espaço Fitness", cnae)
        assert seg == "fora_familia" and not incl, f"CNAE {cnae} deveria ser joio"


def test_clubes_e_ensino_fora_por_decisao():
    # 9312300 clubes e 8591100 ensino esportivo: FORA da família (decisão de produto)
    assert _seg("Clube Esportivo X", "9312300") == ("fora_familia", False)
    assert _seg("Escola de Futebol Y", "8591100") == ("fora_familia", False)


def test_cnae_fitness_secundario_nao_resgata():
    # principal fora da família + fitness só no secundário → ainda joio
    seg, incl = _seg("Clínica com Musculação", "8650004", "9313100")
    assert seg == "fora_familia" and not incl


# ── DENTRO da família: nome separa o TIPO (mesmo CNAE 9313100) ─────────────────

def test_mesmo_cnae_nome_separa_tipo():
    assert _seg("Academia Forte", "9313100")[0] == "academia"
    assert _seg("Studio de Pilates Zen", "9313100")[0] == "studio_pilates"
    assert _seg("CrossFit Cocó Box", "9313100")[0] == "crossfit_box"
    assert _seg("Team Muay Thai", "9313100")[0] == "lutas"
    # todos entram no parque (incluir_no_parque=True)
    for nome in ("Academia Forte", "Studio de Pilates Zen", "CrossFit Cocó Box"):
        assert _seg(nome, "9313100")[1] is True


def test_familia_instalacoes_e_lutas_entram():
    assert _seg("Arena Esportes", "9311500")[1] is True
    assert _seg("Centro de Lutas", "9319101")[1] is True


def test_clinica_dentro_da_familia_ainda_cai_por_nome():
    # 9313100 (família) mas nome de fisio → o filtro de nome ainda exclui
    seg, incl = _seg("Clínica de Fisioterapia Movimente", "9313100")
    assert seg == "saude_clinica" and incl is False
