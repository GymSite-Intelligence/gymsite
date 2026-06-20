"""Checkpoint do state por agente em Supabase (CONSTITUTION C6.4 — estado de
orquestração persistido externamente, recuperável).

NÃO troca o SessionService (InMemory segue no runtime — swap teria risco de quebrar
o pipeline). Este callback só dá DURABILIDADE: snapshota o state acumulado após cada
agente em relatorio_state_checkpoint, pra inspeção/recuperação pós-crash. Best-effort,
falha silenciosa — nunca derruba o pipeline.
"""
from __future__ import annotations

import json
import logging
import os
from tools.db_schema import tbl

logger = logging.getLogger("gymsite.checkpoint")

_MAX_BYTES = int(os.getenv("STATE_CHECKPOINT_MAX_BYTES", "600000"))


def after_agent_checkpoint(callback_context) -> None:
    """after_agent_callback: grava snapshot do state em Supabase. Degrada limpo."""
    try:
        state = getattr(callback_context, "state", None)
        if state is None:
            return
        try:
            state_dict = dict(state)
        except Exception:
            return
        rid = state_dict.get("relatorio_id")
        if not isinstance(rid, str) or not rid:
            return  # sem id não dá pra recuperar — pula

        from tools.token_telemetry import _resolve_agent_name

        agente = _resolve_agent_name(callback_context) or "desconhecido"
        keys = [str(k) for k in state_dict.keys()]

        # Serializa best-effort. State gigante → guarda só as keys (recuperação parcial,
        # não estoura o limite de row). default=str p/ tipos não-JSON.
        try:
            blob = json.loads(json.dumps(state_dict, default=str))
            if len(json.dumps(blob)) > _MAX_BYTES:
                blob = {"_truncado": True, "_motivo": f"state > {_MAX_BYTES} bytes"}
        except Exception:
            blob = {"_erro_serializacao": True}

        key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
               or os.environ.get("SUPABASE_SERVICE_KEY")
               or os.environ.get("SUPABASE_KEY"))
        url = os.environ.get("SUPABASE_URL")
        if not (url and key):
            return

        from tools.supabase_client import load_create_client

        cli = load_create_client()(url, key)
        tbl(cli, "relatorio_state_checkpoint").upsert(
            {"relatorio_id": rid, "agente": agente, "state": blob, "state_keys": keys},
            on_conflict="relatorio_id,agente",
        ).execute()
    except Exception:
        logger.debug("checkpoint falhou (degrada)", exc_info=True)
