"""Testes do C6.4 (checkpoint de state) + C6.3 (gate HITL informado)."""
import api
from tools.state_checkpoint import after_agent_checkpoint


class _Q:
    def __init__(self, data):
        self.data = data
        self.upserted = None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def maybe_single(self):
        return self

    def upsert(self, row, **k):
        self.upserted = row
        return self

    def execute(self):
        return type("R", (), {"data": self.data})()


# ── C6.3: _aviso_hitl_relatorio ──────────────────────────────────────────────
class _SBHitl:
    def __init__(self, out, val):
        self.out, self.val = out, val

    def table(self, n):
        return _Q(self.out if n == "relatorio_outputs" else self.val)


def test_hitl_inviavel_e_revisar_manual():
    sb = _SBHitl({"veredito": "REPROVADO", "score_viabilidade": 3.2}, [{"revisar_manual": True}])
    av = api._aviso_hitl_relatorio(sb, "rid")
    assert av["requer_validacao_humana"] is True
    assert any("REPROVADO" in m for m in av["motivos"])
    assert any("revisar_manual" in m for m in av["motivos"])


def test_hitl_aprovado_sem_aviso():
    sb = _SBHitl({"veredito": "APROVADO", "score_viabilidade": 7.5}, [])
    assert api._aviso_hitl_relatorio(sb, "rid") is None


def test_hitl_score_baixo_isolado():
    sb = _SBHitl({"veredito": "APROVADO COM RESSALVAS", "score_viabilidade": 4.0}, [])
    av = api._aviso_hitl_relatorio(sb, "rid")
    assert av is not None and any("viabilidade" in m for m in av["motivos"])


def test_hitl_degrada_em_erro_db():
    class _Boom:
        def table(self, n):
            raise RuntimeError("db down")
    # não levanta — best-effort
    assert api._aviso_hitl_relatorio(_Boom(), "rid") is None


# ── C6.4: after_agent_checkpoint ─────────────────────────────────────────────
class _Ctx:
    def __init__(self, state):
        self.state = state


def test_checkpoint_sem_relatorio_id_nao_grava(monkeypatch):
    chamado = {"v": False}

    def _fake_client():
        chamado["v"] = True
        raise AssertionError("não deveria conectar sem relatorio_id")

    monkeypatch.setattr("tools.supabase_client.load_create_client", lambda: _fake_client, raising=False)
    after_agent_checkpoint(_Ctx({"foo": 1}))  # sem relatorio_id
    assert chamado["v"] is False


def test_checkpoint_degrada_sem_state():
    # state None → não levanta
    after_agent_checkpoint(_Ctx(None))


def test_checkpoint_state_nao_dict_degrada():
    class _Bad:
        state = object()  # dict(state) falha
    after_agent_checkpoint(_Bad())  # não levanta
