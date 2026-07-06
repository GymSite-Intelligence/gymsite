"""Camada 3 do offer_mapper (SPEC_OFERTA_AGREGADORES). Fixture = texto REAL da página
de parceiro do Wellhub (CT Greenlife, sondagem 07/07/2026) — teste determinístico,
sem rede. Valida: parser do Wellhub (tier, rating, IG, comodidades), barreira de
matching anti-falso-positivo e o isolamento tier ≠ preço de balcão."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.agregadores_fetcher import _nome_casa, parse_wellhub_texto

_FIXTURE_WELLHUB_CT = (
    "CT Greenlife 4.86 (1843 Avaliações) A partir do plano Gold Tenha acesso a esta e "
    "mais de 47.000 outras opções de bem-estar por apenas R$ 319,99/mês Verificar "
    "elegibilidade Sobre CT Greenlife CT Greenlife é a escolha certa para quem busca um "
    "box que oferece treinos de cross training, condicionamento físico e boot camp. "
    "Comodidades O que este parceiro oferece Ar condicionado Área de alongamento "
    "Área de cardio Área de musculação Área de pesos livres Armários Balança de "
    "bioimpedância Banheiro acessível Bebedouro Chuveiro Elevador Estacionamento "
    "Loja de artigos esportivos Vestiário Wi-Fi --- Horário de funcionamento "
    "Segunda-feira 00:00 - 23:59 O que você pode fazer Condicionamento Físico Crossfit "
    "Boot Camp Abdomen e Braço Body Jam Informações de contato "
    "https://instagram.com/greenlife_ct/?hl=en (85) 2028-4240 "
    "R. Dr. Gilberto Studart, 155 - Cocó, Fortaleza - CE Silver+ R$ 199,99 / mês "
    "Gold R$ 319,99 / mês Gold+ R$ 439,99 / mês"
)


def test_parser_wellhub_tier_e_rating():
    out = parse_wellhub_texto(_FIXTURE_WELLHUB_CT)
    assert out["tier_agregador"]["plano"] == "Gold"
    assert out["tier_agregador"]["preco_mensal_brl"] == 319.99
    assert "não é mensalidade de balcão" in out["tier_agregador"]["observacao"]
    assert out["rating_agregador"]["nota"] == 4.86
    assert out["rating_agregador"]["avaliacoes"] == 1843


def test_parser_wellhub_instagram_e_comodidades():
    out = parse_wellhub_texto(_FIXTURE_WELLHUB_CT)
    assert out["instagram_handle"] == "greenlife_ct"
    blob = " ".join(out.get("comodidades") or [])
    assert "bioimpedância" in blob.lower()
    assert "Estacionamento" in blob


def test_matching_anti_falso_positivo():
    assert _nome_casa("CT Greenlife", "CT Greenlife - Cocó - Wellhub")
    assert _nome_casa("vs club", "vs club - Aldeota - Fortaleza - Gurupass")
    assert not _nome_casa("CT Greenlife", "Bodytech - Iguatemi Fortaleza")
    assert not _nome_casa("Academia Onda", "Melhores academias de Fortaleza - lista 2026")


def test_texto_sem_dados_nao_inventa():
    out = parse_wellhub_texto("página genérica sem nada de parceiro")
    assert "tier_agregador" not in out
    assert "rating_agregador" not in out
