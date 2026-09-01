from tools.bairro_normalize import (
    bairro_coincide,
    bairro_em_alvo,
    formatar_bairro_exibicao,
    normalizar_bairro,
    partes_bairro_alvo,
    resolver_bairro_canonico,
    sanity_renda_geocode,
)


def test_normalizar_acentos_case():
    assert normalizar_bairro("Cocó") == normalizar_bairro("coco")
    assert normalizar_bairro("  ALDEOTA  ") == "aldeota"


def test_partes_compostas():
    assert "coco" in partes_bairro_alvo("Cocó / Guararapes")
    assert "guararapes" in partes_bairro_alvo("Cocó / Guararapes")


def test_bairro_em_alvo():
    assert bairro_em_alvo("ALDEOTA", "Aldeota")
    assert bairro_em_alvo("Meireles", "meireles")
    assert not bairro_em_alvo("COCO", "Meireles")


def test_formatar_exibicao():
    assert formatar_bairro_exibicao("ALDEOTA") == "Aldeota"


def test_lagoa_rj_alias():
    assert resolver_bairro_canonico("Lagoa", uf="RJ") == "Lagoa Rodrigo de Freitas"
    assert resolver_bairro_canonico("lagoa", uf="rj") == "Lagoa Rodrigo de Freitas"
    assert resolver_bairro_canonico("Rodrigo de Freitas", uf="RJ") == "Lagoa Rodrigo de Freitas"
    # Outra UF não remapeia
    assert resolver_bairro_canonico("Lagoa", uf="CE") == "Lagoa"


def test_sanity_renda_lagoa():
    assert sanity_renda_geocode(403.0, "Lagoa", uf="RJ") is not None
    assert sanity_renda_geocode(7957.0, "Lagoa Rodrigo de Freitas", uf="RJ") is None
    assert sanity_renda_geocode(18002.0, "Lagoa Rodrigo de Freitas", uf="RJ") is None


if __name__ == "__main__":
    test_normalizar_acentos_case()
    test_partes_compostas()
    test_bairro_em_alvo()
    test_formatar_exibicao()
    test_lagoa_rj_alias()
    test_sanity_renda_lagoa()
    print("ok")
