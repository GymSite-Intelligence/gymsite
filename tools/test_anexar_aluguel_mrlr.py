"""A1 anexa aluguel DETERMINÍSTICO (MRLR) por candidato — `_anexar_aluguel_mrlr`.

Antes: candidato A1 vinha com aluguel=None (probe Cocó) e só `price_raw` (anúncio
raspado, varia 17k→88k na mesma praça). Agora cada candidato carrega o aluguel MRLR —
a MESMA chamada que o A4 usa (aluguel_deterministico(area, cidade, bairro)) → número de
decisão consistente entre A1 e A4. Puro/offline: monkeypatch no MRLR, sem DB.
"""
import tools.aluguel_mrlr as mrlr
from tools.anchoring_tools import _anexar_aluguel_mrlr


def _fake_ok(*, area_m2, cidade, bairro):
    # valor_unitario fixo → total proporcional à área (prova memoização por área)
    return {"status": "ok", "valor_unitario_m2": 50.0,
            "aluguel_total": round(50.0 * area_m2, 2), "fonte": "MRLR IBAPE-GO (fake)"}


def test_anexa_aluguel_por_area(monkeypatch):
    monkeypatch.setattr(mrlr, "aluguel_deterministico", _fake_ok)
    cands = [{"area_estimada_m2": 1000}, {"area_estimada_m2": 600}]
    out = _anexar_aluguel_mrlr(cands, "Fortaleza", "Cocó")
    assert out[0]["aluguel_estimado"] == 50000.0
    assert out[0]["aluguel_unitario_m2"] == 50.0
    assert "MRLR" in out[0]["aluguel_fonte"]
    assert out[1]["aluguel_estimado"] == 30000.0


def test_sem_bairro_nao_calcula(monkeypatch):
    chamado = {"n": 0}

    def _spy(**k):
        chamado["n"] += 1
        return _fake_ok(**k)

    monkeypatch.setattr(mrlr, "aluguel_deterministico", _spy)
    for bairro in ("", "(cidade inteira)", None):
        cands = [{"area_estimada_m2": 1000}]
        out = _anexar_aluguel_mrlr(cands, "Fortaleza", bairro)
        assert "aluguel_estimado" not in out[0]
    assert chamado["n"] == 0  # nunca chamou MRLR sem bairro real


def test_sem_area_pula(monkeypatch):
    monkeypatch.setattr(mrlr, "aluguel_deterministico", _fake_ok)
    cands = [{"area_estimada_m2": 0}, {"nome": "sem area"}]
    out = _anexar_aluguel_mrlr(cands, "Fortaleza", "Cocó")
    assert "aluguel_estimado" not in out[0]
    assert "aluguel_estimado" not in out[1]


def test_memoiza_por_area(monkeypatch):
    chamado = {"n": 0}

    def _spy(**k):
        chamado["n"] += 1
        return _fake_ok(**k)

    monkeypatch.setattr(mrlr, "aluguel_deterministico", _spy)
    # 3 candidatos, 2 áreas distintas (1000 repetido) → só 2 chamadas MRLR
    cands = [{"area_estimada_m2": 1000}, {"area_estimada_m2": 1000}, {"area_estimada_m2": 600}]
    _anexar_aluguel_mrlr(cands, "Fortaleza", "Cocó")
    assert chamado["n"] == 2


def test_idempotente(monkeypatch):
    monkeypatch.setattr(mrlr, "aluguel_deterministico", _fake_ok)
    cands = [{"area_estimada_m2": 1000, "aluguel_estimado": 99999.0}]
    out = _anexar_aluguel_mrlr(cands, "Fortaleza", "Cocó")
    assert out[0]["aluguel_estimado"] == 99999.0  # já tinha → não sobrescreve


def test_status_nao_ok_deixa_none(monkeypatch):
    monkeypatch.setattr(mrlr, "aluguel_deterministico",
                        lambda **k: {"status": "indisponivel", "motivo": "sem dado"})
    cands = [{"area_estimada_m2": 1000}]
    out = _anexar_aluguel_mrlr(cands, "Fortaleza", "Cocó")
    assert "aluguel_estimado" not in out[0]
