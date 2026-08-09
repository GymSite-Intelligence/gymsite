from __future__ import annotations

from tools import resend_client as rc


def test_enroll_sem_chave(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    out = rc.enroll_explorar_lead("a@b.com", "João Pessoa", "Bessa")
    assert out["ok"] is False
    assert out["motivo"] == "sem_chave"


def test_enroll_dispara_contato_e_email(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RESEND_FROM", "GymSite <contato@gymsite.com.br>")
    calls: list[tuple[str, dict]] = []

    def _post(path, body, idempotency_key=None):
        calls.append((path, body, idempotency_key))
        return {"ok": True, "status": 200, "data": {"id": "x"}}

    monkeypatch.setattr(rc, "_post", _post)
    out = rc.enroll_explorar_lead("Marcelo.Abissulo@gmail.com", "João Pessoa", "Bessa")
    assert out["ok"] is True
    assert calls[0][0] == "/contacts"
    assert calls[0][1]["email"] == "marcelo.abissulo@gmail.com"
    assert calls[1][0] == "/emails"
    assert calls[1][1]["to"] == ["marcelo.abissulo@gmail.com"]
    assert "preço" not in calls[1][1]["html"].lower()
    assert "plano" not in calls[1][1]["html"].lower()
    assert calls[1][2] == "explorar-welcome/marcelo.abissulo@gmail.com"


def test_enroll_email_invalido():
    assert rc.enroll_explorar_lead("")["motivo"] == "email_invalido"
