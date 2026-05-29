from tools.bairro_normalize import (
    bairro_coincide,
    bairro_em_alvo,
    formatar_bairro_exibicao,
    normalizar_bairro,
    partes_bairro_alvo,
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


if __name__ == "__main__":
    test_normalizar_acentos_case()
    test_partes_compostas()
    test_bairro_em_alvo()
    test_formatar_exibicao()
    print("ok")
