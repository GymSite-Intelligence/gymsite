from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from tools.a1_listing_pipeline import buscar_candidatos_listing_mrlr

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (os.getenv("SEARCHAPI_KEY") or "").strip(),
        reason="SEARCHAPI_KEY ausente",
    ),
]


def test_pirapora_listing_ou_vazio_honesto():
    result = buscar_candidatos_listing_mrlr(
        cidade="Pirapora",
        uf="MG",
        bairro="Centro",
        area_m2_min=500,
        area_m2_max=2000,
    )

    assert result["status"] in {"ok", "ok_vazio"}
    assert result["fonte"] == "listing_cascata_searchapi+mrlr"
    for candidate in result["candidatos"]:
        assert candidate["qualidade_sinal"] == "direto-listing-bairro"
        assert candidate["area_m2"] > 0
        assert candidate["cidade"] == "Pirapora"
        assert candidate["uf"] == "MG"
        assert "Diadema" not in candidate["endereco"]
