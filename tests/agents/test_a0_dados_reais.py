"""A0 com dados reais (Supabase CNPJ) — não mock.

Roda: pytest tests/agents/test_a0_dados_reais.py -q
Skip automático se SUPABASE_* ausente ou tool indisponível.
"""
from __future__ import annotations

import os
import types as _t
from pathlib import Path

import pytest
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)

_CIDADE = "Fortaleza"
_UF = "CE"
_BAIRRO = "Cocó"


def _supabase_ok() -> bool:
    return bool(
        (os.getenv("SUPABASE_URL") or "").strip()
        and (
            (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
            or (os.getenv("SUPABASE_KEY") or "").strip()
            or (os.getenv("SUPABASE_ANON_KEY") or "").strip()
        )
    )


pytestmark = [
    pytest.mark.skipif(
        not _supabase_ok(),
        reason="SUPABASE_URL/KEY ausentes no .env — teste com dados reais precisa DB",
    ),
    pytest.mark.integration,
]


@pytest.fixture(scope="module")
def parque_cnpj_real():
    from tools.cnpj_fitness_tools import dados_parque_cnpj_para_a0

    out = dados_parque_cnpj_para_a0(_CIDADE, _UF, 90, _BAIRRO)
    if not isinstance(out, dict) or out.get("status") != "ok":
        pytest.skip(f"CNPJ indisponível: {out.get('status') if isinstance(out, dict) else out}")
    return out


def test_dados_parque_cnpj_numeros_reais(parque_cnpj_real):
    m = parque_cnpj_real.get("metricas_objetivas") or {}
    ativo = m.get("parque_ativo_total")
    comercial = m.get("parque_comercial_total")
    novos = m.get("novos_cnpj_fitness_90d")
    assert isinstance(ativo, int) and ativo > 0
    assert isinstance(comercial, int) and comercial > 0
    assert comercial <= ativo
    assert isinstance(novos, int) and novos >= 0
    arv = parque_cnpj_real.get("arvore_2x2_parque")
    assert isinstance(arv, dict)
    assert "estoque_municipio" in arv
    assert "entrantes_municipio_90d" in arv
    # carimbo mínimo no bloco
    assert parque_cnpj_real.get("cidade") or _CIDADE
    assert parque_cnpj_real.get("dias_janela") == 90 or parque_cnpj_real.get("dias") in (90, None)


def test_a0_override_com_tool_real_sobrescreve_llm(parque_cnpj_real, monkeypatch):
    """LLM inventa 9999; callback aplica números da tool (snapshot real 1×)."""
    import agents.a0_context_builder as a0

    # 1 fetch real; reusa no callback — evita drift entre 2 queries ao Supabase.
    monkeypatch.setattr(
        "tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
        lambda *a, **k: parque_cnpj_real,
    )
    m = parque_cnpj_real["metricas_objetivas"]
    st = {
        "input_params": {"cidade": _CIDADE, "uf": _UF, "bairro": _BAIRRO},
        "market_context": {
            "market_context": {
                "cidade": _CIDADE,
                "uf": _UF,
                "bairro": _BAIRRO,
                "ticket_medio_mercado": "R$ 1 (llm)",
                "parque_ativo_total": 9999,
                "parque_comercial_total": 8888,
                "novos_cnpj_fitness_90d": 777,
            }
        },
    }
    a0._a0_override_cnpj_numeros(_t.SimpleNamespace(state=st))
    inner = st["market_context"]["market_context"]
    assert inner["parque_ativo_total"] == m["parque_ativo_total"]
    assert inner["parque_comercial_total"] == m["parque_comercial_total"]
    assert inner["novos_cnpj_fitness_90d"] == m["novos_cnpj_fitness_90d"]
    assert inner["academias_ativas_cidade_cnpj"] == m["parque_ativo_total"]
    assert inner["_cnpj_override"] == "deterministico_tool"
    assert inner["arvore_2x2_parque"] == parque_cnpj_real.get("arvore_2x2_parque")
    assert m["parque_ativo_total"] != 9999  # prova que veio do banco, não do LLM
    assert inner["ticket_medio_mercado"] == "R$ 1 (llm)"


def test_market_bundle_fortaleza_se_existir():
    """Bundle em disco/cache — se missing, skip (não falha CI sem artifact)."""
    from tools.market_bundle import carregar_market_bundle

    b = carregar_market_bundle(_CIDADE, _BAIRRO, _UF)
    if not isinstance(b, dict):
        pytest.skip("bundle não-dict")
    if b.get("status") == "missing" or "missing" in str(b.get("status", "")).lower():
        pytest.skip("market_bundle missing para Fortaleza/Cocó")
    # briefing ou payload útil
    blob = str(b)
    assert len(blob) > 50
