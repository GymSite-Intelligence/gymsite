"""Regressão da contradição do Cocó (4b211a02): A9 marca INDETERMINADO depois de o
A6 já ter consolidado o resumo, e o resumo recomendava Mid Market sem ressalva.
Valida a emenda idempotente no JSON local e o texto da ressalva."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agents.a9_positioning_strategist as a9


def _rel_tmp(tmp_path, resumo="Cocó: veredito INVESTIGAR MAIS. Modelo recomendado Mid Market (payback 26 meses)."):
    rel = {"output_consolidado": {
        "resumo_executivo": resumo,
        "contato_decisor": {"resumo_executivo": resumo},
    }}
    p = tmp_path / "rpt_teste.json"
    p.write_text(json.dumps(rel, ensure_ascii=False), encoding="utf-8")
    return p


def _patch(tmp_path, monkeypatch, veredito):
    monkeypatch.setattr(a9, "_RELATORIOS_DIR", tmp_path)
    a9._patch_relatorio_json("rpt_teste", {"veredito_posicionamento": veredito})
    return json.loads((tmp_path / "rpt_teste.json").read_text(encoding="utf-8"))["output_consolidado"]


def test_indeterminado_emenda_ressalva(tmp_path, monkeypatch):
    _rel_tmp(tmp_path)
    out = _patch(tmp_path, monkeypatch, "INDETERMINADO")
    assert a9._RESSALVA_INDETERMINADO in out["resumo_executivo"]
    assert a9._RESSALVA_INDETERMINADO in out["contato_decisor"]["resumo_executivo"]
    assert "Modelo recomendado Mid Market" in out["resumo_executivo"]


def test_emenda_e_idempotente(tmp_path, monkeypatch):
    _rel_tmp(tmp_path)
    _patch(tmp_path, monkeypatch, "INDETERMINADO")
    out = _patch(tmp_path, monkeypatch, "INDETERMINADO")
    assert out["resumo_executivo"].count(a9._RESSALVA_INDETERMINADO) == 1


def test_veredito_definido_nao_emenda(tmp_path, monkeypatch):
    _rel_tmp(tmp_path)
    out = _patch(tmp_path, monkeypatch, "APROVADO")
    assert a9._RESSALVA_INDETERMINADO not in out["resumo_executivo"]


def test_emendar_ressalva_texto_vazio():
    assert a9._emendar_ressalva(None) is None
    assert a9._emendar_ressalva("") == ""
