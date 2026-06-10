"""Testes B2 — fetch CVM ITR (fixtures, sem rede)."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from tools.cvm_fetch import (
    CompanyRef,
    build_sector_listed_payload,
    extract_financials_from_itr,
    resolve_company,
    _value_ytd,
    _read_csv_text,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cvm"


def _load_fixture(name: str) -> list[dict]:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return list(_read_csv_text(text))


def _build_mini_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("itr_cia_aberta_DRE_con_2024.csv", (FIXTURES / "dre_con_sample.csv").read_bytes())
        zf.writestr("itr_cia_aberta_BPP_con_2024.csv", (FIXTURES / "bpp_con_sample.csv").read_bytes())
        zf.writestr("itr_cia_aberta_BPA_con_2024.csv", (FIXTURES / "bpa_con_sample.csv").read_bytes())
        zf.writestr("itr_cia_aberta_DFC_MI_con_2024.csv", (FIXTURES / "dfc_mi_con_sample.csv").read_bytes())
    return buf.getvalue()


@pytest.fixture
def smart_ref() -> CompanyRef:
    return CompanyRef(
        ticker="SMFT3",
        cd_cvm="24260",
        cnpj="07594978000178",
        denom_social="SMARTFIT ESCOLA DE GINASTICA E DANCA S.A.",
    )


def test_resolve_company_from_fixture_cad():
    rows = _load_fixture("cad_cia_aberta_sample.csv")
    ref = resolve_company("SMFT3", cad_rows=rows)
    assert ref is not None
    assert ref.cd_cvm == "24260"
    assert ref.cnpj == "07594978000178"


def test_resolve_rejects_unknown_ticker():
    assert resolve_company("BIOM3", cad_rows=_load_fixture("cad_cia_aberta_sample.csv")) is None


def test_value_ytd_picks_correct_period():
    rows = _load_fixture("dre_con_sample.csv")
    v = _value_ytd(rows, "3.01", "2024-09-30")
    assert v == 1000.0


def test_extract_financials_from_mini_zip(smart_ref: CompanyRef):
    fin = extract_financials_from_itr(_build_mini_zip(), smart_ref)
    assert fin is not None
    assert fin["periodo_ref"] == "2024-09-30"
    assert fin["receita_liquida_mil"] == 1000.0
    assert fin["margem_ebitda_pct"] == 40.0  # (320+80)/1000
    assert fin["divida_liquida_ebitda"] is not None


def test_build_sector_listed_payload():
    payload = build_sector_listed_payload(
        {
            "ticker": "SMFT3",
            "cd_cvm": "24260",
            "periodo_ref": "2024-09-30",
            "itr_ano": 2024,
            "margem_ebitda_pct": 40.0,
            "divida_liquida_ebitda": 1.2,
        }
    )
    assert len(payload["empresas"]) == 1
    assert payload["empresas"][0]["ticker"] == "SMFT3"
    assert "BIOM3" not in str(payload)


def test_default_listed_no_bluefit():
    from tools.cvm_listed_metrics import DEFAULT_LISTED

    tickers = [e.get("ticker") for e in DEFAULT_LISTED.get("empresas") or []]
    assert tickers == ["SMFT3"]
    assert "BIOM3" not in tickers
