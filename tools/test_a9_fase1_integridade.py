"""Fase 1: ERRC única fonte + headroom sanitizado + cobertura no JSON."""
from __future__ import annotations

import json

from agents.a9_positioning_strategist import (
    _a9_override_veredito_deterministico,
    _build_errc_indeterminado,
    _garantir_eixos_errc_indeterminado,
    _patch_relatorio_json,
    _sanitizar_headroom_se_indeterminado,
)


def test_sanitizar_headroom_zera_tier_e_ticket():
    hr = {
        "status": "ok",
        "renda_pc": 7957.79,
        "tier_modelo_percentil": "Premium",
        "ticket_teto_sustentavel": 1193.67,
        "headroom_ratio": 1.2,
        "headroom_premium": 400.0,
        "veredito_posicionamento": "INDETERMINADO",
    }
    out = _sanitizar_headroom_se_indeterminado(hr, "INDETERMINADO")
    assert out["renda_pc"] == 7957.79
    assert out["tier_modelo_percentil"] is None
    assert out["ticket_teto_sustentavel"] is None
    assert out["headroom_ratio"] is None
    assert out["headroom_premium"] is None
    assert out["veredito_posicionamento"] == "INDETERMINADO"


def test_sanitizar_nao_mexe_oceano_azul():
    hr = {"tier_modelo_percentil": "Premium", "ticket_teto_sustentavel": 800.0}
    out = _sanitizar_headroom_se_indeterminado(hr, "OCEANO_AZUL")
    assert out["tier_modelo_percentil"] == "Premium"
    assert out["ticket_teto_sustentavel"] == 800.0


def test_garantir_eixos_preenche_errc_vazio():
    parsed = {
        "veredito_posicionamento": "INDETERMINADO",
        "framework_errc": {"eliminar": [], "reduzir": [], "aumentar": [], "criar": []},
    }
    state = {
        "input_params": {"cidade": "Fortaleza", "bairro": "Meireles", "uf": "CE"},
        "output_consolidado": {
            "dores_dominantes": [{"dor": "atendimento_ruim", "mencoes": 4}],
        },
    }
    _garantir_eixos_errc_indeterminado(state, parsed)
    errc = parsed["framework_errc"]
    assert len(errc["eliminar"]) >= 2
    assert any("atendimento" in b.lower() for b in errc["eliminar"])
    assert len(errc["reduzir"]) >= 2
    assert len(errc["aumentar"]) >= 1


def test_garantir_eixos_nao_sobrescreve_preenchido():
    parsed = {
        "veredito_posicionamento": "INDETERMINADO",
        "framework_errc": {
            "eliminar": ["já tinha"],
            "reduzir": [],
            "aumentar": [],
            "criar": [],
        },
    }
    _garantir_eixos_errc_indeterminado({}, parsed)
    assert parsed["framework_errc"]["eliminar"] == ["já tinha"]


def test_build_errc_indeterminado_unica_fonte():
    out = _build_errc_indeterminado(
        {
            "input_params": {"cidade": "Fortaleza", "bairro": "Meireles", "uf": "CE"},
            "output_consolidado": {
                "dores_dominantes": [{"dor": "equipamento_problema", "mencoes": 3}],
            },
        },
        motivo="A4 sem modelo viável",
        fonte_veredito="a4_sem_modelo_viavel",
    )
    errc = out["framework_errc"]
    assert errc["eliminar"]
    assert errc["reduzir"]
    assert any("equipamento" in b.lower() or "climatiz" in b.lower() for b in errc["aumentar"])


def test_override_sanitiza_quando_a4_nenhum(monkeypatch):
    fake_hr = {
        "status": "ok",
        "renda_pc": 5125.0,
        "tier_modelo_percentil": "Premium",
        "ticket_teto_sustentavel": 768.87,
        "headroom_ratio": None,
        "veredito_posicionamento": "INDETERMINADO",
    }
    monkeypatch.setattr(
        "tools.posicionamento_renda.avaliar_posicionamento",
        lambda *a, **k: fake_hr,
    )
    parsed = {
        "veredito_posicionamento": "INDETERMINADO",
        "fonte_veredito": "a4_sem_modelo_viavel",
        "framework_errc": {"eliminar": [], "reduzir": [], "aumentar": [], "criar": []},
        "recomendacao_ticket": {"ticket_recomendado": None},
    }
    state = {
        "input_params": {"cidade": "Fortaleza", "bairro": "Meireles", "uf": "CE"},
        "cidade": "Fortaleza",
        "bairro": "Meireles",
        "uf": "CE",
        "output_consolidado": {
            "dores_dominantes": [{"dor": "atendimento_ruim", "mencoes": 4}],
        },
    }
    _a9_override_veredito_deterministico(state, parsed)
    hr = parsed["headroom_renda"]
    assert hr["renda_pc"] == 5125.0
    assert hr["tier_modelo_percentil"] is None
    assert hr["ticket_teto_sustentavel"] is None
    assert parsed["veredito_posicionamento"] == "INDETERMINADO"
    assert parsed["framework_errc"]["eliminar"]


def test_patch_persiste_cobertura_se_ausente(tmp_path, monkeypatch):
    import agents.a9_positioning_strategist as a9

    monkeypatch.setattr(a9, "_RELATORIOS_DIR", tmp_path)
    rel = {"id": "rpt_teste", "output_consolidado": {"resumo_executivo": "ok"}}
    (tmp_path / "rpt_teste.json").write_text(json.dumps(rel), encoding="utf-8")
    cov = {"gated_n": 14, "n_com_oferta": 3, "oferta_por_gated": {"x": {"servicos": []}}}
    a9._patch_relatorio_json(
        "rpt_teste",
        {"veredito_posicionamento": "INDETERMINADO"},
        state={"cobertura_competitiva": cov},
    )
    out = json.loads((tmp_path / "rpt_teste.json").read_text(encoding="utf-8"))
    assert out["output_consolidado"]["cobertura_competitiva"]["gated_n"] == 14
    assert out["output_consolidado"]["posicionamento_estrategico"]["veredito_posicionamento"] == "INDETERMINADO"
