"""Testes do #64: libera entitlement da análise gratuita quando o pipeline falha
(só org anônima) + cap de abuso do chat de degustação por IP/turnos (P2.1)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ─── _liberar_entitlement_analise_gratuita (api.py) ──────────────────────────

def _mock_tbl(org_id: str, monkeypatch) -> dict:
    """Instala um tbl() falso; retorna dict que conta as chamadas de delete."""
    calls = {"delete": 0}

    def fake_tbl(sb, tabela):
        m = MagicMock()
        m.select.return_value = m
        m.eq.return_value = m
        m.limit.return_value = m
        m.execute.return_value = MagicMock(data=[{"org_id": org_id}])

        def _delete():
            calls["delete"] += 1
            d = MagicMock()
            d.eq.return_value = d
            d.execute.return_value = None
            return d

        m.delete.side_effect = _delete
        return m

    monkeypatch.setattr("tools.db_schema.tbl", fake_tbl)
    return calls


def test_libera_entitlement_para_org_anonima(monkeypatch):
    import api
    from backend.routers.site_agent import _ANON_ORG_ID

    calls = _mock_tbl(_ANON_ORG_ID, monkeypatch)
    api._liberar_entitlement_analise_gratuita(MagicMock(), "rel-anon")
    assert calls["delete"] == 1  # deletou o entitlement → email pode tentar de novo


def test_nao_libera_para_org_real(monkeypatch):
    import api

    calls = _mock_tbl("11111111-1111-1111-1111-111111111111", monkeypatch)
    api._liberar_entitlement_analise_gratuita(MagicMock(), "rel-cliente")
    assert calls["delete"] == 0  # conta real: NÃO mexe no entitlement


def test_liberar_entitlement_e_failsafe(monkeypatch):
    """tbl() explode → não propaga (o mark_failed não pode quebrar por causa disso)."""
    import api

    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr("tools.db_schema.tbl", boom)
    api._liberar_entitlement_analise_gratuita(MagicMock(), "rel-x")  # não deve levantar


# ─── _cap_chat_estourado (site_agent.py) — P2.1 ──────────────────────────────

def _mock_redis(monkeypatch, incr_valor: int):
    import backend.routers.site_agent as sa

    r = MagicMock()
    r.incr = AsyncMock(return_value=incr_valor)
    r.expire = AsyncMock()

    async def fake_get_redis():
        return r

    monkeypatch.setattr("tools.redis_client.get_redis", fake_get_redis)
    return sa


async def test_cap_sessoes_estoura(monkeypatch):
    sa = _mock_redis(monkeypatch, incr_valor=99)  # muito acima do cap
    motivo = await sa._cap_chat_estourado("1.2.3.4", None, nova_sessao=True, agente="degustacao")
    assert motivo == "sessoes"


async def test_cap_dentro_do_limite_passa(monkeypatch):
    sa = _mock_redis(monkeypatch, incr_valor=1)  # 1ª sessão do IP
    motivo = await sa._cap_chat_estourado("1.2.3.4", None, nova_sessao=True, agente="degustacao")
    assert motivo is None


async def test_cap_turnos_estoura(monkeypatch):
    sa = _mock_redis(monkeypatch, incr_valor=999)  # acima do cap de turnos
    motivo = await sa._cap_chat_estourado("1.2.3.4", "proj-1", nova_sessao=False, agente="degustacao")
    assert motivo == "turnos"


async def test_clarificacao_nao_conta_como_pergunta(monkeypatch):
    """MODO_DEGUSTACAO on: responder a pergunta do agente (continuação, nova_sessao=False)
    NÃO pode bater no cap `agente`, mesmo com o contador do agente estourado. A clarificação
    é parte da mesma pergunta — só a abertura (nova_sessao) conta. (Bug: usuário respondia o
    estado que o agente pediu e a degustação era encerrada como 'pergunta extra'.)"""
    import backend.routers.site_agent as sa
    monkeypatch.setattr(sa, "_CHAT_MODO_DEGUSTACAO", True)
    _mock_redis(monkeypatch, incr_valor=99)  # agente cap estourado E turnos alto
    # continuação: nova_sessao=False → não passa pelo cap agente; cai só no turnos.
    motivo = await sa._cap_chat_estourado("1.2.3.4", "proj-1", nova_sessao=False, agente="mercado")
    assert motivo == "turnos"   # bloqueia por turnos (5), NUNCA por "agente"


async def test_abertura_ainda_conta_no_cap_agente(monkeypatch):
    """A 1ª mensagem (nova_sessao=True) continua consumindo a cota do especialista."""
    import backend.routers.site_agent as sa
    monkeypatch.setattr(sa, "_CHAT_MODO_DEGUSTACAO", True)
    _mock_redis(monkeypatch, incr_valor=2)  # 2ª abertura do mesmo agente hoje
    motivo = await sa._cap_chat_estourado("1.2.3.4", None, nova_sessao=True, agente="mercado")
    assert motivo == "agente"


async def test_cap_sem_redis_bloqueia(monkeypatch):
    """Redis inacessível → fail-CLOSED.

    Era fail-open (188be38) pra não derrubar a degustação. Mas o mesmo evento
    derruba o enqueue: `_enqueue_ou_background` degrada pra BackgroundTasks e o
    turno roda dentro da api (maxScale=20), não no worker. Sem cap + execução
    inline = gasto de Gemini sem teto. Gasto ilimitado é pior que degustação
    fora do ar por alguns minutos — e o /analise capeia via Supabase, então o
    funil de lead sobrevive à queda do Redis.
    """
    import backend.routers.site_agent as sa

    async def fake_get_redis():
        raise RuntimeError("redis down")

    monkeypatch.setattr("tools.redis_client.get_redis", fake_get_redis)
    motivo = await sa._cap_chat_estourado("1.2.3.4", None, nova_sessao=True, agente="degustacao")
    assert motivo == "indisponivel"


async def test_cap_com_redis_falhando_no_meio_bloqueia(monkeypatch):
    """Redis conecta mas o incr explode → também fail-closed (não só a conexão)."""
    import backend.routers.site_agent as sa

    r = MagicMock()
    r.incr = AsyncMock(side_effect=RuntimeError("connection reset"))
    r.expire = AsyncMock()

    async def fake_get_redis():
        return r

    monkeypatch.setattr("tools.redis_client.get_redis", fake_get_redis)
    motivo = await sa._cap_chat_estourado("1.2.3.4", None, nova_sessao=True, agente="degustacao")
    assert motivo == "indisponivel"


async def test_bypass_nao_passa_pelo_cap(monkeypatch):
    """Dono/dev com bypass nunca chega no cap — queda do Redis não bloqueia o teste interno."""
    import backend.routers.site_agent as sa

    monkeypatch.setattr(sa, "_CHAT_BYPASS_TOKEN", "token-de-teste")
    req = MagicMock()
    req.headers = {"x-site-chat-token": "token-de-teste"}
    assert sa._bypass_autorizado(req, None, "9.9.9.9") is True
