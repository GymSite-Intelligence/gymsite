import pytest

from agents_site import tools_l1_dados as l1


@pytest.mark.asyncio
async def test_buscar_pontos_usa_listing_mrlr(monkeypatch):
    calls = []
    fake = {
        "status": "ok",
        "total_candidatos": 1,
        "candidatos": [
            {
                "nome": "Loja",
                "qualidade_sinal": "direto-listing-bairro",
                "aluguel_fonte": "MRLR",
            }
        ],
    }

    def _listing(**kwargs):
        calls.append(kwargs)
        return fake

    monkeypatch.setattr(l1, "buscar_candidatos_listing_mrlr", _listing, raising=False)

    result = await l1.buscar_pontos_comerciais(
        "Pirapora",
        "Centro",
        "MG",
        600,
        1200,
    )

    assert calls == [
        {
            "cidade": "Pirapora",
            "uf": "MG",
            "bairro": "Centro",
            "area_m2_min": 600,
            "area_m2_max": 1200,
        }
    ]
    assert result["status"] == "ok"
    assert result["candidatos"][0]["qualidade_sinal"] == "direto-listing-bairro"


@pytest.mark.asyncio
async def test_buscar_pontos_vazio_traz_aviso_usuario(monkeypatch):
    monkeypatch.setattr(
        l1,
        "buscar_candidatos_listing_mrlr",
        lambda **kwargs: {
            "status": "ok_vazio",
            "total_candidatos": 0,
            "candidatos": [],
            "aviso": "Nenhum anúncio verificável.",
        },
        raising=False,
    )

    result = await l1.buscar_pontos_comerciais("Pirapora", "Centro", "MG")

    assert result["status"] == "ok_vazio"
    assert result["candidatos"] == []
    assert result["aviso_usuario"] == "Nenhum anúncio verificável."
